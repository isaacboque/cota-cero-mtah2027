# CLAUDE.md — Cota Cero, More Than a Hack 2027

Entry point for any LLM/agent working in this repo. Keep it short; details live in `docs/llm/`.

**Task:** per-frame ball possession (`H`, `A`, `D`, `X`) for one LaLiga match (BAR-ATH) from automatic tracking data. Score: spellF1 / macroF1. Initial Challenge submission due **17 Nov 2026**.

## Hard rules (competition compliance) — read `docs/llm/01-rules.md` before any task
Anything not explicitly allowed is forbidden. In particular, never:
1. Upload, paste or send match data (tracking, video, smart tagging, homography, ground truth) to any AI service — **including you**. Do not read/cat/print the contents of anything under `data/` or any `*.csv` label set into the conversation. The organisers' Terms forbid making the data "or any extracts thereof" available to any hosted LLM. Work from code, the organisers' public docs, external data (IDSSE) and synthetic data only; never run commands on BAR-ATH data yourself.
2. Check an output against the video, or create hand labels / manual data on the provided match.
3. Train, fit, tune or calibrate on the ground truth (including `evaluation/gt/*_public*`) or on the provided video. Parameters/training come from **external data only**, with a license we hold.
4. Commit match data or full-match label sets (repo is public; see `.gitignore`).
5. Choose a version by its score on the public 5-minute window.

If a request would break one of these, stop and say which rule.

## Map
- `docs/llm/README.md` — index of the LLM docs
- `docs/llm/01-rules.md` — rules, allowed/forbidden, gray-area calls
- `docs/llm/02-task-and-data.md` — task, labels, assets, frame alignment
- `docs/llm/03-repo-map.md` — what each file does
- `docs/llm/04-workflow.md` — branches, PRs, submission procedure, log
- `docs/llm/05-decisions-log.md` — dated decisions and their compliance rationale
- `docs/llm/06-compliance-checklist.md` — run before every PR/submission
- `docs/llm/07-roadmap.md` — schedule, approach ladder, Round 2 outline, open questions
- `docs/team-plan.md` — team roles, rituals, day-by-day plan, submission runbook
- `docs/llm/08-model-plan.md` — model architecture, external data (IDSSE), work split, timeline, Claude Code task queue

Organisers' docs (CHALLENGE, RULES, EVALUATION, SUBMISSION, DATA, FAQ) are linked from `README.md`, not copied. They win over anything here if they disagree.

## Commands
```bash
pip install -r requirements.txt
python evaluation/run_evaluation.py                      # scores shipped baselines, needs no data
python pipeline/make_submission.py                       # needs data in data/tactical/
python evaluation/validate_submission.py submissions/<file>.csv
```

## Conventions
- Surgical edits over rewrites; no new dependencies without noting them in `requirements.txt` and `05-decisions-log.md`.
- CSVs are written with LF endings (`pipeline/make_submission.py`); record sha256 in `SUBMISSIONS.md`.
- Every modelling choice (window, threshold, feature) gets a line in `docs/llm/05-decisions-log.md` stating its source (organiser doc, external dataset, literature) — never "looked good on the public window".
- Work on a branch, open a PR; fill in the PR template checklist.
