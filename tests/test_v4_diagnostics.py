"""v4 diagnostics and the "deadnan" variant, on invented scenes only (no BAR-ATH, no ground truth)."""
import numpy as np

from external import v4_diagnostics as diag
from pipeline import v4
from tests.test_v4 import AWAY0, AWAY1, HOME0, N, SLOW, run, scene

H, A, D = 0, 1, 2
HALVES = np.array([[1, 0, N - 1]])


def interception():
    return scene([(0, 40, 34), (200, 48, 34), (240, 64, 34), (280, 52, 34), (N - 1, 52 + SLOW * 319, 34)],
                 holds=[(50, 200, HOME0), (280, 450, AWAY1)], touches=[(240, AWAY0)])


def test_owner_changes_ignore_changes_across_dead_rows():
    codes = np.array([H, H, A, A, D, D, H, H])
    assert diag.owner_changes(codes, np.array([[1, 0, 7]])) == [(2, A)]


def test_found_change_is_counted_as_found():
    d = interception()
    gt = np.full(N, H, dtype=np.int8)
    gt[240:] = A
    miss, _ = diag.diagnose(d, gt)
    assert miss["total"] == 1 and miss["found"] == 1


def test_missed_change_causes():
    seen = np.ones(10, dtype=bool)
    seen[5] = False
    halves = np.array([[1, 0, 9]])
    pred = np.full(10, H, dtype=np.int8)
    gt = np.array([H] * 5 + [A] * 5, dtype=np.int8)
    # change at an unseen row, nothing predicted
    assert diag.missed_changes(gt, pred, [], [], seen, halves, fps=1.0, tol_s=1.0)["ball_unseen"] == 1
    # same change, ball seen, no contact of A
    seen[:] = True
    assert diag.missed_changes(gt, pred, [], [], seen, halves, fps=1.0, tol_s=1.0)["no_contact"] == 1
    # a lone touch of A, never confirmed
    cs = [(5, 6, A, False)]
    seqs = [{"start": 5, "end": 6, "team": A, "n": 1, "control": False, "confirmed": False}]
    assert diag.missed_changes(gt, pred, seqs, cs, seen, halves, fps=1.0, tol_s=1.0)["unconfirmed"] == 1
    # predicted dead at the change
    pred[5] = D
    assert diag.missed_changes(gt, pred, seqs, cs, seen, halves, fps=1.0, tol_s=1.0)["in_dead"] == 1


def test_false_dead_counts_every_wrong_row_once():
    d = interception()
    gt = np.full(N, H, dtype=np.int8)
    gt[240:] = A
    pred = np.asarray(run(d))
    out = diag.false_dead(gt, pred, d)
    wrong = int((np.isin(gt, (H, A)) & (pred == D)).sum())
    assert sum(out[k] for k in diag.DEAD_CAUSES) == wrong
    assert out["alive"] == N


def test_deadnan_default_is_unchanged():
    d = scene([(0, 40, 34), (N - 1, 40 + SLOW * (N - 1), 34)], holds=[(0, N, HOME0)], missing=[(300, 340)])
    assert (run(d) == run(d, params={"RESTART_NAN_STATIC": True})).all()


def test_unknown_speed_does_not_extend_a_dead_run_into_live_play():
    # ball out of play (x > 105.3) until row 150, thrown in at 151 and conducted at 1.5 m/s;
    # the tracking loses it on rows 154-156. Rows 151-153 are seen but their speed is unknown (NaN).
    way = [(0, 106.5, 34), (150, 106.5, 34), (151, 104, 34), (N - 1, 104 - SLOW * (N - 152), 34)]
    d = scene(way, holds=[(151, N, HOME0)], missing=[(154, 157)])
    c = v4._cfg(None)
    static = v4.dead_mask(d, [], c, None)
    unknown = v4.dead_mask(d, [], dict(c, RESTART_NAN_STATIC=False), None)
    assert static[:151].all() and unknown[:151].all()
    assert static[151:154].all()          # current rule: unknown speed counts as static
    assert not unknown[151:].any()        # variant: the run ends when the ball is put in play
