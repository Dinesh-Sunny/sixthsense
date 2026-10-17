"""The one place supervision/trackers (and cv2) are used: boxes -> tracks -> verify checks.

Two checks: closing_gap (fixed cameras: two road users close on each other) and closing_on_us
(vehicle-mounted cameras: a road user's box grows fast in our lane = we are closing on it).

Ported from pipeline/run.py closing_gap: same rule (pair ends within CLOSE_CL car lengths,
>= MIN_SHARED_FRAMES shared frames, 3-point smoothing), with ByteTrack replacing IoU linking.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

from .clients.vss import DetectionsResp, Frame
from .contracts import GapPoint
from .modes import (
    CLOSE_CL,
    COCO_IDS,
    DEFAULT_FRAME_WH,
    EGO_GROWTH_MIN,
    EGO_MEDIAN_FRAMES,
    EGO_MIN_FRAMES,
    EGO_MIN_MEAN_CONF,
    EGO_MIN_SPAN_S,
    EGO_MIN_START_AREA,
    EGO_NEAR_HEIGHT,
    EGO_SELF_MASK,
    EGO_TTC_MAX_S,
    EGO_TTC_MIN_SCALE,
    EGO_TTC_SPAN_S,
    EGO_WINDOW_S,
    EGO_ZONES,
    GAP_SERIES_MAX_POINTS,
    HIGH_CONF_DET,
    MIN_DET_CONF,
    MIN_SHARED_FRAMES,
    MIN_TRACK_FRAMES,
    TRACK_ACTIVATION,
    VEHICLES,
    CameraView,
)

DEFAULT_FPS = 30.0


@dataclass
class GapResult:
    score: float  # 0..1, share of the starting gap that closed
    note: str
    gap_series: list[GapPoint] = field(default_factory=list)
    passed: bool | None = None  # set by checks with their own pass rule (ego); else score >= VERIFY_MIN
    # ego only: best passing (score, note) per road-user class, so the note can follow the hazard
    passing: dict[str, tuple[float, str]] = field(default_factory=dict)


@dataclass
class _Point:
    center: np.ndarray
    diag: float
    xyxy: np.ndarray
    conf: float = 1.0


@dataclass
class _Track:
    label: str
    points: dict[float, _Point] = field(default_factory=dict)  # t -> box


def to_detections(frame: Frame, allowed: frozenset[str]) -> sv.Detections:
    """One frame's boxes as sv.Detections, keeping only allowed COCO labels and sane boxes."""
    rows = [
        (b.bbox, b.confidence, b.label.lower())
        for b in frame.detections
        if b.label.lower() in allowed
        and b.label.lower() in COCO_IDS
        and b.confidence >= MIN_DET_CONF
        and len(b.bbox) == 4
        and all(math.isfinite(v) for v in b.bbox)
        and b.bbox[2] > b.bbox[0]
        and b.bbox[3] > b.bbox[1]
    ]
    if not rows:
        return sv.Detections.empty()
    return sv.Detections(
        xyxy=np.array([r[0] for r in rows], dtype=np.float32),
        confidence=np.array([r[1] for r in rows], dtype=np.float32),
        class_id=np.array([COCO_IDS[r[2]] for r in rows], dtype=np.int64),
        data={"class_name": np.array([r[2] for r in rows])},
    )


def _frame_time(frame: Frame, fps: float) -> float:
    return frame.time_sec if frame.time_sec is not None else frame.frame_index / fps


def _class_groups(classes: frozenset[str]) -> list[frozenset[str]]:
    """Vehicles and people/bikes get separate trackers: ByteTrack is class-agnostic,
    so a pedestrian box next to a car could otherwise take the car's id."""
    groups = [classes & VEHICLES, classes - VEHICLES]
    return [g for g in groups if g]


