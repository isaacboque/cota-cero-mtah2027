import numpy as np

from pipeline import config, deadball, features


def _d(n, ball=None, seen=None, players=None, halves=None):
    ball = np.tile([50.0, 30.0], (n, 1)) if ball is None else ball
    seen = np.ones(n, bool) if seen is None else seen
    if players is None:
        players = np.zeros((n, 4, 2))
        players[:, :, 0] = np.array([10.0, 20.0, 80.0, 90.0])
        players[:, :, 1] = 30.0
    return {"ball_xy": ball.astype(float), "ball_seen": seen, "players_xy": players,
            "slot_team": np.array([0, 0, 1, 1], dtype=np.int8),
            "halves": np.array([[1, 0, n - 1]]) if halves is None else halves}


def test_features_distances_and_counts():
    d = _d(5)
    d["players_xy"][:, 0] = [52.0, 30.0]  # home player 2 m from ball
    f = features.compute_features(d)
    assert np.allclose(f["d_home"], 2.0)
    assert np.allclose(f["d_away"], 30.0)
    assert np.allclose(f["gap"], 28.0)
    assert (f["n_home_r"] == 1).all() and (f["n_away_r"] == 0).all()


def test_features_speed_and_missing_run():
    n = 6
    ball = np.zeros((n, 2))
    ball[:, 0] = np.arange(n) * 0.4  # 0.4 m/frame = 10 m/s
    seen = np.array([1, 1, 0, 0, 1, 1], bool)
    ball[~seen] = np.nan
    f = features.compute_features(_d(n, ball=ball, seen=seen))
    assert np.isclose(f["ball_speed"][1], 10.0)
    assert np.isnan(f["ball_speed"][2]) and np.isnan(f["ball_speed"][4])
    assert f["missing_run"].tolist() == [0, 0, 1, 2, 0, 0]


def test_features_oob_with_margin():
    ball = np.array([[50, 30], [-0.3, 30], [-1.0, 30], [50, 70.0]])
    f = features.compute_features(_d(4, ball=ball))
    assert f["oob"].tolist() == [False, False, True, True]


def test_hysteresis_ignores_blips_and_holds():
    raw = np.zeros(60, bool)
    raw[10:12] = True   # blip shorter than enter
    raw[20:40] = True   # real
    raw[30] = False     # one-frame dropout inside stays on
    out = deadball.hysteresis(raw, 5, 10)
    assert not out[10:12].any()
    assert out[20:40].all()
    assert not out[40:].any()


def test_oob_rule_marks_dead():
    n = 200
    ball = np.tile([50.0, 30.0], (n, 1))
    ball[80:120] = [-3.0, 30.0]
    d = _d(n, ball=ball)
    m = deadball.dead_mask(d, kickoff_2nd=None)
    assert m[85:115].all() and not m[:70].any() and not m[140:].any()


def test_global_slowdown_rule():
    n = 400
    ball = np.tile([50.0, 30.0], (n, 1))
    pl = np.zeros((n, 4, 2))
    pl[:, :, 1] = 30.0
    x = np.array([10.0, 20.0, 80.0, 90.0])
    pl[:, :, 0] = x
    pl[:150, :, 0] += np.arange(150)[:, None] * 0.2  # 5 m/s, then everyone stands still
    d = _d(n, ball=ball, players=pl)
    m = deadball.dead_mask(d, kickoff_2nd=None)
    assert m[260:].all() and not m[:100].any()


def test_slowdown_shorter_than_min_is_ignored():
    n = 400
    pl = np.zeros((n, 4, 2))
    pl[:, :, 1] = 30.0
    pl[:, :, 0] = np.array([10.0, 20.0, 80.0, 90.0]) + (np.arange(n)[:, None] * 0.1)
    pl[200:230, :, 0] = pl[200, :, 0]  # 1.2 s standstill < 4 s
    ball = np.tile([50.0, 30.0], (n, 1))
    ball[:, 0] += np.arange(n) * 0.1
    d = _d(n, players=pl, ball=ball)
    assert not deadball.dead_mask(d, kickoff_2nd=None).any()


def test_missing_run_ending_static():
    n = 300
    seen = np.ones(n, bool)
    seen[50:200] = False
    ball = np.tile([50.0, 30.0], (n, 1))
    ball[~seen] = np.nan
    pl = np.zeros((n, 4, 2))
    pl[:, :, 1] = 30.0
    pl[:, :, 0] = np.array([10.0, 20.0, 80.0, 90.0]) + (np.arange(n)[:, None] * 0.3)
    d = _d(n, ball=ball, seen=seen, players=pl)
    m = deadball.dead_mask(d, kickoff_2nd=None)
    assert m[60:190].all() and not m[:40].any()
    # same gap but the ball reappears moving: not dead
    ball2 = ball.copy()
    ball2[200:] = ball[200:] + np.arange(100)[:, None] * 0.5
    ball2[~seen] = np.nan
    d2 = _d(n, ball=ball2, seen=seen, players=pl)
    assert not deadball.dead_mask(d2, kickoff_2nd=None)[60:190].any()


def test_hard_dead_outside_halves_and_before_kickoff():
    halves = np.array([[1, 100, 199], [2, 300, 499]])
    h = deadball.hard_dead(600, halves, kickoff_2nd=350)
    assert h[:100].all() and h[200:300].all() and h[500:].all()
    assert h[300:350].all() and not h[350:500].any() and not h[100:200].any()
    h2 = deadball.hard_dead(600, halves, kickoff_2nd=None)
    assert not h2[300:500].any()


def test_default_kickoff_constant():
    assert config.KICKOFF_2ND == 113742
