"""E1 check: do the IDSSE files expose ball status and ball-owning team? Prints H/A/D label counts
per match (IDSSE only, external CC BY 4.0 data; never BAR-ATH).

    python external/idsse_report.py [--cache-dir data/external/idsse]
"""
import argparse
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def label_counts(d):
    g = np.asarray(d["gt_codes"])
    n = len(g)
    return {"H": int((g == 0).sum()), "A": int((g == 1).sum()), "D": int((g == 2).sum()),
            "unknown": int((g < 0).sum()), "n": n,
            "labelled_share": float((g >= 0).mean()) if n else 0.0,
            "ball_seen_share": float(np.mean(d["ball_seen"])) if n else 0.0}


def main():
    from external import idsse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=os.path.join(ROOT, "data", "external", "idsse"))
    args = ap.parse_args()
    print("{:<8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>9} {:>9}".format(
        "match", "frames", "H", "A", "D", "unknown", "labelled", "ball_seen"))
    for mid in idsse.MATCH_IDS:
        c = label_counts(idsse.load_idsse(mid, args.cache_dir))
        print("{:<8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8.1%} {:>9.1%}".format(
            mid, c["n"], c["H"], c["A"], c["D"], c["unknown"], c["labelled_share"], c["ball_seen_share"]))


if __name__ == "__main__":
    main()