def _track_group(det: DetectionsResp, group: frozenset[str], fps: float) -> list[_Track]:
    # One fresh tracker per clip and group: trackers are stateful and ids restart at 0.
    tracker = ByteTrackTracker(
        frame_rate=fps,
        track_activation_threshold=TRACK_ACTIVATION,
        high_conf_det_threshold=HIGH_CONF_DET,
    )
    tracks: dict[int, _Track] = {}
    last_t = -math.inf
    for frame in sorted(det.frames, key=lambda f: f.frame_index):
        t = _frame_time(frame, fps)
        if t <= last_t:  # tracker skips non-increasing timestamps; keep ours consistent
            continue
        last_t = t
        # update() on empty frames too: that is what lets a track survive a gap.
        tracked = tracker.update(to_detections(frame, group), timestamp=t)
        if len(tracked) == 0 or tracked.tracker_id is None:
            continue
        tracked = tracked[tracked.tracker_id >= 0]
        if len(tracked) == 0:
            continue
        centers = tracked.get_anchors_coordinates(sv.Position.CENTER)
        for i, tid in enumerate(tracked.tracker_id):
            x1, y1, x2, y2 = tracked.xyxy[i]
            diag = float(math.hypot(x2 - x1, y2 - y1))
            tr = tracks.setdefault(int(tid), _Track(label=str(tracked.data["class_name"][i])))
            conf = float(tracked.confidence[i]) if tracked.confidence is not None else 1.0
            tr.points[round(t, 3)] = _Point(centers[i], diag, tracked.xyxy[i].astype(float), conf)
    return [t for t in tracks.values() if len(t.points) >= MIN_TRACK_FRAMES]


def _smooth(values: list[float]) -> list[float]:
    """3-point moving average: damps id jitter (same as the original pipeline)."""
    out = []
    for i in range(len(values)):
        window = values[max(0, i - 1) : i + 2]
        out.append(sum(window) / len(window))
    return out


def _tracks(det: DetectionsResp, classes: frozenset[str]) -> list[_Track]:
    fps = det.fps or DEFAULT_FPS
    return [t for group in _class_groups(classes) for t in _track_group(det, group, fps)]


def _a(label: str) -> str:
    return {"person": "a pedestrian", "bicycle": "a cyclist", "motorcycle": "a motorbike"}.get(
        label, "a " + label
    )


def _thin(series: list[GapPoint]) -> list[GapPoint]:
    if len(series) <= GAP_SERIES_MAX_POINTS:
        return series
    step = len(series) / GAP_SERIES_MAX_POINTS
    return [series[int(i * step)] for i in range(GAP_SERIES_MAX_POINTS)]


def closing_gap(det: DetectionsResp | None, classes: frozenset[str] = VEHICLES) -> GapResult | None:
    """Best pair (at least one vehicle) whose gap closes to within CLOSE_CL car lengths.

    Returns None when there are no frames (caller falls back to YOLO / Cosmos).
    """
    if det is None or not det.frames:
        return None
    tracks = _tracks(det, classes)
    best: tuple[float, str, list[GapPoint]] | None = None
    for i, a in enumerate(tracks):
        for b in tracks[i + 1 :]:
            if a.label not in VEHICLES and b.label not in VEHICLES:
                continue
            shared = sorted(set(a.points) & set(b.points))
            if len(shared) < MIN_SHARED_FRAMES:
                continue
            raw = []
            for t in shared:
                pa, pb = a.points[t], b.points[t]
                size = max((pa.diag + pb.diag) / 2, 1.0)
                raw.append(float(np.linalg.norm(pa.center - pb.center)) / size)
            dist = _smooth(raw)
            d0, dmin = sum(dist[:2]) / 2, min(dist)
            if d0 <= 0 or dmin > CLOSE_CL:
                continue
            score = (d0 - dmin) / d0
            if best is None or score > best[0]:
                k = dist.index(dmin)
                t0 = shared[0]
                note = (
                    f"{_a(a.label)} and {_a(b.label)} closed from {d0:.1f} to {dmin:.1f} "
                    f"car lengths in {shared[k] - t0:.1f}s"
                )
                series = [GapPoint(t=round(t - t0, 2), cl=round(d, 2)) for t, d in zip(shared, dist, strict=True)]
                best = (score, note, series)
    if best is None:
        return GapResult(0.0, f"{len(tracks)} road users tracked, no pair closing within {CLOSE_CL} car lengths")
    return GapResult(round(best[0], 2), best[1], _thin(best[2]))


