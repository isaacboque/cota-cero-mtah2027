import numpy as np

from pipeline import cv

H, A, D = 0, 1, 2


def _gt():
    # 2 halves of 40 rows: H 20, A 20 | A 20, D 20
    gt = np.array([H] * 20 + [A] * 20 + [A] * 20 + [D] * 20, dtype=np.int8)
    halves = np.array([[1, 0, 39], [2, 40, 79]])
    return gt, halves


def test_perfect_prediction_scores_one():
    gt, halves = _gt()
    spell, macro = cv.score(gt, gt.copy(), halves)
    assert spell == 1.0 and macro == 1.0


def test_constant_guess_scores_zero_spell():
    gt, halves = _gt()
    spell, macro = cv.score(gt, np.full(len(gt), D, dtype=np.int8), halves)
    assert spell == 0.0
    assert macro < 0.5


def test_possession_does_not_span_halves():
    # A at the end of half 1 and the start of half 2 are two possessions, not one.
    gt, halves = _gt()
    merged = np.array([H] * 20 + [A] * 60, dtype=np.int8)  # one long A across the break
    spell, _ = cv.score(gt, merged, halves)
    assert spell < 1.0


def test_unknown_gt_not_graded():
    gt, halves = _gt()
    gt2 = gt.copy()
    gt2[:5] = -1
    pred = gt.copy()
    pred[:5] = D
    _, macro = cv.score(gt2, pred, halves)
    assert macro == 1.0


def _synthetic_dict(n=12):
    ball = np.zeros((n, 2))
    ball[:, 0] = np.arange(n)
    players = np.full((n, 4, 2), 50.0)
    for i in range(n):
        slot = 0 if i < 6 else 2  # home slot 0 near ball first half, then away slot 2
        players[i, slot] = ball[i] + 0.5
    return {"ball_xy": ball, "ball_seen": np.ones(n, bool),
            "players_xy": players, "slot_team": np.array([0, 0, 1, 1], dtype=np.int8),
            "halves": np.array([[1, 0, n - 1]])}


def test_baseline_v1_two_team_sequence():
    d = _synthetic_dict()
    out = cv.baseline_v1(d, window=1)
    assert out.tolist() == [H] * 6 + [A] * 6


def test_baseline_v1_unseen_ball_is_dead():
    d = _synthetic_dict()
    d["ball_seen"][:] = False
    d["ball_xy"][:] = np.nan
    assert (cv.baseline_v1(d, window=1) == D).all()


def test_leave_one_match_out_writes_table(tmp_path):
    gt, halves = _gt()
    seen = []

    def loader(mid, cache_dir):
        return {"gt_codes": gt, "halves": halves}

    def predict(d, train):
        seen.append(tuple(train))
        return d["gt_codes"].copy()

    rows = cv.leave_one_match_out(["m1", "m2", "m3"], predict, "unused", name="t",
                                  out_dir=str(tmp_path), loader=loader)
    assert seen == [("m2", "m3"), ("m1", "m3"), ("m1", "m2")]
    assert [r["match"] for r in rows] == ["m1", "m2", "m3", "MEAN"]
    assert rows[-1]["spell_f1"] == 1.0
    text = (tmp_path / "cv_t.csv").read_text()
    assert text.splitlines()[0].startswith("match,spell_f1")
    assert "MEAN" in text
