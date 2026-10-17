"""Ego "closing on us" check for vehicle-mounted cameras, on synthetic growing boxes."""

from sixthsense.clients.vss import DetectionsResp
from sixthsense.modes import MODES, VEHICLES, VULNERABLE
from sixthsense.pipeline import Verification, bus_prompt, retarget_ego
from sixthsense.tracking import closing_on_us, ego_diagnostics, growth_min

ALL = VEHICLES | VULNERABLE
W, H = 1920, 1080


def box(label, cx, h, bottom, conf, aspect=None):
    w = h * (aspect or (0.4 if label == "person" else 1.6))
    return {"label": label, "confidence": conf, "bbox": [cx - w / 2, bottom - h, cx + w / 2, bottom]}


def growing(label="person", cx=960, h0=300.0, rate=1.0, n=60, fps=30, bottom=900.0, conf=0.8, extra=None,
            spike_at=None, conf_after=None):
    """One box whose height grows `rate`x per second (rate=1 = constant), anchored at `bottom`."""
    frames = []
    for i in range(n):
        t = i / fps
        h = h0 * rate**t
        if spike_at is not None and i == spike_at:
            h *= 13.2  # one jittery detection
        c = conf_after if conf_after is not None and i >= 3 else conf
        dets = [box(label, cx, min(h, bottom), bottom, c)]
        if extra:
            dets.append(extra(i))
        frames.append({"frame_index": i, "time_sec": t, "detections": dets})
    return DetectionsResp.model_validate({"fps": fps, "video_shape": [H, W], "frames": frames})


# ---------- the gate ----------
def test_pedestrian_ahead_closing_fast_is_kept_with_plain_note():
    r = closing_on_us(growing(rate=1.8, n=45), ALL, "front")  # 1.5 s at 1.8x/s -> ~2.3x
    assert r.passed is True and r.score >= 0.5
    assert r.note.startswith("a pedestrian ahead grew 2.") and "s from the front of the bus" in r.note
    assert r.gap_series == [] and "person" in r.passing


def test_constant_size_box_is_not_kept():
    r = closing_on_us(growing(rate=1.0), ALL, "front")
    assert r.passed is False and r.note == "1 road user tracked, none closing on us fast enough"


def test_growth_gate_is_per_class_and_inclusive():
    # 1.25x/s over 1.2 s -> ~1.3x: below the vehicle gate (1.4x), above the person gate (1.25x)
    car = ego_diagnostics(growing(label="car", h0=250, rate=1.25, n=36), ALL, "front")[0]
    assert car.reason == "growth 1.27x < 1.4x"
    person = ego_diagnostics(growing(rate=1.25, n=36), ALL, "front")[0]
    assert person.reason == "pass" and person.rule == "growth"
    # exactly at the gate passes (>=): 1.4x for a car over the window
    assert growth_min("car") == 1.4 and growth_min("person") == growth_min("bicycle") == 1.25


def test_span_floor_is_per_class():
    # vehicles: 0.6 s / 6 frames. At 8 fps the tracker confirms from frame 2: 7 frames = 6 tracked
    assert closing_on_us(growing(label="car", h0=250, rate=3.0, n=7, fps=8), ALL, "front").passed is True
    assert closing_on_us(growing(label="car", h0=250, rate=3.0, n=6, fps=8), ALL, "front").passed is False
    # people: 0.5 s / 12 frames. 15 frames at 30 fps = 14 tracked over 0.43 s: too short
    assert ego_diagnostics(growing(rate=3.0, n=15), ALL, "front")[0].reason.startswith("short span")
    assert closing_on_us(growing(rate=3.0, n=17), ALL, "front").passed is True  # 16 tracked, 0.5 s


def test_growth_alone_needs_ttc_or_a_near_box():
    # steady growth over 2 s: ~1.66x but TTC ~ 3.6 s and the box ends at 23% of frame height
    slow = closing_on_us(growing(label="car", rate=1.3, n=60, h0=150), ALL, "front")
    assert slow.passed is False
    # same growth, but the box ends at ~31% of the frame height -> close enough
    near = closing_on_us(growing(label="car", rate=1.3, n=60, h0=200), ALL, "front")
    assert near.passed is True and near.note.endswith("of the frame height), now close")


