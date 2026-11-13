"""Why does v4 miss possession changes and predict too much dead ball? (ticket #17, "Not yet specified")

IDSSE only (external, CC BY 4.0). Never run on BAR-ATH data or its ground truth: the labels used
here are IDSSE's own. Two breakdowns, per match and condition (raw / degraded seeds):

1. Missed changes. Every owner change of the reference (filtered labels, alive rows) is matched to a
   predicted change to the same team within TOL_S. A miss gets the FIRST cause that applies:
   - in_dead: v4 predicts D at the change frame
   - ball_unseen: the ball is missing at the change frame
   - no_contact: no contact of the new team in [f - TOL_S, f + TOL_S]
   - unconfirmed: contacts of the new team there, but no confirmed sequence
   - confirmed_off: a confirmed sequence of the new team there, yet no predicted change in tolerance
     (state already that team, or overwritten later / by MIN_RUN smoothing)
2. False dead. Reference alive rows (H/A) that v4 labels D, split by cause (first that applies):
   hard (outside halves), oob, slow, missing_static, static_run (each a dead-score component that is
   on at that row), combined (dead only because weak components add up), extension (only dead
   because a dead run was extended), no_team (live stretch where no team could be given).

    python external/v4_diagnostics.py [--seeds 0 1 2] [--cache-dir data/external/idsse]

Writes external/results/v4_diag.csv (gitignored) and prints the aggregated shares.
"""
import argparse
import csv
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import config, v4  # noqa: E402
from pipeline.deadball import _runs, hysteresis, min_run  # noqa: E402
from pipeline.features import compute_features  # noqa: E402

TOL_S = 2.0  # a predicted change within 2 s of the reference change counts as found
MISS_CAUSES = ("in_dead", "ball_unseen", "no_contact", "unconfirmed", "confirmed_off")
DEAD_CAUSES = ("hard", "oob", "slow", "missing_static", "static_run", "combined", "extension", "no_team")


def owner_changes(codes, halves):
    """[(frame, new_team)] where an alive row's owner differs from the previous alive row's, inside
    one alive stretch of one half (a change across a D run is a restart, not counted)."""
    codes = np.asarray(codes)
    out = []
    for _, a, b in np.asarray(halves).reshape(-1, 3):
        a, b = int(a), int(b) + 1
        for i in range(a + 1, b):
            if codes[i] in (0, 1) and codes[i - 1] in (0, 1) and codes[i] != codes[i - 1]:
                out.append((i, int(codes[i])))
    return out


def missed_changes(gt, pred, seqs, contacts, seen, halves, fps, tol_s=TOL_S):
    """Counts per cause, plus 'found' and 'total'."""
    tol = int(round(tol_s * fps))
    pred_ch = owner_changes(pred, halves)
    by_team = {0: np.array([f for f, t in pred_ch if t == 0]), 1: np.array([f for f, t in pred_ch if t == 1])}
    out = {k: 0 for k in MISS_CAUSES + ("found", "total")}
    for f, t in owner_changes(gt, halves):
        out["total"] += 1
        p = by_team[t]
        if len(p) and np.min(np.abs(p - f)) <= tol:
            out["found"] += 1
            continue
        lo, hi = f - tol, f + tol
        if pred[f] == 2:
            out["in_dead"] += 1
        elif not seen[f]:
            out["ball_unseen"] += 1
        elif not any(c[2] == t and c[0] <= hi and c[1] >= lo for c in contacts):
            out["no_contact"] += 1
        elif not any(q["team"] == t and q["confirmed"] and q["start"] <= hi and q["end"] >= lo for q in seqs):
            out["unconfirmed"] += 1
        else:
            out["confirmed_off"] += 1
    return out


