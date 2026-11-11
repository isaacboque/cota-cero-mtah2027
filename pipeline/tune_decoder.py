"""Grid search of the v3 decoder and the v4 rules on IDSSE only (leave-one-match-out, optionally degraded).

    python pipeline/tune_decoder.py [--cache-dir data/external/idsse] [--raw]

Needs the IDSSE files (external data, CC BY 4.0) and kloppy. Never touches BAR-ATH. Writes one CSV
per setting plus a summary to external/results/ (gitignored). Pick the setting from the flat region
of the curve, not the maximum, then copy it into pipeline/config.py with this run's id as source.
"""
import argparse
import itertools
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from external import degrade, idsse  # noqa: E402
from pipeline import cv, decode, v2, v4  # noqa: E402

GRID = {
    "MIN_DWELL_HA_S": (0.5, 1.0, 2.0),
    "LOG_SWITCH_FAR": (-4.0, -8.0, -12.0),
    "LOG_TO_D": (-2.0, -3.0, -5.0),
}
# v4: kept small on purpose (7 matches; a large grid finds a winner by chance). Smart Tagging
# constants are not here: IDSSE has no Smart Tagging (NO-IDSSE in pipeline/config.py).
V4_GRID = {
    "DV_TOUCH_MS": (3.0, 4.0, 6.0),
    "SEQ_GAP_S": (2.0, 3.0),
    "GAP_PLACEMENT": ("reappear", "midpoint"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "data", "external", "idsse"))
    ap.add_argument("--raw", action="store_true", help="do not degrade the tracking")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    def loader(mid, cache_dir):
        d = idsse.load_idsse(mid, cache_dir)
        return d if args.raw else degrade.degrade(d, seed=args.seed)

    tag = "raw" if args.raw else "degraded"
    ids = list(idsse.MATCH_IDS)

    def run(name, fn):
        rows = cv.leave_one_match_out(ids, fn, args.cache_dir, name="{}_{}".format(name, tag),
                                      loader=loader)
        return rows[-1]["spell_f1"], rows[-1]["macro_f1"]

    summary = [("v1", ) + run("v1", lambda d, tr: cv.baseline_v1(d)),
               ("v2", ) + run("v2", lambda d, tr: v2.predict_v2(d, kickoff_2nd=None))]
    keys = sorted(GRID)
    for combo in itertools.product(*(GRID[k] for k in keys)):
        params = dict(zip(keys, combo))
        name = "v3_" + "_".join("{}{}".format(k[:6], v) for k, v in params.items())
        summary.append((name,) + run(name, lambda d, tr, p=params: decode.predict_v3(
            d, kickoff_2nd=None, params=p)))
    keys = sorted(V4_GRID)
    for combo in itertools.product(*(V4_GRID[k] for k in keys)):
        params = dict(zip(keys, combo))
        name = "v4_" + "_".join("{}{}".format(k[:6], v) for k, v in params.items())
        summary.append((name,) + run(name, lambda d, tr, p=params: v4.predict_v4(
            d, kickoff_2nd=None, params=p)))
    for row in summary:
        print("{:<60} spellF1 {:.4f}  macroF1 {:.4f}".format(*row))


if __name__ == "__main__":
    main()
