# Technical document — Team Cota Cero (skeleton)

Required deliverable (PDF or Markdown, a few pages at most). Fill in as decisions land in `docs/llm/05-decisions-log.md`; do not paste match data or frame-level exports.

## 1. Approach
(Pipeline overview: inputs → per-frame signal → temporal model → labels `H`/`A`/`D`/`X`.)

## 2. Assets used, and assets tried and dropped
(Tracking ATD, homography, Smart Tagging, video, external data with name + license. For each dropped asset, why.)

## 3. Possession rules
- Loose balls:
- Challenges / duels (what counts as "control"):
- Restarts (kickoff, throw-in, corner, goal kick, free kick):
- Dead ball (`D`) detection:
- Missing ball (41 % of graded frames) and use of `X`:

## 4. Compliance statement
No hand labels or manual annotation; no training, fitting or calibration on ground-truth possession data or on the provided video; parameters/training from external data only (list with licenses); no provided data uploaded to AI services.

## 5. Limitations

## 6. Reproduction
Environment (pinned versions), data placement (`data/tactical/` or `MTAH_DATA_DIR`), command that regenerates the file, expected sha256 (see `SUBMISSIONS.md`).
