"""v4 on synthetic plays, one test per rule of the team document "Reglas de posesion" v0.2.

Every scene is invented: a ball path through waypoints, players parked far away (moving at ~3 m/s
so the "everybody stopped" rule never fires), and players brought to the ball where the play needs them.
Nothing here reads BAR-ATH data or ground truth.
"""
import numpy as np

from pipeline import make_submission, v4

H, A, D = 0, 1, 2
N = 600
HOME0, HOME1, AWAY0, AWAY1 = 0, 1, 2, 3
SLOW = 0.06  # m per frame = 1.5 m/s, a ball conducted by a player


def scene(waypoints, n=N, holds=(), touches=(), stands=(), missing=(), halves=None):
    """waypoints [(frame, x, y)]: ball path, linear in between, metres.
    holds [(a, b, slot)]: slot conducts the ball (1 m away, same velocity) on rows a..b-1.
    touches [(frame, slot)]: slot stands where the ball is at `frame`, for 13 rows around it.
    stands [(a, b, slot, x, y)]: slot stands still at (x, y) on rows a..b-1.
    missing [(a, b)]: the tracking loses the ball on rows a..b-1 (players are still tracked)."""
    t = np.arange(n, dtype=float)
    wf = [w[0] for w in waypoints]
    ball = np.stack([np.interp(t, wf, [w[1] for w in waypoints]),
                     np.interp(t, wf, [w[2] for w in waypoints])], axis=1)
    pl = np.zeros((n, 4, 2))
    pl[:, :, 0] = [5.0, 10.0, 95.0, 100.0]
    pl[:, :, 1] = 10.0 + 1.5 * np.sin(np.pi * t[:, None] / 25)  # ~3 m/s, never "everybody stopped"
    for a, b, slot in holds:
        pl[a:b, slot] = ball[a:b] + [1.0, 0.0]
    for f, slot in touches:
        pl[f - 6:f + 7, slot] = ball[f] + [0.5, 0.0]
    for a, b, slot, x, y in stands:
        pl[a:b, slot] = [x, y]
    seen = np.ones(n, dtype=bool)
    for a, b in missing:
        seen[a:b] = False
        ball[a:b] = np.nan
    return {"ball_xy": ball, "ball_seen": seen, "players_xy": pl,
            "slot_team": np.array([0, 0, 1, 1], dtype=np.int8),
            "halves": np.array([[1, 0, n - 1]] if halves is None else halves)}


def changes(out):
    return [(int(i) + 1, int(out[i + 1])) for i in np.flatnonzero(out[1:] != out[:-1])]


def run(d, **kw):
    kw.setdefault("kickoff_2nd", None)
    return v4.predict_v4(d, **kw)


# §5: a rival touch that goes back to the team in possession changes nothing.
def test_rebound_back_to_the_same_team_keeps_possession():
    d = scene([(0, 40, 34), (200, 48, 34), (240, 64, 34), (280, 52, 34), (N - 1, 52 + SLOW * 319, 34)],
              holds=[(50, 200, HOME0), (280, 450, HOME1)], touches=[(240, AWAY0)])
    out = run(d)
    assert (out[60:450] == H).all()


# §4 + §8: interception confirmed by a teammate's control, written from the first touch.
def test_interception_is_backdated_to_the_first_touch():
    d = scene([(0, 40, 34), (200, 48, 34), (240, 64, 34), (280, 52, 34), (N - 1, 52 + SLOW * 319, 34)],
              holds=[(50, 200, HOME0), (280, 450, AWAY1)], touches=[(240, AWAY0)])
    out = run(d)
    assert (out[60:230] == H).all() and (out[245:450] == A).all()
    switch = [f for f, t in changes(out) if t == A]
    assert switch and 233 <= switch[0] <= 243  # at the touch (~240), not when AWAY1 controls (281)


