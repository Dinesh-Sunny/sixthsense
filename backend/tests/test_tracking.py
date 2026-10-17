import math

from fakes import converging_frames
from sixthsense.clients.vss import DetectionsResp, Frame
from sixthsense.modes import CLOSE_CL, VEHICLES, VULNERABLE
from sixthsense.tracking import closing_gap, to_detections

CITY = VEHICLES | VULNERABLE


def det(frames, fps=30):
    return DetectionsResp.model_validate({"fps": fps, "frames": frames})


def test_converging_pair_verifies_with_gap_series():
    r = closing_gap(det(converging_frames()))
    assert r is not None and r.score > 0.3
    assert "closed from" in r.note
    assert r.gap_series and r.gap_series[0].t == 0.0
    assert min(p.cl for p in r.gap_series) <= CLOSE_CL
    assert r.gap_series[0].cl > r.gap_series[-1].cl


def test_mid_confidence_box_gets_a_track():
    # conf 0.5 is below trackers' defaults (0.7 activation / 0.6 high-conf); our thresholds keep it.
    r = closing_gap(det(converging_frames(conf=0.5)))
    assert r is not None and r.score > 0.3


def test_parallel_pair_is_not_verified():
    r = closing_gap(det(converging_frames(speed=0)))
    assert r is not None and r.score == 0.0
    assert "no pair closing" in r.note


def test_no_frames_returns_none():
    assert closing_gap(det([])) is None
    assert closing_gap(None) is None


def test_empty_frame_mid_clip_keeps_the_pair():
    frames = converging_frames()
    for f in frames[60:63]:
        f["detections"] = []
    r = closing_gap(det(frames))
    assert r is not None and r.score > 0.3


def test_non_vehicle_pairs_are_ignored():
    frames = [
        {
            "frame_index": i,
            "time_sec": i / 30,
            "detections": [
                {"label": "person", "confidence": 0.9, "bbox": [100 + i * 3, 500, 140 + i * 3, 600]},
                {"label": "bicycle", "confidence": 0.9, "bbox": [700, 500, 760, 600]},
            ],
        }
        for i in range(150)
    ]
    r = closing_gap(det(frames), CITY)
    assert r is not None and r.score == 0.0


def test_person_and_car_pair_verifies_in_city():
    frames = [
        {
            "frame_index": i,
            "time_sec": i / 30,
            "detections": [
                {"label": "person", "confidence": 0.8, "bbox": [100 + i * 3, 500, 140 + i * 3, 600]},
                {"label": "car", "confidence": 0.9, "bbox": [700, 500, 900, 600]},
            ],
        }
        for i in range(150)
    ]
    r = closing_gap(det(frames), CITY)
    assert r is not None and r.score > 0.3 and "pedestrian" in r.note
    # road mode does not track people at all
    assert closing_gap(det(frames), VEHICLES).score == 0.0


def test_builder_drops_bad_boxes_and_unknown_labels():
    f = Frame.model_validate(
        {
            "detections": [
                {"label": "car", "confidence": 0.9, "bbox": [0, 0, 10, 10]},
                {"label": "car", "confidence": 0.9, "bbox": [10, 0, 5, 10]},  # inverted
                {"label": "car", "confidence": 0.9, "bbox": [0, math.nan, 10, 10]},
                {"label": "car", "confidence": 0.1, "bbox": [0, 0, 10, 10]},  # below MIN_DET_CONF
                {"label": "giraffe", "confidence": 0.9, "bbox": [0, 0, 10, 10]},
                {"label": "person", "confidence": 0.9, "bbox": [0, 0, 10, 10]},  # not allowed in road
            ]
        }
    )
    d = to_detections(f, VEHICLES)
    assert len(d) == 1 and d.data["class_name"].tolist() == ["car"]
    assert len(to_detections(Frame(), VEHICLES)) == 0


def test_tracker_is_fresh_per_clip():
    a = closing_gap(det(converging_frames()))
    b = closing_gap(det(converging_frames()))
    assert a is not None and b is not None and a.note == b.note