# ---------- ego check: vehicle-mounted cameras ----------
_WHERE = {"front": "ahead", "nearside": "alongside"}
_TOWARD = {"front": "the front of the bus", "nearside": "the side of the bus"}


@dataclass
class _EgoHit:
    growth: float
    window_s: float
    ttc_s: float | None
    height_frac: float
    passed: bool

    @property
    def score(self) -> float:
        # growth beyond the gate, plus credit for a short time to contact; capped at 1
        ttc = 1 - self.ttc_s / EGO_TTC_MAX_S if self.ttc_s is not None and self.ttc_s < EGO_TTC_MAX_S else 0.0
        return round(min(1.0, max((self.growth - 1) / (EGO_GROWTH_MIN - 1) / 2, ttc)), 2)


def _frame_wh(det: DetectionsResp) -> tuple[float, float]:
    if det.video_shape and len(det.video_shape) >= 2 and det.video_shape[0] > 0 and det.video_shape[1] > 0:
        return float(det.video_shape[1]), float(det.video_shape[0])
    # Unknown shape: the largest box edge seen is a lower bound; never smaller than 1080p.
    xs = [b.bbox[2] for f in det.frames for b in f.detections if len(b.bbox) == 4]
    ys = [b.bbox[3] for f in det.frames for b in f.detections if len(b.bbox) == 4]
    return max([DEFAULT_FRAME_WH[0], *xs]), max([DEFAULT_FRAME_WH[1], *ys])


def _drop_camera_boxes(det: DetectionsResp, wh: tuple[float, float], view: CameraView) -> DetectionsResp:
    """Remove boxes that belong to the camera's own vehicle (bike handlebars, hands, front wheel)."""
    mask = EGO_SELF_MASK.get(view)
    if mask is None:
        return det
    band, max_w = mask
    floor, widest = (1 - band) * wh[1], max_w * wh[0]

    def own(bbox: list[float]) -> bool:
        return len(bbox) == 4 and (bbox[3] >= floor or bbox[2] - bbox[0] > widest)

    frames = [
        f.model_copy(update={"detections": [b for b in f.detections if not own(b.bbox)]}) for f in det.frames
    ]
    return det.model_copy(update={"frames": frames})


def _in_zone(p: _Point, wh: tuple[float, float], view: CameraView) -> bool:
    x_min, x_max, y_min = EGO_ZONES[view]
    cx = (p.xyxy[0] + p.xyxy[2]) / 2
    return x_min * wh[0] <= cx <= x_max * wh[0] and p.xyxy[3] >= y_min * wh[1]


def _trailing_median(values: list[float], n: int) -> list[float]:
    return [float(np.median(values[max(0, i - n + 1) : i + 1])) for i in range(len(values))]


def _usable(track: _Track, wh: tuple[float, float]) -> bool:
    ts = sorted(track.points)
    first = track.points[ts[0]].xyxy
    start_area = (first[2] - first[0]) * (first[3] - first[1]) / (wh[0] * wh[1])
    mean_conf = sum(p.conf for p in track.points.values()) / len(track.points)
    return start_area >= EGO_MIN_START_AREA and mean_conf >= EGO_MIN_MEAN_CONF