def dead_components(d, c):
    """Boolean masks, one per dead-score component, as v4.dead_mask builds them (no Smart Tagging)."""
    n = len(d["ball_seen"])
    fps = c["FPS"]
    seen = np.asarray(d["ball_seen"], dtype=bool)
    f = compute_features(d)
    oob = hysteresis(f["oob"], config.OOB_ENTER_FRAMES, config.OOB_EXIT_FRAMES)
    with np.errstate(invalid="ignore"):
        slow = (f["med_speed_home"] < config.SLOW_TEAM_SPEED_MS) & (f["med_speed_away"] < config.SLOW_TEAM_SPEED_MS)
        static_or_missing = ~seen | (f["ball_speed"] < config.BALL_STATIC_MS)
    slow = min_run(slow & static_or_missing, int(config.SLOW_MIN_S * fps))
    ms = np.zeros(n, dtype=bool)
    w = config.STATIC_WINDOW_FRAMES
    ball = np.asarray(d["ball_xy"], dtype=float)
    for a, b in _runs(~seen):
        if b - a < int(config.MISSING_RUN_MIN_S * fps) or b + w >= n:
            continue
        if seen[b] and seen[b + w] and np.linalg.norm(ball[b + w] - ball[b]) * fps / w < config.BALL_STATIC_MS:
            ms[a:b] = True
    _, speed = v4.ball_kinematics(d["ball_xy"], c["VEL_LAG_FRAMES"], fps)
    with np.errstate(invalid="ignore"):
        static = seen & (speed < c["BALL_STATIC_MS"])
    static_run = min_run(static, v4._frames(c["STATIC_MIN_S"], fps))
    return {"oob": oob, "slow": slow, "missing_static": ms, "static_run": static_run}


def false_dead(gt, pred, d, params=None):
    """Counts of reference-alive rows predicted D, per cause; plus 'alive' (reference alive rows)."""
    c = v4._cfg(params)
    dd = v4.prepare_ball(d, c)
    n = len(gt)
    hard = v4.hard_dead(n, d["halves"], None)
    base = v4.dead_mask(dd, [], dict(c, RESTART_MAX_EXT_S=0.0), None)
    full = v4.dead_mask(dd, [], c, None)
    comp = dead_components(dd, c)
    alive = np.isin(gt, (0, 1))
    wrong = alive & (np.asarray(pred) == 2)
    out = {"alive": int(alive.sum())}
    left = wrong.copy()
    for name, mask in [("hard", hard)] + [(k, comp[k] & base) for k in ("oob", "slow", "missing_static", "static_run")] \
            + [("extension", full & ~base), ("no_team", ~full)]:
        hit = left & mask
        out[name] = int(hit.sum())
        left &= ~hit
    out["combined"] = int(left.sum())  # dead in `base` with no single component on
    return out


def diagnose(d, gt, params=None):
    """Both breakdowns for one prediction of v4 on `d` against reference codes `gt`."""
    c = v4._cfg(params)
    pred = np.asarray(v4.predict_v4(d, kickoff_2nd=None, params=params)).astype(np.int8)
    dd = v4.prepare_ball(d, c)
    dead = v4.dead_mask(dd, [], c, None)
    cs = v4.contacts(dd, dead, c)
    seqs = v4.sequences(cs, v4._frames(c["SEQ_GAP_S"], c["FPS"]))
    seen = np.asarray(dd["ball_seen"], dtype=bool)
    miss = missed_changes(np.asarray(gt), pred, seqs, cs, seen, d["halves"], c["FPS"])
    return miss, false_dead(np.asarray(gt), pred, d, params)


def main():
    from external import degrade, idsse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "data", "external", "idsse"))
    args = ap.parse_args()
    rows = []
    for mid in idsse.MATCH_IDS:
        clean = idsse.load_idsse(mid, args.cache_dir)
        gt = idsse.filter_owner_flicks(clean["gt_codes"], clean["halves"])
        for mode, seed in [("raw", 0)] + [("degraded", s) for s in args.seeds]:
            d = clean if mode == "raw" else degrade.degrade(clean, {}, seed=seed)
            miss, dead = diagnose(d, gt)
            rows.append(dict(match=mid, mode=mode, seed=seed, **{"miss_" + k: v for k, v in miss.items()},
                             **{"falseD_" + k: v for k, v in dead.items()}))
        print(mid, "done", flush=True)
    out_dir = os.path.join(ROOT, "external", "results")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "v4_diag.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for mode in ("raw", "degraded"):
        sel = [r for r in rows if r["mode"] == mode]
        tot = sum(r["miss_total"] for r in sel) or 1
        alive = sum(r["falseD_alive"] for r in sel) or 1
        print("\n[{}] reference changes: {} | found {:.1%}".format(mode, tot, sum(r["miss_found"] for r in sel) / tot))
        print("  missed, share of all changes: " + ", ".join(
            "{} {:.1%}".format(k, sum(r["miss_" + k] for r in sel) / tot) for k in MISS_CAUSES))
        print("  alive rows predicted D, share of alive rows: " + ", ".join(
            "{} {:.1%}".format(k, sum(r["falseD_" + k] for r in sel) / alive) for k in DEAD_CAUSES))
    print("\nwritten", path)


if __name__ == "__main__":
    main()
