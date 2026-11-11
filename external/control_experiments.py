"""IDSSE experiments for the "Plan rediseño de control" map (issue #17). External data only.

    python external/control_experiments.py base|noise|touch [--cache-dir data/external/idsse]

Degradation always uses explicit parameters (degrade.DEFAULT_PARAMS plus the overrides below),
never data/cache/degrade_params.json: that file holds BAR-ATH statistics and must not feed a run
whose output an AI reads. Every prediction is scored against the raw IDSSE labels and against the
filtered ones (idsse.filter_owner_flicks), per ticket "Criterios de éxito del control".

Writes external/results/ctrl_<exp>.csv (one row per match x setting x labels, gitignored) and
prints means over matches, then mean/min/max over seeds.
"""
import argparse
import csv
import itertools
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from external import degrade, idsse  # noqa: E402
from pipeline import cv, v2, v4  # noqa: E402

V4_BEST_SO_FAR = {"DV_TOUCH_MS": 6.0, "SEQ_GAP_S": 3.0, "GAP_PLACEMENT": "midpoint"}
DEAD_BINS_S = (0, 2, 10, 30, 1e9)  # dead-spell length bins (s) for the dead-ball breakdown


def predictors(exp):
    p = {"v1": lambda d: cv.baseline_v1(d),
         "v2": lambda d: v2.predict_v2(d, kickoff_2nd=None),
         "v4best": lambda d: v4.predict_v4(d, kickoff_2nd=None, params=V4_BEST_SO_FAR)}
    if exp == "base":
        p["v4default"] = lambda d: v4.predict_v4(d, kickoff_2nd=None)
    if exp == "touch":
        p = {}
        for dv, gap in itertools.product((6.0, 8.0, 10.0, 12.0), ("reappear", "midpoint")):
            prm = {"DV_TOUCH_MS": dv, "SEQ_GAP_S": 3.0, "GAP_PLACEMENT": gap}
            p["v4_dv{}_{}".format(int(dv), gap)] = (
                lambda d, prm=prm: v4.predict_v4(d, kickoff_2nd=None, params=prm))
    return p


def conditions(exp):
    """(mode, overrides, seed) tuples; mode 'raw' means no degradation."""
    if exp == "noise":
        return [("degraded", {"noise_sigma_m": s, "dup_prob": dp}, 0)
                for s in (0.0, 0.1, 0.3) for dp in (0.0, 0.02)]
    return [("raw", {}, 0)] + [("degraded", {}, s) for s in (0, 1, 2)]


def _spells(mask):
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def dead_breakdown(gt, pred, fps):
    """Share of graded rows predicted D and, per length bin, share of reference dead spells
    with at least half their rows predicted D."""
    graded = gt >= 0
    out = {"d_share_gt": float(np.mean(gt[graded] == 2)),
           "d_share_pred": float(np.mean(pred[graded] == 2))}
    spells = _spells(gt == 2)
    for lo, hi in zip(DEAD_BINS_S[:-1], DEAD_BINS_S[1:]):
        sel = [(a, b) for a, b in spells if lo * fps <= b - a < hi * fps]
        hit = [np.mean(pred[a:b] == 2) >= 0.5 for a, b in sel]
        out["dead_recall_{}s".format(int(lo))] = float(np.mean(hit)) if hit else float("nan")
        out["n_dead_{}s".format(int(lo))] = len(sel)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=("base", "noise", "touch"))
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "data", "external", "idsse"))
    args = ap.parse_args()
    preds, conds = predictors(args.exp), conditions(args.exp)
    rows = []
    for mid in idsse.MATCH_IDS:
        clean = idsse.load_idsse(mid, args.cache_dir)
        labels = {"raw": clean["gt_codes"],
                  "filtered": idsse.filter_owner_flicks(clean["gt_codes"], clean["halves"])}
        fps = float(clean["fps"])
        for mode, over, seed in conds:
            d = clean if mode == "raw" else degrade.degrade(clean, over, seed=seed)
            for name, fn in preds.items():
                pred = np.asarray(fn(d)).astype(np.int8)
                for lab, gt in labels.items():
                    spell, macro, n_gt, n_pred, _ = cv._score_detail(gt, pred, d["halves"])
                    r = {"exp": args.exp, "predictor": name, "mode": mode,
                         "noise": over.get("noise_sigma_m", degrade.DEFAULT_PARAMS["noise_sigma_m"]),
                         "dup": over.get("dup_prob", degrade.DEFAULT_PARAMS["dup_prob"]),
                         "seed": seed, "labels": lab, "match": mid, "spell_f1": spell,
                         "macro_f1": macro, "n_gt_spells": n_gt, "n_pred_spells": n_pred}
                    r.update(dead_breakdown(np.asarray(gt), pred, fps))
                    rows.append(r)
        print(mid, "done", flush=True)
    out_dir = os.path.join(ROOT, "external", "results")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "ctrl_{}.csv".format(args.exp))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    summarize(path)


def summarize(path):
    import pandas as pd
    df = pd.read_csv(path)
    keys = ["predictor", "mode", "noise", "dup", "labels"]
    per_seed = df.groupby(keys + ["seed"]).agg(
        spell_f1=("spell_f1", "mean"), n_gt=("n_gt_spells", "mean"), n_pred=("n_pred_spells", "mean"),
        d_gt=("d_share_gt", "mean"), d_pred=("d_share_pred", "mean")).reset_index()
    agg = per_seed.groupby(keys).agg(
        spell=("spell_f1", "mean"), spell_min=("spell_f1", "min"), spell_max=("spell_f1", "max"),
        n_gt=("n_gt", "mean"), n_pred=("n_pred", "mean"), d_gt=("d_gt", "mean"),
        d_pred=("d_pred", "mean")).reset_index()
    with pd.option_context("display.width", 200, "display.max_rows", 500):
        print(agg.round(4).to_string(index=False))
        rec = [c for c in df.columns if c.startswith("dead_recall_")]
        print(df.groupby(["predictor", "mode", "labels"])[rec].mean().round(3).to_string())


if __name__ == "__main__":
    main()
