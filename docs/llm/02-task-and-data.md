# Task and data

Short orientation. Authoritative definitions are in the organisers' `CHALLENGE.md`, `DATA.md`, `EVALUATION.md` (linked from `README.md`); this file only points the way.

## Task
For every frame of one LaLiga match (**BAR-ATH**, tactical recording) output one label per frame: `H`, `A`, `D` or `X`. See upstream `CHALLENGE.md` for exact label meanings and what counts as possession — do not guess them.

Output: CSV `frame,label`, row *i* = frame *i* of `BAR-ATH_tactical.mp4`, **199 319 rows**, LF line endings, validated by `evaluation/validate_submission.py`. Frame rate is 25 fps (±50 frames = ±2 s).

## Metrics
`spellF1` (segment/spell level) and `macroF1` (frame level). They can rank the same files differently: smoothing windows that barely move macroF1 change spellF1 a lot. Details: upstream `EVALUATION.md`.

## Assets (gated, never committed, never sent to AI)
Live in `data/tactical/` or `$MTAH_DATA_DIR`:
- `BAR-ATH_tactical.mp4` — reference timeline (video)
- `BAR-ATH_tactical_atd.txt` / `_atd.xml` — automatic tracking data, players + ball, and its metadata
- `BAR-ATH_tactical_homography.csv` — one 3×3 matrix per frame
- `BAR-ATH_tactical_smart_tagging.xml` — 638 tactical phases and set pieces
- `data/broadcast/*` — optional, **not** synchronised to the tactical timeline

All paths are derived in `games.py` (`asset_paths(source="tactical"|"broadcast")`). Never hard-code a path elsewhere.

## Ground truth
- Full-match GT is held by the organisers. A 5-minute **public** window is in `evaluation/gt/` for scorer sanity only. Both are off-limits for training, fitting, calibration and model selection (see `01-rules.md`).

## Current baseline
v1 = nearest tracked player to the ball + majority vote ±50 frames (organisers' published best on the full match, spellF1 ≈ 0.2433). Byte-identical to `baseline_smooth50`. Improvements must come from inputs we are allowed to use and parameters justified by external data or organiser documentation.
