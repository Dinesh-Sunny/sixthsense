import functools

import httpx

from fakes import FakeVSS
from sixthsense import cli
from sixthsense.main import Transports, open_resources


async def test_gate_debug_prints_one_line_per_candidate(settings, monkeypatch, capsys):
    fake = FakeVSS()
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(
        cli, "open_resources", functools.partial(open_resources, transports=Transports(vss=httpx.MockTransport(fake)))
    )
    assert await cli.gate_debug("bus_front", 3) == 0
    out = capsys.readouterr().out.strip().splitlines()
    rows = [line for line in out if line.startswith("[")]
    assert len(rows) == 1  # FakeVSS returns 2 adjacent segments of one video: near-duplicates, one kept
    assert "Pedestrian stepping out" in rows[0] and "growth" in rows[0] and "lane" in rows[0]
    assert out[-1].startswith("summary: ")
    assert not any(p.startswith("/agent") for p in fake.calls)  # search + detections only
    assert {"/search", "/videos/detections"} <= set(fake.calls)
    assert await cli.gate_debug("road", 3) == 2  # not an ego mode
