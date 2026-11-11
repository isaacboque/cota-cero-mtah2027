"""Count IDSSE ball frames by raw BallStatus / BallPossession value (external data, CC BY 4.0).

Answers: what share of alive frames (BallStatus=1) carry no usable possession flag (not 1 or 2)?
kloppy maps every such frame to the away team. Prints aggregate counts only.

    python external/idsse_flag_check.py [cache_dir]
"""
import collections
import os
import sys
import xml.etree.ElementTree as ET

from idsse import MATCH_IDS


def count(path):
    c = collections.Counter()
    in_ball = False
    for ev, el in ET.iterparse(path, events=("start", "end")):
        if el.tag == "FrameSet":
            if ev == "start":
                in_ball = el.get("TeamId") == "BALL"
            else:
                el.clear()
        elif el.tag == "Frame" and ev == "end":
            if in_ball:
                c[(el.get("BallStatus"), el.get("BallPossession"))] += 1
            el.clear()
    return c


def main(cache_dir):
    tot_alive = tot_bad = 0
    for mid in MATCH_IDS:
        p = os.path.join(cache_dir, "{}_tracking.xml".format(mid))
        if not os.path.exists(p):
            print(mid, "missing")
            continue
        c = count(p)
        alive = sum(v for (s, _), v in c.items() if s == "1")
        bad = sum(v for (s, o), v in c.items() if s == "1" and o not in ("1", "2"))
        tot_alive += alive
        tot_bad += bad
        print("{} alive={} no_flag={} ({:.3%}) values={}".format(
            mid, alive, bad, bad / max(alive, 1), dict(sorted(c.items(), key=str))))
    print("TOTAL alive={} no_flag={} ({:.3%})".format(tot_alive, tot_bad, tot_bad / max(tot_alive, 1)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/external/idsse")
