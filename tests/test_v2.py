import numpy as np

from pipeline import control, make_submission, report, v2

H, A, D = 0, 1, 2
N = 600


def _scene(plan, n=N, halves=None):
    """Ball on the x axis moving slowly; `plan` = [(start, stop, slot)] puts that slot 1 m from the
    ball for those rows. Slots 0,1 home, 2,3 away; others parked far away, moving to avoid the
    global slowdown rule."""
    t = np.arange(n)
    ball = np.stack([40.0 + 0.04 * t, np.full(n, 30.0)], axis=1)
    pl = np.zeros((n, 4, 2))
    pl[:, :, 1] = 10.0
    pl[:, :, 0] = np.array([5.0, 10.0, 95.0, 100.0]) + 0.04 * t[:, None]
    pl[:, :, 1] += 1.5 * np.sin(np.pi * t[:, None] / 25)  # ~3 m/s: team speed > slowdown threshold
    for a, b, s in plan:
        pl[a:b, s] = ball[a:b] + [1.0, 0.0]
    return {"ball_xy": ball, "ball_seen": np.ones(n, bool), "players_xy": pl,
            "slot_team": np.array([0, 0, 1, 1], dtype=np.int8),
            "halves": np.array([[1, 0, n - 1]] if halves is None else halves)}


def test_control_requires_min_frames():
    d = _scene([(100, 103, 0), (200, 260, 2)])
    ev = control.control_events(d)
    # row 200 is the teleport step; the centred velocity (VEL_LAG_FRAMES=3) sees it on rows 197-202
    assert [(f, t) for f, t, _ in ev] == [(203, 1)]


def test_one_frame_touch_does_not_flip():
    d = _scene([(50, 200, 0), (120, 121, 2)])
    out = v2.predict_v2(d, kickoff_2nd=None)
    assert (out[60:200] == H).all()


def test_possession_changes_on_other_team_control_and_loose_ball_keeps_last():
    d = _scene([(50, 200, 0), (300, 400, 2)])
    out = v2.predict_v2(d, kickoff_2nd=None)
    assert (out[60:200] == H).all()
    assert (out[220:290] == H).all()  # loose ball keeps last team
    assert (out[310:400] == A).all()


def test_ball_missing_carries_state():
    d = _scene([(50, 500, 0)])
    d["ball_seen"][150:170] = False
    d["ball_xy"][150:170] = np.nan
    out = v2.predict_v2(d, kickoff_2nd=None)
    assert (out[100:200] == H).all()


def test_dead_outside_halves_and_before_second_half_kickoff():
    halves = [[1, 100, 299], [2, 400, 599]]
    d = _scene([(100, 600, 0)], halves=halves)
    out = v2.predict_v2(d, kickoff_2nd=450)
    assert (out[:100] == D).all() and (out[300:400] == D).all()
    assert (out[400:450] == D).all()
    assert (out[460:600] == H).all()


def test_no_x_and_deterministic_sha(tmp_path):
    d = _scene([(50, 200, 0), (300, 400, 2)])
    a, b = v2.predict_v2(d, kickoff_2nd=None), v2.predict_v2(d, kickoff_2nd=None)
    assert set(np.unique(a)) <= {H, A, D}
    labels = np.array(["H", "A", "D"])
    p1 = make_submission.write_csv(str(tmp_path / "a.csv"), labels[a])
    p2 = make_submission.write_csv(str(tmp_path / "b.csv"), labels[b])
    assert make_submission.sha256(p1) == make_submission.sha256(p2)
    assert b"\r" not in open(p1, "rb").read()


def test_report_numbers():
    codes = np.array([0] * 50 + [2] * 10 + [1] * 10 + [0] * 5 + [2] * 5 + [3] * 0)
    halves = [[1, 0, 49], [2, 50, 79]]
    r = report.sanity(codes, halves)
    assert r["per_half"][0] == {"half": 1, "possessions": 1, "mean_duration_s": 2.0}
    assert r["per_half"][1]["possessions"] == 2
    assert r["runs_under_1s"] == 2 and r["stoppages"] == 2
    assert abs(r["d_share"] - 15 / 80) < 1e-9
    assert "D share" in report.format_report(r)


def test_control_survives_realistic_tracking_jitter():
    rng = np.random.default_rng(0)
    d = _scene([(50, 300, 0), (350, 550, 2)])
    d["ball_xy"] = d["ball_xy"] + rng.normal(0, 0.1, d["ball_xy"].shape)
    d["players_xy"] = d["players_xy"] + rng.normal(0, 0.1, d["players_xy"].shape)
    out = v2.predict_v2(d, kickoff_2nd=None)
    assert (out[100:300] == H).mean() > 0.95
    assert (out[400:550] == A).mean() > 0.95
