import numpy as np

from pipeline import decode
from tests.test_v2 import _scene

H, A, D = 0, 1, 2


def _emis(path, strength=3.0):
    e = np.zeros((len(path), 3))
    e[np.arange(len(path)), path] = strength
    return e


def _costs(n, sw=-1.0, ex=-1.0):
    return np.full((n, 2), sw), np.full((n, 2), ex)


def test_viterbi_recovers_known_path():
    truth = np.array([H] * 30 + [A] * 40 + [D] * 30 + [H] * 20)
    sw, ex = _costs(len(truth))
    out = decode.viterbi_dwell(_emis(truth), 5, 5, sw, ex, -1.0)
    assert np.array_equal(out, truth)


def test_min_dwell_removes_flicker():
    truth = np.array([H] * 60)
    emis = _emis(truth, 1.0)
    emis[30:33] = _emis(np.array([A] * 3), 1.0)  # 3-frame blip toward A
    sw, ex = _costs(60, sw=-0.1, ex=-0.1)
    short = decode.viterbi_dwell(emis, 1, 1, sw, ex, -0.1)
    assert (short[30:33] == A).all()           # without dwell the blip is decoded
    out = decode.viterbi_dwell(emis, 10, 10, sw, ex, -0.1)
    assert (out == H).all()                     # with dwell it cannot be
    cut = np.flatnonzero(out[1:] != out[:-1])
    assert len(cut) == 0


def test_runs_never_shorter_than_dwell():
    rng = np.random.default_rng(0)
    emis = rng.normal(size=(400, 3))
    sw, ex = _costs(400, -0.2, -0.2)
    out = decode.viterbi_dwell(emis, 12, 8, sw, ex, -0.2)
    cut = np.flatnonzero(out[1:] != out[:-1]) + 1
    b = np.concatenate(([0], cut, [400]))
    assert (np.diff(b) >= 8).all()


def test_merge_short_runs():
    path = np.array([0] * 10 + [1] * 2 + [0] * 10 + [2] * 3 + [1] * 10, dtype=np.int8)
    out = decode.merge_short_runs(path, 5)
    assert out[:22].tolist() == [0] * 22  # the 2-frame blip is absorbed
    cut = np.flatnonzero(out[1:] != out[:-1]) + 1
    b = np.concatenate(([0], cut, [len(out)]))
    assert (np.diff(b) >= 5).all()


def test_predict_v3_follows_control_and_carries_through_missing_ball():
    d = _scene([(50, 200, 0), (300, 450, 2)])
    d["ball_seen"][100:120] = False
    d["ball_xy"][100:120] = np.nan
    out = decode.predict_v3(d, kickoff_2nd=None, params={"MIN_DWELL_HA_S": 0.4, "MIN_DWELL_D_S": 0.4})
    assert (out[60:200] == decode.H).all()          # carries through the missing ball
    assert (out[320:450] == decode.A).all()          # switches after the other team's control
    assert set(np.unique(out)) <= {H, A, D}


def test_predict_v3_hard_dead_outside_halves_and_pre_kickoff():
    halves = [[1, 100, 299], [2, 400, 599]]
    d = _scene([(100, 600, 0)], halves=halves)
    out = decode.predict_v3(d, kickoff_2nd=450, params={"MIN_DWELL_HA_S": 0.4, "MIN_DWELL_D_S": 0.4})
    assert (out[:100] == D).all() and (out[300:400] == D).all()
    assert (out[400:450] == D).all()
    assert (out[470:600] == H).all()


def test_restart_cue_picks_team_after_dead_ball():
    # long dead stretch 150-300 (ball out of bounds), then BOTH teams are near; cue names away
    n = 500
    d = _scene([(320, 500, 2), (310, 500, 0)])
    d["ball_xy"][150:300] = [-5.0, 30.0]
    d["ball_xy"][300:] = d["ball_xy"][300:] * 0 + [40.0, 30.0]
    out = decode.predict_v3(d, kickoff_2nd=None, restarts=[(305, 1, "throw_in")],
                            params={"MIN_DWELL_HA_S": 0.4, "MIN_DWELL_D_S": 0.4})
    assert (out[170:290] == D).all()
    assert out[n - 1] in (H, A)
