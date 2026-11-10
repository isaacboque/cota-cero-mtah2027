# Rules (from the organisers' clarification email, 10 Nov 2026)

Principle (verbatim spirit): **anything that is not explicitly allowed is not permitted.** Each team is responsible for its own compliance.

## Not allowed
- Checking your output against the video.
- Hand labels, human-produced data or any other data created manually on the provided game.
- Uploading the provided data to AI services.
- Training, fitting or calibrating the algorithm on the ground-truth possession data or on the provided video.

## Allowed
- Automatic checks using only the provided data.
- Inspecting the provided data and the video to understand what counts as possession (understanding, not labelling or tuning).
- Using as input the video, the automatic tracking data, the smart tagging or any other generated data, **as long as the algorithm was not trained on the ground truth or on the provided video**.
- Providing files of intermediate steps.
- Using any dataset we have the rights to use. Check the license first.

## Training and tuning
- Training/retraining: **external data only**.
- Tunable parameters (smoothing windows, thresholds, weights): tune on **external data only** — never on the ground-truth possession data, never on the provided video.

## Admin
- Each member accepts the terms individually by registering; all members use the exact same team name (**Cota Cero** — same spelling, spacing, capitalisation). Registration deadline was 10 Nov 2026.
- Drive access is individual (within 72 h of registering).
- Submission instructions: to be sent by the organisers; check `SUBMISSION.md` upstream.

## Additions from the organisers' repo documents (read 10 Nov 2026)
- `RULES.md`: any method is allowed if organisers can access and inspect it and the technical document explains it; pre-trained models, LLMs (hosted or local), commercial APIs and external data are allowed. A private in-house model or unavailable internal dataset is the one thing ruled out — ask first.
- `RULES.md`: improving or replacing the provided tracking/tagging/homography is explicitly legitimate.
- `RULES.md`: do not use the full-match ground truth, or anything derived from it, "beyond the 5 minutes published in this repository".
- `RULES.md`: running our repo on the provided data must reproduce our submission — "not approximately, the same file".
- `RULES.md`: do not redistribute the data, **nor publish derived data that would reconstruct it** (frame-level tracking exports, clipped video, and similar). Our submission CSV is a label set, not tracking, but never commit intermediate frame-level exports of tracking or video.
- Enrolment terms (not `RULES.md`) are the final authority on what is permitted.

### Known tension, resolved conservatively
`RULES.md` is silent on whether the public 5 minutes may be used for tuning/validation, and says small hand-labelled sets used to train/validate are "fine and normal". The organisers' 10 Nov email is stricter and later: no hand labels or manual data on the provided game, and no training/fitting/calibrating on ground-truth possession data. **We follow the stricter reading**: the public window is for scorer sanity and for reading the definition of possession, never for choosing parameters, features or versions. If the team ever wants a looser reading, ask the organisers in writing first (open an issue upstream, as `RULES.md` suggests).

## What this means for an LLM/agent in this repo
1. **Data never enters your context.** "Uploading the provided data to AI services" includes pasting rows, printing file heads, or reading `data/**` with a tool. Allowed: reading code, file names, shapes/dtypes, counts and aggregate numbers that code computed locally and that reveal no per-frame content. When in doubt, write a script for the human to run and discuss only the summary they paste back.
2. **No ground truth in the loop.** `evaluation/gt/*_public*` (5-minute public window) exists for the organisers' scorer. Do not use it to select features, windows, thresholds or model versions. Reporting a score is fine; deciding by it is not. Do not write code that reads it inside `pipeline/`.
3. **No video verification.** Do not build or suggest steps where a person watches the video to confirm/fix labels. Watching to understand the concept of possession is fine, and must not turn into per-frame corrections.
4. **Method choices need an external justification:** organiser baseline, published literature, or an external dataset we have rights to (record license in `05-decisions-log.md`).
5. **Gray area → ask.** If unsure whether something is allowed, treat it as not allowed and ask the human, who can ask the organisers.
6. **Public repo.** Never commit data, video, `*_possession_gt*`, or full-match label CSVs (only `baseline_*.csv` are tracked on purpose).

## Quick examples
| Idea | Verdict |
|---|---|
| Nearest-player-to-ball + majority vote, window from organiser docs | OK |
| Picking the smoothing window that maximises score on the public 5 min | **No** (tuning on GT) |
| Learning a classifier on another league's tracking data we are licensed to use | OK, log the license |
| Watching the video to correct wrong segments in our output | **No** |
| Pasting 200 rows of the ATD into a chat to "see the format" | **No** |
| Looking at `starter/` notebooks' own outputs / schemas in docs | OK |
| Unit test that runs on synthetic/fabricated tracking data | OK |
| Using smart_tagging.xml as an input feature | OK (generated data, not GT) |
