"""Validation harness: score label arrays against IDSSE gt_codes, leave-one-match-out.

Label codes everywhere: 0 = H, 1 = A, 2 = D, 3 = X (abstain / not graded). IDSSE's `gt_codes`
use -1 for "ball state unknown"; `score` maps it to X so it is never graded.

The scorer is imported from evaluation/possession_metrics.py (never copied). This module never
reads evaluation/gt/ or any BAR-ATH file; it works on arrays built from IDSSE or synthetic data.
"""
import csv
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "evaluation"))
import possession_metrics as pm  # noqa: E402

H, A, D, X = pm.H, pm.A, pm.D, pm.X
# Default smoothing half-width of the organisers' baseline_smooth50 (starter/baseline.py VARIANTS).
BASELINE_WINDOW = 50
COLUMNS = ("match", "spell_f1", "macro_f1", "n_gt_spells", "n_pred_spells", "n_graded")


def _runs(halves, n):
    """Half-open [start, stop) row spans from `halves` rows (period, first_row, last_row)."""
    return [(int(a), int(b) + 1) for _, a, b in np.asarray(halves).reshape(-1, 3) if a <= b < n]


def score(gt_codes, pred_codes, halves):
    """(spellF1, macroF1) of `pred_codes` against `gt_codes`, temporal metrics per half.

    Possessions never span two halves even when the rows are contiguous (IDSSE has no gap rows).
    Rows outside the halves and gt == -1 are not graded.
    """
    gt = np.asarray(gt_codes).astype(np.int8).copy()
    pred = np.asarray(pred_codes).astype(np.int8)
    if len(gt) != len(pred):
        raise ValueError("length mismatch: gt {} vs pred {}".format(len(gt), len(pred)))
    runs = _runs(halves, len(gt))
    inside = np.zeros(len(gt), dtype=bool)
    for a, b in runs:
        inside[a:b] = True
    gt[(gt < 0) | ~inside] = X
    cm3 = pm.scored_confusion(pm.confusion(gt, pred))
    filled = pm.fill_abstentions(pred, runs)
    spell = pm.spell_scores(gt, filled, runs)
    return spell["mean_f1"], pm.macro_f1(cm3)


def _score_detail(gt_codes, pred_codes, halves):
    spell, macro = score(gt_codes, pred_codes, halves)
    runs = _runs(halves, len(gt_codes))
    gt = np.asarray(gt_codes).astype(np.int8).copy()
    gt[gt < 0] = X
    pred = pm.fill_abstentions(np.asarray(pred_codes).astype(np.int8), runs)
    return spell, macro, len(pm.possession_spells(gt, runs)), \
        len(pm.possession_spells(pred, runs)), int(np.sum(gt != X))


def baseline_v1(d, window=BASELINE_WINDOW):
    """starter/baseline.py logic on the array dict: team of the player nearest the ball, then a
    centred majority vote over +/- `window` frames; D where no estimate falls in the window.
    Ties go to home. Returns int8 codes (0 H, 1 A, 2 D). Not applied across half boundaries."""
    n = len(d["ball_seen"])
    near = np.full(n, -1, dtype=np.int8)
    diff = d["players_xy"] - d["ball_xy"][:, None, :]
    dist = diff[..., 0] ** 2 + diff[..., 1] ** 2
    dist = np.where(np.isnan(dist), np.inf, dist)
    best = np.argmin(dist, axis=1)
    ok = d["ball_seen"] & np.isfinite(dist[np.arange(n), best])
    near[ok] = np.asarray(d["slot_team"])[best[ok]]
    out = np.full(n, D, dtype=np.int8)
    for a, b in _runs(d["halves"], n) or [(0, n)]:
        seg = near[a:b]
        hc = np.concatenate(([0], np.cumsum(seg == 0)))
        ac = np.concatenate(([0], np.cumsum(seg == 1)))
        idx = np.arange(len(seg))
        lo = np.maximum(0, idx - window)
        hi = np.minimum(len(seg), idx + window + 1)
        home, away = hc[hi] - hc[lo], ac[hi] - ac[lo]
        seen = (home + away) > 0
        lab = np.full(len(seg), D, dtype=np.int8)
        lab[seen] = np.where(home[seen] >= away[seen], H, A)
        out[a:b] = lab
    return out


def leave_one_match_out(match_ids, predict_fn, cache_dir, name="run",
                        out_dir=None, loader=None):
    """Score `predict_fn(d, train_ids) -> codes` on every match in turn.

    `train_ids` are the other matches (what a tunable model may fit on); parameter-free
    predictors ignore it. Writes `<out_dir>/cv_<name>.csv` (default external/results/, gitignored)
    with one row per match plus a MEAN row, and returns the list of row dicts.
    """
    if loader is None:
        from external.idsse import load_idsse as loader
    if out_dir is None:
        out_dir = os.path.join(_ROOT, "external", "results")
    rows = []
    for mid in match_ids:
        d = loader(mid, cache_dir)
        pred = predict_fn(d, [m for m in match_ids if m != mid])
        spell, macro, n_gt, n_pred, n_graded = _score_detail(d["gt_codes"], pred, d["halves"])
        rows.append({"match": mid, "spell_f1": spell, "macro_f1": macro,
                     "n_gt_spells": n_gt, "n_pred_spells": n_pred, "n_graded": n_graded})
    if rows:
        rows.append({"match": "MEAN",
                     "spell_f1": float(np.mean([r["spell_f1"] for r in rows])),
                     "macro_f1": float(np.mean([r["macro_f1"] for r in rows])),
                     "n_gt_spells": "", "n_pred_spells": "", "n_graded": ""})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "cv_{}.csv".format(name)), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows
