# Workflow

## Branches and PRs
- Never commit to `main`. Branch names: `feat/…`, `fix/…`, `docs/…`.
- Open a PR for every pushed work branch; fill the template (`.github/pull_request_template.md`).
- There is currently no CI. Merge only when the owner (Isaac) approves; otherwise leave the PR open.
- Commit messages: imperative, short subject; body states the *source* of any parameter choice.

## Producing a new submission version
1. Implement in `pipeline/`; one command regenerates the file byte for byte (LF endings, fixed seeds, no wall-clock or machine-dependent input).
2. Log the decision in `docs/llm/05-decisions-log.md` (what, why, external source/license).
3. Run `python evaluation/validate_submission.py submissions/cota-cero_vN.csv`.
4. Add a row to `SUBMISSIONS.md`: date, version, sha256, validation result, H/A possession share, segment count/mean length, comment.
5. Run the checklist in `06-compliance-checklist.md`.
6. Only then upload per the organisers' `SUBMISSION.md` instructions (the three deliverables and the form).

## Version selection
Pick by principle and external evidence, never by score on the public 5-minute window. The score column is for control only.

## Working with an LLM
- Give it code and docs, not data. If it needs to understand a file format, point it to `starter/load_*.py` and `DATA.md`.
- Ask it to write scripts you run locally; paste back only aggregate output.
- Have it update `05-decisions-log.md` in the same PR as the change.
