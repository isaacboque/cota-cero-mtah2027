"""BAR-ATH input statistics for external/degrade.py.  *** A HUMAN RUNS THIS. Claude Code never does. ***

Reads only the provided ATD tracking INPUT (never ground truth, never video) via pipeline.data and
games.asset_paths(), computes on graded frames (the two halves):
  - the histogram of ball-missing run lengths (frames), binned by DEFAULT_BINS,
  - the share of graded frames with the ball missing,
  - the mean number of visible player slots per frame,
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
from pipeline import data  # noqa: E402

DEFAULT_BINS = [1, 5, 25, 125, 625, 3125, 10 ** 7]
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
    return {
        "target_missing": float(np.mean(~seen[graded])),
        "gap_bins": [int(x) for x in bins],
        "gap_weights": [float(x) / total for x in hist] if total else [1.0 / (len(bins) - 1)] * (len(bins) - 1),
        "target_visible_slots": float(np.mean(vis[graded])),
    }


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
