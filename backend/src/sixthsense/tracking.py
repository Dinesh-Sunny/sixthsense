"""The one place supervision/trackers (and cv2) are used: boxes -> tracks -> closing-gap check.

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
    GAP_SERIES_MAX_POINTS,
    HIGH_CONF_DET,
    MIN_DET_CONF,
    MIN_SHARED_FRAMES,
    MIN_TRACK_FRAMES,
    TRACK_ACTIVATION,
    VEHICLES,
)

DEFAULT_FPS = 30.0


@dataclass
class GapResult:
    score: float  # 0..1, share of the starting gap that closed
    note: str
    gap_series: list[GapPoint] = field(default_factory=list)


@dataclass
class _Track:
    label: str
    points: dict[float, tuple[np.ndarray, float]] = field(default_factory=dict)  # t -> (center, diagonal)


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
            tr.points[round(t, 3)] = (centers[i], diag)
    return [t for t in tracks.values() if len(t.points) >= MIN_TRACK_FRAMES]


def _smooth(values: list[float]) -> list[float]:
    """3-point moving average: damps id jitter (same as the original pipeline)."""
    out = []
    for i in range(len(values)):
        window = values[max(0, i - 1) : i + 2]
        out.append(sum(window) / len(window))
    return out


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
    fps = det.fps or DEFAULT_FPS
    tracks = [t for group in _class_groups(classes) for t in _track_group(det, group, fps)]
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
                (ca, da), (cb, db) = a.points[t], b.points[t]
                size = max((da + db) / 2, 1.0)
                raw.append(float(np.linalg.norm(ca - cb)) / size)
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
