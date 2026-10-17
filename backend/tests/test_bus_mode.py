from fakes import hit
from sixthsense.clients.vss import Segment
from sixthsense.modes import BUS_HAZARD_TYPES, MODE_NAMES, MODES
from sixthsense.pipeline import FORESEE_BUS, Candidate, bus_hazard_type, round_robin


def cand(i: int, q: str, parent: str, desc: str) -> Candidate:
    h = {**hit(i, parent), "reasoning_content": desc}
    return Candidate(hit=Segment.model_validate(h), query=q)


def test_bus_mode_config():
    assert "bus" in MODE_NAMES
    cfg = MODES["bus"]
    assert len(cfg["queries"]) == 8 and len(set(cfg["queries"])) == 8
    assert set(MODES["city"]["cameras"]) | set(MODES["street"]["cameras"]) == set(cfg["cameras"])
    prompt = FORESEE_BUS.format(types=", ".join(BUS_HAZARD_TYPES), horizon=cfg["horizon"])
    assert "London bus safety analyst" in prompt and "Scooter weaving" in prompt


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
