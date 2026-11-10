"""Team Cota Cero: possession file v1 (nearest player to the ball + majority-vote smoothing).

One command regenerates the submission byte for byte:

    python pipeline/make_submission.py                 # writes submissions/cota-cero_v1.csv
    python evaluation/validate_submission.py submissions/cota-cero_v1.csv

v1 reuses the organisers' reference steps (starter/baseline.py) with a +/-50 frame window. That
window is the one the organisers publish as best on the FULL match (EVALUATION.md); it was not
chosen by looking at the public 5-minute window, which the rules forbid for tuning.

The only thing added here is the file contract: the CSV is always written with "\\n" line endings,
so the same input gives the same sha256 on Windows, macOS and Linux (the organisers' writer uses
the platform default, which is CRLF on Windows).
"""

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "starter"))

import baseline  # noqa: E402

TEAM = "cota-cero"
VERSION = "v1"
WINDOW = 50  # half-width of the majority vote, in frames (2 s each side at 25 fps)
OUT_DIR = os.path.join(ROOT, "submissions")


def write_csv(path, labels):
    """frame,label CSV with LF line endings on every platform."""
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", newline="\n") as handle:
        handle.write("frame,label\n")
        handle.writelines("{},{}\n".format(frame, label) for frame, label in enumerate(labels))
    return path


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", type=int, default=WINDOW, help="v1 only")
    parser.add_argument("--out", default=OUT_DIR)
    parser.add_argument("--version", choices=("v1", "v2", "v3"), default=VERSION)
    args = parser.parse_args()

    if args.version in ("v2", "v3"):
        import numpy as np
        import games
        from pipeline import data
        meta, raw = games.require(["atd_meta", "atd_raw"])
        d = data.load_barath(meta, raw, n_frames=games.source_frames())
        if args.version == "v2":
            from pipeline import v2
            codes = v2.predict_v2(d)
        else:
            import load_smart_tagging
            from pipeline import decode, restarts
            home, away = baseline.team_names(meta)
            cues = restarts.restart_events(load_smart_tagging.load(), {home: 0, away: 1})
            codes = decode.predict_v3(d, restarts=cues)
        labels = np.array(["H", "A", "D"])[codes]
    else:
        codes = baseline.build()
        labels = baseline.smooth(codes, args.window)
    path = write_csv(os.path.join(args.out, "{}_{}.csv".format(TEAM, args.version)), labels)

    counts = {label: int((labels == label).sum()) for label in ("H", "A", "D")}
    print("wrote {}".format(os.path.relpath(path, ROOT)))
    print("rows {}  H {}  A {}  D {}".format(len(labels), counts["H"], counts["A"], counts["D"]))
    print("sha256 {}".format(sha256(path)))
    print("next: python evaluation/validate_submission.py {}".format(os.path.relpath(path, ROOT)))


if __name__ == "__main__":
    main()