def test_single_jitter_spike_does_not_count():
    r = closing_on_us(growing(rate=1.0, spike_at=40), ALL, "front")
    assert r.passed is False


def test_tiny_start_and_low_confidence_tracks_are_ignored():
    tiny = closing_on_us(growing(rate=1.8, n=45, h0=60), ALL, "front")  # starts at ~0.07% of frame
    assert tiny.passed is False and tiny.note.startswith("0 road users")
    # born at 0.9, then the detector drops to 0.28 (still matched in ByteTrack's second stage)
    unsure = growing(rate=1.8, n=45, conf=0.9, conf_after=0.28)
    d = ego_diagnostics(unsure, ALL, "front")[0]
    assert d.reason.startswith("unsure conf") and d.mean_conf < 0.35
    assert closing_on_us(unsure, ALL, "front").passed is False


def test_lane_zone_front_vs_nearside():
    side = growing(label="bicycle", cx=200, rate=1.8, n=45, h0=200)
    assert closing_on_us(side, ALL, "front").passed is False
    near = closing_on_us(side, ALL, "nearside")
    assert near.passed is True and near.note.startswith("a cyclist alongside grew ")
    assert "the side of the bus" in near.note
    high = growing(rate=1.8, n=45, bottom=420.0, h0=150)  # bottom edge above the zone line
    assert closing_on_us(high, ALL, "front").passed is False


def test_nearside_ignores_the_riders_own_handlebars_and_wheel():
    # handlebars: a wide box glued to the bottom of the frame that "grows" as the rider moves
    bars = growing(label="bicycle", cx=960, rate=1.8, n=45, h0=200, bottom=1080.0)
    assert closing_on_us(bars, ALL, "nearside").passed is False
    wide = growing(label="bicycle", cx=960, rate=1.8, n=45, h0=500, bottom=900.0)  # > 45% of frame width
    assert closing_on_us(wide, ALL, "nearside").passed is False
    # the front camera keeps boxes near the bottom (a close pedestrian may touch it)
    assert closing_on_us(growing(rate=1.8, n=45, bottom=1080.0), ALL, "front").passed is True


def test_no_frames_returns_none_and_unknown_shape_defaults():
    assert closing_on_us(None, ALL, "front") is None
    assert closing_on_us(DetectionsResp(frames=[]), ALL, "front") is None
    d = growing(rate=1.8, n=45)
    d.video_shape = None  # falls back to 1080p frame size
    assert closing_on_us(d, ALL, "front").passed is True


def test_vehicle_class_filter_applies():
    car = growing(label="car", rate=1.8, n=45, h0=200)
    assert closing_on_us(car, frozenset({"person"}), "front").passed is False
    assert closing_on_us(car, ALL, "front").note.startswith("a car ahead grew")


# ---------- hazard-matched note ----------
def _ver_for(det):
    r = closing_on_us(det, ALL, "front")
    return Verification(verified=bool(r.passed), verify_score=r.score, verify_note=r.note,
                        verify_by="yolo boxes (closing on us)", ego_passing=r.passing)


def test_pedestrian_hazard_cites_the_pedestrian_not_the_car():
    # a car grows faster (would be cited by default) but a pedestrian also passes
    car = lambda i: box("car", 1300, 200 * 2.2 ** (i / 30), 900, 0.9)  # noqa: E731
    ver = _ver_for(growing(rate=1.8, n=45, cx=700, extra=car))
    assert ver.verified and ver.verify_note.startswith("a car ahead")
    out = retarget_ego(ver, "Pedestrian stepping out")
    assert out.verified and out.verify_note.startswith("a pedestrian ahead")
    assert retarget_ego(ver, "Vehicle cutting in").verify_note.startswith("a car ahead")  # names no class


