from fakes import hit
from sixthsense.clients.vss import Segment
from sixthsense.modes import BUS_HAZARD_TYPES, MODE_NAMES, MODES
from sixthsense.pipeline import Candidate, bus_hazard_type, bus_prompt, round_robin


def cand(i: int, q: str, parent: str, desc: str) -> Candidate:
    h = {**hit(i, parent), "reasoning_content": desc}
    return Candidate(hit=Segment.model_validate(h), query=q)


def test_bus_mode_config():
    assert "bus" in MODE_NAMES
    cfg = MODES["bus"]
    assert len(cfg["queries"]) == 8 and len(set(cfg["queries"])) == 8
    assert set(MODES["city"]["cameras"]) | set(MODES["street"]["cameras"]) == set(cfg["cameras"])
    prompt = bus_prompt(cfg)
    assert "London bus safety analyst" in prompt and "Scooter weaving" in prompt
    assert all(t in prompt for t in BUS_HAZARD_TYPES)


def test_view_prompts_frame_the_camera_and_use_their_hazard_set():
    front, near = bus_prompt(MODES["bus_front"]), bus_prompt(MODES["bus_nearside"])
    assert "front camera" in front and "bonnet" in front and "Braking ahead" in front
    assert "nearside camera" in near and "Bus stop crowd" in near and "Braking ahead" not in near
    for p in (front, near):
        assert "{" not in p.replace("{{", "").split("Answer in JSON only")[0]  # fully formatted
    assert MODES["bus_front"]["cameras"] == ["pie_cam-3"] and MODES["bus_front"]["view"] == "front"
    assert MODES["bus_nearside"]["cameras"] == ["nyc_bike_gopro-1"] and MODES["bus_nearside"]["view"] == "nearside"
    assert len(MODES["bus_front"]["queries"]) == 8 and len(MODES["bus_nearside"]["queries"]) == 6
    assert bus_hazard_type("braking ahead", MODES["bus_front"]["hazard_types"]) == "Braking ahead"


def test_cli_accepts_limit_up_to_60():
    import pytest

    from sixthsense.cli import main

    with pytest.raises(SystemExit):
        main(["run", "--mode", "bus_front", "--limit", "61"])


def test_round_robin_covers_each_query_and_skips_near_duplicates():
    cands = [
        cand(0, "a", "s3://b/v1.mp4", "a cyclist beside a white truck"),
        cand(1, "a", "s3://b/v1.mp4", "next segment of the same scene"),  # adjacent segment -> dup
        cand(5, "a", "s3://b/v3.mp4", "a red car parks on the left"),
        cand(0, "b", "s3://b/v2.mp4", "a cyclist beside a white truck!"),  # same text -> dup
        cand(9, "b", "s3://b/v2.mp4", "a woman steps off the kerb near a bus stop"),
    ]
    out = round_robin(cands, ["a", "b"])
    assert [(c.query, c.hit.description) for c in out] == [
        ("a", "a cyclist beside a white truck"),
        ("b", "a woman steps off the kerb near a bus stop"),
        ("a", "a red car parks on the left"),
    ]


def test_hazard_type_snaps_to_fixed_set():
    assert bus_hazard_type("cyclist on the nearside.") == "Cyclist on the nearside"
    assert bus_hazard_type("Pedestrian stepping-out") == "Pedestrian stepping out"
    assert bus_hazard_type("something else entirely") == "something else entirely"