# §10.3: in a long 50-50 the last team keeps the ball until someone comes out with it.
def test_long_dispute_keeps_last_team_until_someone_comes_out():
    way = [(0, 40, 34), (200, 52, 34), (215, 55, 30), (230, 58, 34), (245, 61, 30), (260, 64, 34),
           (275, 67, 30), (300, 70, 34), (450, 70 + SLOW * 150, 34), (N - 1, 79 + SLOW * 149, 34)]
    d = scene(way, holds=[(50, 200, HOME0), (300, 450, AWAY0)],
              touches=[(215, AWAY0), (230, HOME1), (245, AWAY1), (260, HOME0), (275, AWAY0)])
    out = run(d)
    assert (out[60:268] == H).all()      # alternating touches never confirm
    assert (out[300:450] == A).all()     # AWAY0 comes out with it, backdated to its touch at ~275
    assert min(f for f, t in changes(out) if t == A) >= 268


# §2: ball not visible = possession unchanged, never D.
def test_missing_ball_carries_possession():
    d = scene([(0, 40, 34), (N - 1, 40 + SLOW * 599, 34)], holds=[(50, 500, HOME0)],
              missing=[(150, 200)])
    out = run(d)
    assert (out[60:500] == H).all()


# §8 / §10.4: a change hidden in a gap goes at reappearance or mid-gap, as configured.
def test_change_hidden_in_gap_placement():
    fast = 0.08  # 2 m/s, so the reappearing ball is clearly not static
    d = scene([(0, 40, 34), (N - 1, 40 + fast * 599, 34)],
              holds=[(50, 150, HOME0), (150, 400, AWAY0)], missing=[(150, 250)])
    at_reappear = [f for f, t in changes(run(d)) if t == A][0]
    assert 248 <= at_reappear <= 256
    mid = [f for f, t in changes(run(d, params={"GAP_PLACEMENT": "midpoint"})) if t == A][0]
    assert abs(mid - 200) <= 3


# §5: a ball flying over a player at constant velocity is not a touch (no height in tracking).
def test_ball_passing_over_a_rival_is_not_a_touch():
    way = [(0, 20, 34), (150, 29, 34), (200, 59, 34), (250, 89, 34), (450, 89 + SLOW * 200, 34),
           (N - 1, 101 + SLOW * 149 * 0, 34)]
    d = scene(way, holds=[(50, 150, HOME0), (250, 450, AWAY1)],
              stands=[(190, 211, AWAY0, 59.0, 34.3)])
    out = run(d)
    assert (out[60:245] == H).all()      # AWAY0 under the flight path does not take it
    assert (out[260:450] == A).all()     # AWAY1 receiving it does


# §6 + §7: throw-in. Out of play is D; Smart Tagging says N/A, so the taker in the tracking restarts.
def test_throw_in_dead_then_taker_team_restarts():
    way = [(0, 40, 34), (200, 52, 34), (230, 58, -1.5), (280, 58, -1.5), (300, 62, 10),
           (450, 62 + SLOW * 150, 10), (N - 1, 71 + SLOW * 149, 10)]
    d = scene(way, holds=[(50, 200, HOME0), (300, 450, AWAY1)],
              stands=[(255, 283, AWAY0, 58.0, -2.5)])
    out = run(d, restarts=[(270, None, "throw_in")])
    assert (out[60:195] == H).all()
    assert (out[235:275] == D).all()
    assert (out[290:450] == A).all()


# §6 + §7: goal kick. D lasts while the ball is lost and then placed static, until it is kicked.
def test_goal_kick_dead_until_the_ball_is_kicked():
    way = [(0, 40, 34), (200, 52, 34), (230, 108, 34), (235, 108, 34), (262, 100, 34),
           (300, 100, 34), (330, 80, 34), (450, 80 - SLOW * 120, 34), (N - 1, 72.8, 34)]
    d = scene(way, holds=[(50, 200, HOME0), (330, 450, AWAY1)], missing=[(235, 262)],
              stands=[(285, 303, AWAY0, 101.0, 34.0)])
    out = run(d)
    assert (out[240:290] == D).all()
    assert (out[310:450] == A).all()


# §6: free kick = ball placed static + a Smart Tagging set piece; the tag's team restarts.
def test_free_kick_static_ball_with_cue_is_dead_and_cue_team_restarts():
    way = [(0, 40, 34), (200, 52, 34), (300, 52, 34), (320, 62, 34), (450, 62 + SLOW * 130, 34),
           (N - 1, 69.8 + SLOW * 149, 34)]
    d = scene(way, holds=[(50, 200, HOME0), (320, 450, HOME1)],
              stands=[(200, 303, AWAY0, 52.8, 34.0)])
    out = run(d, restarts=[(240, 0, "free_kick")])
    assert (out[210:290] == D).all()
    assert (out[305:450] == H).all()     # tag names home; AWAY0 standing by the ball does not win