def test_cyclist_hazard_with_only_a_car_closing_names_the_closest_road_user():
    ver = _ver_for(growing(label="car", rate=1.8, n=45, h0=200))
    out = retarget_ego(ver, "Cyclist ahead")
    assert out.verified is True
    assert out.verify_note.startswith("a car ahead grew") and out.verify_note.endswith("(closest road user: car)")


# ---------- prompts and judge ----------
def test_prompts_demand_a_change_and_nearside_ignores_handlebars():
    near = bus_prompt(MODES["bus_nearside"])
    assert "handlebars" in near and "belong to" in near and "ignore them" in near
    for p in (near, bus_prompt(MODES["bus_front"])):
        assert "CHANGE" in p and "continues walking" in p and "reaches the bus's lane in about 2 s" in p


def test_diagnostics_explain_each_rejection():
    reasons = {
        "pass": growing(rate=1.8, n=45),
        "small": growing(rate=1.8, n=45, h0=60),
        "out-of-lane": growing(label="car", rate=1.8, n=45, bottom=420.0, h0=150),
        "far": growing(label="car", rate=1.3, n=60, h0=150),
    }
    for want, det in reasons.items():
        d = ego_diagnostics(det, ALL, "front")[0]
        assert d.reason.split(" ")[0] == want, (want, d)
        assert d.frames > 0 and 0 < d.start_h < 1


def crossing(start_x, end_x, seconds=1.3, fps=30, h=300.0, label="person", bottom=900.0):
    n = int(seconds * fps) + 1
    frames = [
        {"frame_index": i, "time_sec": i / fps,
         "detections": [box(label, start_x + (end_x - start_x) * i / (n - 1), h, bottom, 0.8)]}
        for i in range(n)
    ]
    return DetectionsResp.model_validate({"fps": fps, "video_shape": [H, W], "frames": frames})


def test_pedestrian_stepping_into_our_lane_passes_without_growth():
    r = closing_on_us(crossing(1700, 1300), ALL, "front")  # from the right edge into the lane (<= 1440)
    assert r.passed is True and r.note.startswith("a pedestrian stepped into the bus's path from the right in ")
    d = ego_diagnostics(crossing(1700, 1300), ALL, "front")[0]
    assert d.rule == "lane-entry"
    left = closing_on_us(crossing(150, 520, label="bicycle", h=200), ALL, "front")  # to within 5% of 480
    assert left.passed is True and left.note.startswith("a cyclist moved into the bus's path from the left")


def test_lane_entry_needs_people_front_camera_and_real_movement():
    assert closing_on_us(crossing(1700, 1300, label="car", h=200), ALL, "front").passed is False
    nearside = ego_diagnostics(crossing(1700, 1300), ALL, "nearside")[0]
    assert nearside.rule != "lane-entry"
    assert closing_on_us(crossing(1700, 1650), ALL, "front").passed is False  # never reaches the lane
    # drifts 100 px over 3 s: never 5% of the width within 2 s (jitter, not a step)
    assert closing_on_us(crossing(1520, 1420, seconds=3.0), ALL, "front").passed is False
    assert closing_on_us(crossing(1700, 1300, bottom=400.0, h=150), ALL, "front").passed is False  # far, high


def test_growth_window_reports_its_own_heights_on_a_shrinking_track():
    # a box that grows for 1 s then shrinks: growth and heights come from the rising part only
    frames = []
    for i in range(60):
        t = i / 30
        h = 200 * (2.0 ** t if t <= 1 else 2.0 * 0.5 ** (t - 1))
        frames.append({"frame_index": i, "time_sec": t, "detections": [box("car", 960, h, 900, 0.9)]})
    det = DetectionsResp.model_validate({"fps": 30, "video_shape": [H, W], "frames": frames})
    d = ego_diagnostics(det, ALL, "front")[0]
    assert d.end_h > d.start_h and abs(d.end_h / d.start_h - d.growth) < 0.01
    r = closing_on_us(det, ALL, "front")
    assert f"({d.start_h:.0%} to {d.end_h:.0%} of the frame height)" in r.note
