"""Ego "closing on us" check for vehicle-mounted cameras, on synthetic growing boxes."""

from sixthsense.clients.vss import DetectionsResp
from sixthsense.modes import VEHICLES, VULNERABLE
from sixthsense.tracking import closing_on_us

ALL = VEHICLES | VULNERABLE
W, H = 1920, 1080


def growing(label="person", cx=960, h0=100.0, rate=1.0, n=60, fps=30, bottom=800.0, conf=0.8):
    """One box whose height grows `rate`x per second (rate=1 = constant), anchored at `bottom`."""
    frames = []
    for i in range(n):
        t = i / fps
        h = h0 * rate**t
        w = h * (0.4 if label == "person" else 1.6)
        frames.append({"frame_index": i, "time_sec": t, "detections": [
            {"label": label, "confidence": conf, "bbox": [cx - w / 2, bottom - h, cx + w / 2, bottom]}]})
    return DetectionsResp.model_validate({"fps": fps, "video_shape": [H, W], "frames": frames})


def test_pedestrian_ahead_growing_fast_is_kept_with_plain_note():
    r = closing_on_us(growing(rate=1.8, n=45), ALL, "front")  # 1.5 s at 1.8x/s
    assert r is not None and r.passed is True and r.score >= 0.3
    assert r.note.startswith("a pedestrian ahead grew ") and " s from the front of the bus" in r.note
    assert r.gap_series == []


def test_constant_size_box_is_not_kept():
    r = closing_on_us(growing(rate=1.0), ALL, "front")
    assert r is not None and r.passed is False and r.note == "1 road user tracked, none closing on us fast enough"


def test_slow_growth_fails_but_short_ttc_passes():
    slow = closing_on_us(growing(rate=1.05, n=60), ALL, "front")  # ~5% per second: TTC ~20 s
    assert slow.passed is False
    # 0.63 s seen at 1.5x/s: growth 1.29 (< 1.35) but scale over 0.5 s gives TTC ~2.3 s
    fast_ttc = closing_on_us(growing(rate=1.5, n=20), ALL, "front")
    assert fast_ttc.passed is True and "about 2 s from the front of the bus" in fast_ttc.note
    # under the TTC span (0.37 s) a short burst cannot pass on TTC alone
    assert closing_on_us(growing(rate=1.5, n=12), ALL, "front").passed is False


def test_outside_the_lane_zone_is_ignored_for_front_but_counts_nearside():
    side = growing(label="bicycle", cx=150, rate=1.8, n=45)  # far left of frame
    assert closing_on_us(side, ALL, "front").passed is False
    near = closing_on_us(side, ALL, "nearside")
    assert near.passed is True and near.note.startswith("a cyclist alongside grew ")
    assert "the side of the bus" in near.note


def test_box_high_in_frame_is_not_in_lane_zone():
    far = growing(rate=1.8, n=45, bottom=300.0)  # bottom edge above the zone line
    assert closing_on_us(far, ALL, "front").passed is False


def test_no_frames_returns_none_and_unknown_shape_defaults():
    assert closing_on_us(None, ALL, "front") is None
    assert closing_on_us(DetectionsResp(frames=[]), ALL, "front") is None
    d = growing(rate=1.8, n=45)
    d.video_shape = None  # falls back to 1080p frame size
    assert closing_on_us(d, ALL, "front").passed is True


def test_vehicle_class_filter_applies():
    car = growing(label="car", rate=1.8, n=45)
    assert closing_on_us(car, frozenset({"person"}), "front").passed is False
    assert closing_on_us(car, ALL, "front").note.startswith("a car ahead grew")
