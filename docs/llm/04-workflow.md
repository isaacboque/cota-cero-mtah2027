# Workflow

## Branches and PRs
- Never commit to `main`. Branch names: `feat/…`, `fix/…`, `docs/…`.
- Open a PR for every pushed work branch; fill the template (`.github/pull_request_template.md`).
- CI (`.github/workflows/ci.yml`) runs pytest and the baseline scorer on Python 3.11 and 3.12. Merge only when the owner (Isaac) approves; otherwise leave the PR open.
- Commit messages: imperative, short subject; body states the *source* of any parameter choice.

## Producing a new submission version
1. Implement in `pipeline/`; one command regenerates the file byte for byte (LF endings, fixed seeds, no wall-clock or machine-dependent input).
2. Log the decision in `docs/llm/05-decisions-log.md` (what, why, external source/license).
3. Run `python evaluation/validate_submission.py submissions/cota-cero_vN.csv`.
4. Add a row to `SUBMISSIONS.md`: date, version, sha256, validation result, H/A possession share, segment count/mean length, comment.
5. Run the checklist in `06-compliance-checklist.md`.
6. Only then submit (see "Final submission package" below).

## Final submission package (from upstream `SUBMISSION.md`)
Three deliverables through one Google Form (URL is emailed to registered participants; needs a Google account):
1. **Possession file** — CSV as in `02-task-and-data.md`, ~1.9 MB. Run `validate_submission.py` on the *exact* file to upload.
2. **Public code repository** — source, **pinned dependencies**, install and run instructions, and the command that regenerates the file; someone with the data bundle must get the same file. No match data.
3. **Technical document** — short PDF or Markdown, a few pages at most: approach; assets used and tried-and-dropped; possession rules (loose balls, challenges, restarts, our definition of "control"); limitations; reproduction steps. Skeleton: `docs/technical-document.md`.

Form fields: Team Name (must match registration exactly) · possession file (.csv) · public repo URL · technical document (.pdf or .md).

File naming: `<team_name>.csv` and `<team_name>.pdf` — the scoreboard identifies the team by file name. `pipeline/make_submission.py` writes `submissions/cota-cero_v1.csv`; **copy it to the final upload name** (see open question on the exact spelling in `07-roadmap.md`).

Other facts: one response per team, editable, the last one before the deadline is scored. Deadline **17 Nov 2026, no time or timezone stated** — treat Mon 16 Nov as the real deadline. There is no live leaderboard or feedback; the only pre-deadline signals are the public window and the validator.

## Version selection
Pick by principle and external evidence, never by score on the public 5-minute window. The score column is for control only.

## Working with an LLM
- Give it code and docs, not data. If it needs to understand a file format, point it to `starter/load_*.py` and `DATA.md`.
- Ask it to write scripts you run locally; paste back only aggregate output.
- Have it update `05-decisions-log.md` in the same PR as the change.
