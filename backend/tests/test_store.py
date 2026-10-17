from sixthsense.contracts import Incident, ModeMetrics
from sixthsense.store import JsonStore, load_seed


def inc(i: str, run_id: str, mode="road", risk=3, came_true="yes") -> Incident:
    return Incident(id=i, mode=mode, run_id=run_id, risk=risk, came_true=came_true, source=f"s3://b/{i}")


def metrics(run_id: str, mode="road", at="2026-10-17T13:00:00+01:00") -> ModeMetrics:
    return ModeMetrics(mode=mode, run_id=run_id, verified=1, checked=1, came_true_yes=1, accuracy=1.0, generated_at=at)


async def test_sample_until_first_run_and_fixtures_never_feed_metrics(tmp_path):
    store = JsonStore(tmp_path / "s.json", load_seed(None))
    road = await store.list_incidents("road")
    assert road and all(i.fixture for i in road)
    assert await store.metrics() == []


async def test_upsert_is_idempotent_and_latest_run_wins(tmp_path):
    store = JsonStore(tmp_path / "s.json", load_seed(None))
    await store.save_run(metrics("r1", at="2026-10-17T13:00:00+01:00"), [inc("a", "r1"), inc("b", "r1")])
    await store.save_run(metrics("r1", at="2026-10-17T13:00:00+01:00"), [inc("a", "r1"), inc("b", "r1")])
    assert [i.id for i in await store.list_incidents("road")] == ["a", "b"]
    await store.save_run(metrics("r2", at="2026-10-17T14:00:00+01:00"), [inc("a", "r2", risk=5)])
    road = await store.list_incidents("road")
    assert [(i.id, i.risk, i.run_id) for i in road] == [("a", 5, "r2")]
    assert [m.run_id for m in await store.metrics()] == ["r2"]
    # street has no run yet -> still Sample
    assert all(i.fixture for i in await store.list_incidents("street"))
    assert (await store.get_incident("a")).risk == 5


def test_payload_round_trips_for_every_fixture():
    for i in load_seed(None):
        assert Incident.model_validate_json(i.model_dump_json()) == i
