"""Loader tests on a tiny SYNTHETIC ATD (made-up numbers, 2 slots per team)."""
import numpy as np
import pytest

from pipeline import data

META = """<?xml version="1.0"?>
<Metadata>
  <Teams>
    <Team id="T1"><Name>Home FC</Name></Team>
    <Team id="T2"><Name>Away FC</Name></Team>
  </Teams>
  <Players>
    <Player id="P1" teamId="T1"/><Player id="P2" teamId="T1"/>
    <Player id="P3" teamId="T2"/><Player id="P4" teamId="T2"/>
  </Players>
</Metadata>
"""
RAW = (
    "1:0.5,0.5,1.0;0.1,0.2,2.0;0.9,0.8,3.0;NaN,NaN,NaN:0.25,0.5,10.0\n"
    "2:0.5,0.5,1.5;0.1,0.2,2.5;0.9,0.8,3.5;0.3,0.4,4.0:NaN,NaN,NaN\n"
    "4:0.0,1.0,0.0;0.0,0.0,0.0;1.0,1.0,0.0;1.0,0.0,0.0:1.0,1.0,5.0\n"
)


@pytest.fixture
def paths(tmp_path):
    meta, raw = tmp_path / "m.xml", tmp_path / "r.txt"
    meta.write_text(META)
    raw.write_text(RAW)
    return str(meta), str(raw)


def test_shapes_and_teams(paths):
    d = data.load_barath(*paths)
    assert d["ball_xy"].shape == (4, 2)
    assert d["players_xy"].shape == (4, 4, 2)
    assert d["players_speed"].shape == (4, 4)
    assert d["slot_team"].tolist() == [0, 0, 1, 1]
    assert d["halves"].shape == (2, 3)


def test_metres_and_index(paths):
    d = data.load_barath(*paths, pitch=(100.0, 50.0))
    assert d["ball_xy"][0].tolist() == [25.0, 25.0]  # frame_id 1 -> row 0
    assert d["ball_speed"][0] == 10.0
    assert d["players_xy"][0, 1].tolist() == [10.0, 10.0]
    assert d["players_xy"][3, 3].tolist() == [100.0, 0.0]  # frame_id 4 -> row 3


def test_nan_handling(paths):
    d = data.load_barath(*paths)
    assert d["ball_seen"].tolist() == [True, False, False, True]
    assert np.isnan(d["ball_xy"][1]).all() and np.isnan(d["ball_speed"][1])
    assert np.isnan(d["players_xy"][0, 3]).all()  # missing slot
    assert np.isnan(d["players_xy"][2]).all()  # frame 3 absent from file


def test_n_frames_truncates_and_pads(paths):
    assert data.load_barath(*paths, n_frames=2)["ball_xy"].shape == (2, 2)
    assert data.load_barath(*paths, n_frames=6)["ball_seen"].shape == (6,)


def test_cache_round_trip(paths, tmp_path):
    d = data.load_barath(*paths)
    p = str(tmp_path / "c.npz")
    data.save_cache(d, p)
    e = data.load_cache(p)
    assert set(e) == set(d)
    for k in d:
        np.testing.assert_array_equal(e[k], d[k])


def test_partial_ball_group_counts_as_unseen(tmp_path):
    meta, raw = tmp_path / "m.xml", tmp_path / "r.txt"
    meta.write_text(META)
    raw.write_text("1:0.5,0.5,1.0;0.1,0.2,2.0;0.9,0.8,3.0;0.3,0.4,4.0:0.5,NaN,7.0\n")
    d = data.load_barath(str(meta), str(raw))
    assert d["ball_seen"].tolist() == [False]
    assert np.isnan(d["ball_xy"]).all()


def test_fps_and_default_pitch_come_from_games(paths):
    import games
    d = data.load_barath(*paths)
    assert float(d["fps"]) == games.GAMES[games.GAME]["fps"]
    assert data.DEFAULT_PITCH == games.GAMES[games.GAME]["pitch"]


def test_load_match_dispatches_to_barath(paths):
    d = data.load_match("barath", *paths)
    assert d["ball_xy"].shape == (4, 2)
    with pytest.raises(ValueError):
        data.load_match("nope")
