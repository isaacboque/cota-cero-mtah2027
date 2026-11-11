"""BAR-ATH input statistics for external/degrade.py.  *** A HUMAN RUNS THIS. Claude Code never does. ***

Reads only the provided ATD tracking INPUT (never ground truth, never video) via pipeline.data and
games.asset_paths(), computes on graded frames (the two halves):
  - the histogram of ball-missing run lengths (frames), binned by DEFAULT_BINS,
  - the share of graded frames with the ball missing,
  - the mean number of visible player slots per frame,
  - the frame-to-frame position jitter of players and ball (degrade.jitter_sigma),
  - `input_stats`: p50/p90/p99 of ball and player frame-to-frame steps, visible slots per team,
    the share of visible slots with a same-team track within DUP_RADIUS_M (-> dup_prob), and the
    rate of physically impossible track jumps > JUMP_M in one frame (-> swap_start_rate, an upper
    bound: not every identity switch crosses teams),
and writes only data/cache/degrade_params.json (gitignored with data/*). It prints nothing but
"written <path>". Nobody pastes that file or any number from it into an AI service.

    python external/barath_gap_stats.py
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import games  # noqa: E402
from external.degrade import jitter_sigma  # noqa: E402
from pipeline import data  # noqa: E402

DEFAULT_BINS = [1, 5, 25, 125, 625, 3125, 10 ** 7]
DUP_RADIUS_M = 0.5   # two same-team tracks closer than this are one player tracked twice
JUMP_M = 3.0         # > 75 m/s at 25 fps: a track switch, not motion
OUT = os.path.join(ROOT, "data", "cache", "degrade_params.json")


def compute(d, bins=DEFAULT_BINS):
    """degrade() params from an array dict; only graded rows (inside `halves`) are used."""
    seen = np.asarray(d["ball_seen"])
    vis = np.isfinite(np.asarray(d["players_xy"])[..., 0]).sum(axis=1)
    graded = np.zeros(len(seen), dtype=bool)
    lengths = []
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        graded[a:b + 1] = True
        miss = ~seen[a:b + 1]
        edges = np.diff(np.concatenate(([0], miss.astype(np.int8), [0])))
        lengths.extend((np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)).tolist())
    hist, _ = np.histogram(lengths, bins=bins)
    total = hist.sum()
    out = {
        "target_missing": float(np.mean(~seen[graded])),
        "gap_bins": [int(x) for x in bins],
        "gap_weights": [float(x) / total for x in hist] if total else [1.0 / (len(bins) - 1)] * (len(bins) - 1),
        "target_visible_slots": float(np.mean(vis[graded])),
        "player_jitter_m": jitter_sigma(np.asarray(d["players_xy"])[graded]),
    }
    if "ball_xy" in d:
        out["ball_jitter_m"] = jitter_sigma(np.asarray(d["ball_xy"])[graded])
    stats = input_stats(d, graded)
    out["input_stats"] = stats
    out["dup_prob"] = stats["dup_share"] / 2.0
    out["swap_start_rate"] = stats["track_jump_rate"]
    return out


def _pct(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"p50": None, "p90": None, "p99": None}
    return {k: float(np.percentile(x, q)) for k, q in (("p50", 50), ("p90", 90), ("p99", 99))}


def input_stats(d, graded):
    """Aggregate percentiles and rates on graded rows; no frame-level values are kept."""
    pl = np.asarray(d["players_xy"], dtype=float)
    steps_pl, steps_ball = [], []
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        seg = pl[a:b + 1]
        steps_pl.append(np.linalg.norm(np.diff(seg, axis=0), axis=-1).ravel())
        if "ball_xy" in d:
            bx = np.asarray(d["ball_xy"], dtype=float)[a:b + 1]
            steps_ball.append(np.linalg.norm(np.diff(bx, axis=0), axis=-1))
    sp = np.concatenate(steps_pl) if steps_pl else np.array([])
    stats = {"player_step_m": _pct(sp),
             "ball_step_m": _pct(np.concatenate(steps_ball)) if steps_ball else _pct([])}
    fin = sp[np.isfinite(sp)]
    stats["track_jump_rate"] = float(np.mean(fin > JUMP_M)) if fin.size else 0.0
    g = pl[graded]
    vis = np.isfinite(g[..., 0])
    team = np.asarray(d.get("slot_team", np.zeros(pl.shape[1], dtype=np.int8)))
    stats["visible_per_team"] = [float(vis[:, team == t].sum(axis=1).mean()) for t in (0, 1)]
    close = np.zeros(vis.shape, dtype=bool)
    for t in (0, 1):
        cols = np.flatnonzero(team == t)
        if len(cols) < 2:
            continue
        for c0 in range(0, len(g), 5000):  # chunks keep memory small on a full match
            x = g[c0:c0 + 5000, cols]
            dist = np.linalg.norm(x[:, :, None, :] - x[:, None, :, :], axis=-1)
            dist[:, np.arange(len(cols)), np.arange(len(cols))] = np.inf
            dist = np.where(np.isnan(dist), np.inf, dist)
            close[c0:c0 + 5000, cols] = dist.min(axis=2) < DUP_RADIUS_M
    stats["dup_share"] = float(close[vis].mean()) if vis.any() else 0.0
    return stats


def main():
    meta, raw = games.require(["atd_meta", "atd_raw"])
    d = data.load_barath(meta, raw, n_frames=games.source_frames())
    params = compute(d)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(params, fh, indent=2)
    print("written", OUT)


if __name__ == "__main__":
    main()