# §6 "NO es D": a goalkeeper holding the ball still is in play, possession of his team.
def test_goalkeeper_holding_the_ball_is_not_dead():
    way = [(0, 40, 34), (200, 52, 34), (300, 52, 34), (N - 1, 52 + SLOW * 299, 34)]
    d = scene(way, holds=[(50, 300, HOME0), (300, 500, HOME0)])
    out = run(d)
    assert (out[60:500] == H).all()


# §6 + §7: goal -> D until the kick-off, even when the ball is moved back to the centre in between.
def test_goal_dead_until_kick_off():
    way = [(0, 40, 34), (200, 52, 34), (230, 108, 34), (235, 108, 34), (300, 64, 34),
           (357, 52.65, 34), (420, 52.65, 34), (440, 45, 34), (N - 1, 45 - SLOW * 159, 34)]
    d = scene(way, holds=[(50, 200, HOME0), (440, 560, AWAY1)], missing=[(235, 300)],
              stands=[(400, 423, AWAY0, 53.5, 34.0)])
    cues = [(210, None, "goal"), (400, None, "kick_off")]
    out = run(d, restarts=cues)
    assert (out[240:410] == D).all()
    assert (out[430:560] == A).all()
    without_goal_cue = run(d, restarts=[(400, None, "kick_off")])
    assert (without_goal_cue[240:350] != D).any()   # the goal rule is what keeps 235-360 dead


# §1, §6: D outside the halves and before the 2nd-half kick-off; never X; reproducible file.
def test_hard_dead_no_x_and_deterministic(tmp_path):
    halves = [[1, 100, 299], [2, 400, 599]]
    d = scene([(0, 40, 34), (N - 1, 40 + SLOW * 599, 34)], holds=[(100, 600, HOME0)],
              halves=halves)
    a = v4.predict_v4(d, kickoff_2nd=450)
    b = v4.predict_v4(d, kickoff_2nd=450)
    assert (a[:100] == D).all() and (a[300:400] == D).all() and (a[400:450] == D).all()
    assert (a[110:299] == H).all() and (a[470:600] == H).all()
    assert set(np.unique(a)) <= {H, A, D}
    labels = np.array(["H", "A", "D"])
    p1 = make_submission.write_csv(str(tmp_path / "a.csv"), labels[a])
    p2 = make_submission.write_csv(str(tmp_path / "b.csv"), labels[b])
    assert make_submission.sha256(p1) == make_submission.sha256(p2)


def test_sequences_confirm_on_control_or_two_contacts():
    cs = [(10, 11, 1, False), (40, 41, 0, False), (60, 61, 0, False), (200, 230, 1, True)]
    seqs = v4.sequences(cs, gap_frames=50)
    assert [(q["team"], q["n"], q["confirmed"]) for q in seqs] == \
        [(1, 1, False), (0, 2, True), (1, 1, True)]


# Ticket "Detector de balón muerto" (#23): after a throw-in the ball is carried back at walking
# pace; play restarts only when it is thrown/kicked (RESTART_KICK_MS), not when it starts moving.
def _carried_back_throw_in():
    n = 800
    way = [(0, 40, 34), (200, 52, 34), (230, 58, -1.5), (260, 58, -1.5), (300, 58, 0.5),
           (460, 66, 0.5), (490, 66, 12.5), (n - 1, 66 + SLOW * 309, 12.5)]
    return scene(way, n=n, holds=[(50, 200, HOME0), (300, 460, AWAY0), (495, 700, AWAY1)])


def test_default_restart_ends_dead_when_ball_moves():
    out = run(_carried_back_throw_in())
    assert (out[240:280] == D).all()
    assert not (out[320:455] == D).all()  # current behaviour: walking the ball back = in play


def test_restart_kick_keeps_dead_until_the_ball_is_struck():
    out = run(_carried_back_throw_in(), params={"RESTART_KICK_MS": 6.0, "RESTART_MAX_EXT_S": 30.0})
    assert (out[240:455] == D).all()
    assert (out[500:700] == A).all()