def _ego_track(track: _Track, wh: tuple[float, float], view: CameraView) -> _EgoHit | None:
    """Best growth of one track while it is in the lane zone.

    Scale expansion is the classic time-to-contact cue: if a box grows by s over dt, contact is
    about dt / (s - 1) away at constant closing speed (no depth or speed needed). Heights are a
    trailing median, so one jittery box can never produce a 13x "growth".
    """
    ts = sorted(track.points)
    raw = [float(track.points[t].xyxy[3] - track.points[t].xyxy[1]) for t in ts]
    heights = _trailing_median(raw, EGO_MEDIAN_FRAMES)
    best: _EgoHit | None = None
    i = k = 0
    for j, tj in enumerate(ts):
        while tj - ts[i] > EGO_WINDOW_S:
            i += 1
        while k < j and tj - ts[k + 1] >= EGO_TTC_SPAN_S:
            k += 1
        if not _in_zone(track.points[tj], wh, view) or heights[j] <= 0:
            continue
        # baseline = smallest box at least EGO_MIN_SPAN_S and EGO_MIN_FRAMES before now
        early = [m for m in range(i, j + 1) if tj - ts[m] >= EGO_MIN_SPAN_S and j - m + 1 >= EGO_MIN_FRAMES]
        if not early:
            continue
        m0 = min(early, key=lambda m: heights[m])
        if heights[m0] <= 0:
            continue
        growth = heights[j] / heights[m0]
        ttc = None
        scale, dt = (heights[j] / heights[k], tj - ts[k]) if heights[k] > 0 else (0.0, 0.0)
        # A shorter span turns 1-2 px of box jitter into a fake "seconds to contact".
        if k < j and scale >= EGO_TTC_MIN_SCALE and dt >= EGO_TTC_SPAN_S:
            ttc = dt / (scale - 1)
        height_frac = heights[j] / wh[1]
        close = (ttc is not None and ttc <= EGO_TTC_MAX_S) or height_frac >= EGO_NEAR_HEIGHT
        hit = _EgoHit(growth, tj - ts[m0], ttc, height_frac, growth >= EGO_GROWTH_MIN and close)
        if best is None or (hit.passed, hit.growth) > (best.passed, best.growth):
            best = hit
    return best


def _users(n: int) -> str:
    return "1 road user" if n == 1 else f"{n} road users"


def _ego_note(label: str, hit: _EgoHit, view: CameraView) -> str:
    note = f"{_a(label)} {_WHERE[view]} grew {hit.growth:.1f}x in {hit.window_s:.1f} s"
    # Cite whichever closeness test actually passed: time to contact first, else box size.
    if hit.ttc_s is not None and hit.ttc_s <= EGO_TTC_MAX_S:
        when = "under 1 s" if hit.ttc_s < 1 else f"about {hit.ttc_s:.0f} s"
        note += f", {when} from {_TOWARD[view]}"
    elif hit.height_frac >= EGO_NEAR_HEIGHT:
        note += f", now filling {hit.height_frac:.0%} of the frame height"
    return note


def closing_on_us(
    det: DetectionsResp | None, classes: frozenset[str], view: CameraView
) -> GapResult | None:
    """Vehicle-mounted camera: keep the clip when a tracked road user in our lane zone grows
    >= EGO_GROWTH_MIN over >= EGO_MIN_SPAN_S, AND is close (TTC proxy <= EGO_TTC_MAX_S or box
    height >= EGO_NEAR_HEIGHT of the frame).

    The camera vehicle has no box of its own, so the pair check cannot apply. Returns None when
    there are no frames. gap_series stays empty: there is no gap in car lengths to chart.
    """
    if det is None or not det.frames:
        return None
    wh = _frame_wh(det)
    tracks = [t for t in _tracks(_drop_camera_boxes(det, wh, view), classes) if _usable(t, wh)]
    best: tuple[_Track, _EgoHit] | None = None
    passing: dict[str, tuple[float, str]] = {}
    for tr in tracks:
        hit = _ego_track(tr, wh, view)
        if hit is None:
            continue
        if hit.passed and (tr.label not in passing or hit.score > passing[tr.label][0]):
            passing[tr.label] = (hit.score, _ego_note(tr.label, hit, view))
        if best is None or (hit.passed, hit.growth) > (best[1].passed, best[1].growth):
            best = (tr, hit)
    if best is None:
        return GapResult(0.0, f"{_users(len(tracks))} tracked, none in the lane {_WHERE[view]}", passed=False)
    tr, hit = best
    if not hit.passed:
        return GapResult(
            round(max(0.0, hit.growth - 1), 2),
            f"{_users(len(tracks))} tracked, none closing on us fast enough",
            passed=False,
        )
    return GapResult(hit.score, _ego_note(tr.label, hit, view), passed=True, passing=passing)


def hazard_match(passing: dict[str, tuple[float, str]], wanted: frozenset[str]) -> tuple[float, str] | None:
    """Best passing track among the classes a hazard names (e.g. person for 'Pedestrian stepping out')."""
    hits = [v for label, v in passing.items() if label in wanted]
    return max(hits) if hits else None
