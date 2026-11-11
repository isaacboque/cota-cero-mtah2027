from types import SimpleNamespace as NS

import numpy as np
import pytest

from external import idsse


class Obj:
    """Hashable by identity, like kloppy's Player."""


class State:
    """Stands in for kloppy's BallState enum member (has .name)."""
    def __init__(self, name):
        self.name = name


def _fake():
    h1, h2, a1 = Obj(), Obj(), Obj()
    teams = [NS(players=[h1, h2]), NS(players=[a1])]
    pt = lambda x, y: NS(x=x, y=y)
    pd = lambda x, y: NS(coordinates=pt(x, y), speed=1.0)
    p1, p2 = NS(id=1), NS(id=2)
    frames = [
        NS(ball_state=State("ALIVE"), ball_owning_team=teams[0], ball_coordinates=pt(.5, .5),
           ball_speed=2.0, period=p1, players_data={h1: pd(.1, .2), a1: pd(.9, .8)}),
        NS(ball_state=State("ALIVE"), ball_owning_team=teams[1], ball_coordinates=pt(.5, .5),
           ball_speed=2.0, period=p1, players_data={h1: pd(.1, .2)}),
        NS(ball_state=State("DEAD"), ball_owning_team=teams[1], ball_coordinates=pt(0, 0),
           ball_speed=0.0, period=p2, players_data={}),
    ]
    meta = NS(teams=teams, frame_rate=25.0, pitch_dimensions=NS(pitch_length=100.0, pitch_width=50.0))
    return NS(metadata=meta, frames=frames)


def test_from_dataset():
    d = idsse.from_dataset(_fake())
    assert d["gt_codes"].tolist() == [0, 1, 2]  # dead frame is D even though 'owner' is away
    assert d["slot_team"].tolist() == [0, 0, 1]
    assert d["players_xy"].shape == (3, 3, 2)
    assert d["players_xy"][0, 0].tolist() == [10.0, 10.0]
    assert np.isnan(d["players_xy"][1, 2]).all()
    assert d["ball_xy"][0].tolist() == [50.0, 25.0]
    assert d["halves"].tolist() == [[1, 0, 1], [2, 2, 2]]


def test_unknown_ball_state_is_not_dead():
    ds = _fake()
    ds.frames[2].ball_state = None
    assert idsse.from_dataset(ds)["gt_codes"].tolist() == [0, 1, -1]


@pytest.mark.idsse
def test_j03wpy():
    d = idsse.load_idsse("J03WPY")
    assert float(d["fps"]) == 25.0
    n = len(d["gt_codes"])
    assert d["players_xy"].shape[0] == n and d["ball_xy"].shape == (n, 2)
    assert all((d["gt_codes"] == c).sum() > 0 for c in (0, 1, 2))


def test_load_idsse_parses_once_then_reads_cache(tmp_path, monkeypatch):
    calls = []

    def fake_raw(match_id, cache_dir):
        calls.append(match_id)
        return idsse.from_dataset(_fake())

    monkeypatch.setattr(idsse, "_load_raw", fake_raw)
    first = idsse.load_idsse("J03WPY", str(tmp_path))
    second = idsse.load_idsse("J03WPY", str(tmp_path))
    assert calls == ["J03WPY"]                      # the slow parse ran once
    assert idsse.cache_path("J03WPY", str(tmp_path)).endswith("J03WPY_arrays_v1.npz")
    assert set(first) == set(second)
    for k in first:
        np.testing.assert_array_equal(first[k], second[k])
    assert not list(tmp_path.glob("*.tmp.npz"))


def test_load_idsse_rebuilds_cache_when_xml_is_newer(tmp_path, monkeypatch):
    import os
    import time
    calls = []
    monkeypatch.setattr(idsse, "_load_raw",
                        lambda m, c: calls.append(m) or idsse.from_dataset(_fake()))
    idsse.load_idsse("J03WPY", str(tmp_path))
    xml = tmp_path / "J03WPY_tracking.xml"
    xml.write_text("<new/>")
    later = time.time() + 10
    os.utime(xml, (later, later))
    idsse.load_idsse("J03WPY", str(tmp_path))
    assert calls == ["J03WPY", "J03WPY"]
