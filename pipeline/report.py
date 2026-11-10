"""Sanity numbers for a label array (08-model-plan.md section 5). No ground truth involved.

For BAR-ATH output this is run and read by a human only. Codes: 0 H, 1 A, 2 D, 3 X.
"""
import numpy as np

from pipeline import config


def _runs(codes):
    if len(codes) == 0:
        return []
    cut = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    b = np.concatenate(([0], cut, [len(codes)]))
    return [(int(b[i]), int(b[i + 1]), int(codes[b[i]])) for i in range(len(b) - 1)]


def sanity(codes, halves, fps=config.FPS):
    codes = np.asarray(codes)
    per_half, short, stoppages = [], 0, 0
    inside = np.zeros(len(codes), dtype=bool)
    for h, a, b in np.asarray(halves).reshape(-1, 3):
        inside[a:b + 1] = True
        runs = _runs(codes[a:b + 1])
        spells = [(s, e) for s, e, c in runs if c in (0, 1)]
        per_half.append({"half": int(h), "possessions": len(spells),
                         "mean_duration_s": float(np.mean([e - s for s, e in spells])) / fps
                         if spells else 0.0})
        short += sum(1 for s, e in spells if e - s < fps)
        stoppages += sum(1 for _, _, c in runs if c == 2)
    g = codes[inside]
    alive = int(np.sum((g == 0) | (g == 1)))
    return {"per_half": per_half,
            "d_share": float(np.mean(g == 2)) if len(g) else 0.0,
            "stoppages": stoppages,
            "home_share_alive": float(np.sum(g == 0)) / alive if alive else 0.0,
            "runs_under_1s": short}


def format_report(r):
    lines = ["half {half}: possessions {possessions}, mean {mean_duration_s:.1f} s".format(**h)
             for h in r["per_half"]]
    lines.append("D share {:.3f}  stoppages {}  home share of alive {:.3f}  runs < 1 s {}".format(
        r["d_share"], r["stoppages"], r["home_share_alive"], r["runs_under_1s"]))
    return "\n".join(lines)


def print_report(codes, halves):
    print(format_report(sanity(codes, halves)))
