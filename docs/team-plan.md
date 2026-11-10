# Team plan — Cota Cero, Initial Challenge

Team: Isaac, Judit, Iker, Elena. All remote; Europe/Madrid time. No fixed roles: we stay flexible.
Goal: a reproducible, rule-compliant submission that beats the published floor (spellF1 0.2433), **submitted Mon 16 Nov** with a safety-net version already in the form on Fri 13.
Technical plan: [`docs/llm/08-model-plan.md`](llm/08-model-plan.md). Rules: [`docs/llm/01-rules.md`](llm/01-rules.md).

## 1. Non-negotiables (everyone)
1. **No match data in any AI tool.** That includes ChatGPT/Claude/Gemini chats *and* AI features in editors (Copilot, Cursor, Gemini Code Assist) when a data file or its output is open. The Terms say "or any extracts thereof". The repo ships `.cursorignore` and `.aiexclude` for `data/`, `evaluation/gt/` and label CSVs; in VS Code, turn Copilot off while a data file or terminal output with data is on screen.
2. **Each member downloads the data from their own Drive access.** Do not forward the files to each other or upload them anywhere.
3. **No looking at the video to fix or check labels.** Watching to understand possession in general is fine.
4. **No hand labels, no tuning on the public 5 minutes**, no choosing versions by its score.
5. Nothing goes to `main` without a PR. Every method choice gets a line in `docs/llm/05-decisions-log.md`.

## 2. Onboarding
Done for all four members (10 Nov 2026).

## 3. How tasks are taken
No fixed roles. The open work is the task list in `docs/llm/08-model-plan.md` §9 (T1–T10) plus the streams below. Anyone takes any item: say "I take X" in the group chat, do it, open a PR. If something sits unclaimed for a day, Isaac picks someone.

Streams that need covering by someone each day: pipeline/BAR-ATH runs · IDSSE validation · football rules (what "control" is, restarts, loose balls) · technical document · organiser questions and the form.

## 4. How we work
- **Daily sync, 15 min, 21:30** (video call; skip if nobody is blocked). Agenda: done / next / blocked, then decisions.
- **Async update** in the group chat by 13:00 using: `Done · Next · Blocked · Decision needed`.
- **Decisions:** whoever is doing the work proposes; if there is no objection by the next sync it stands, and they log it in `05-decisions-log.md`. Isaac decides ties.
- **PRs:** small, one topic, template checklist filled, one reviewer (anyone but the author). No CI, so the reviewer runs the stated command.
- **BAR-ATH runs** (anything touching `data/`) are done by a human on their own machine. Only the validator's pass/fail and the sha256 are shared with Claude Code.

## 5. Milestones
| Day | Must be true by the end of the day |
|---|---|
| Tue 10 | Docs merged; organisers emailed (cut-off hour, `<team_name>` file spelling); T1–T3 queued |
| Wed 11 | BAR-ATH loader works; IDSSE loads and its ball-status/owner fields are confirmed or ruled out; first page of possession rules written |
| Thu 12 | v1 scored on IDSSE (validation harness works); degradation done; dead-ball detector started |
| **Fri 13** | **v2 validated, sha256 logged, submitted in the form as a safety net** |
| Sat 14 | Decoder tuned on IDSSE → v3 candidate; tech doc sections 1, 3, 5 drafted |
| **Sun 15** | **Go/no-go 20:00**: v3 only if IDSSE CV beats v2 by ≥ 0.04; clean-clone reproducibility check; tech doc complete |
| **Mon 16** | Final file, sha256, checklist, form response edited. Done |
| Tue 17 | Buffer only; no new methods |

## 6. Submission runbook (Mon 16)
1. Someone runs `python pipeline/make_submission.py --version <final>` and `python evaluation/validate_submission.py <file>`.
2. A second person regenerates on another machine; sha256 must match. If not, stop and fix before submitting.
3. Copy the file to the agreed name (`Cota Cero.csv` unless the organisers say otherwise); same for the PDF.
4. Run `docs/llm/06-compliance-checklist.md` together (5 min).
5. Whoever submitted on Fri 13 edits the **same** form response (one response per team, last one counts), from the same Google account that submitted on Fri 13. Screenshot the confirmation into the team chat.
6. Tag the commit: `git tag submission-final && git push --tags`.

## 7. Risks
| Risk | Mitigation |
|---|---|
| IDSSE has no usable ball-status/owner flags | Decide by Wed night: fall back to rule-based v2 with parameters from organiser docs and football rules; drop v3 tuning. |
| Data leaks into an AI tool by accident | Stop, tell the team, write it down; do not hide it. Ask the organisers if needed. |
| v3 late or not better | v2 is already in the form on Fri 13; ship v2. |
| File not reproducible on another machine | Deterministic code, pinned deps, LF writer; second-machine check on Sun and Mon. |
| Unclear rule | Whoever hits it asks the organisers (email or upstream issue) before building on it. |

## 8. After the Initial Challenge
If we are in the top 20: Innovation Challenge 26 Nov – 14 Jan, 10 professional matches, open question. build a shortlist of football questions (see `docs/llm/07-roadmap.md`); one call the week of 23 Nov to choose it.
