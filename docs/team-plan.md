# Team plan — Cota Cero, Initial Challenge

Team: Isaac (lead, merges PRs), Judit, Iker, Elena. All remote; Europe/Madrid time.
Goal: a reproducible, rule-compliant submission that beats the published floor (spellF1 0.2433), **submitted Mon 16 Nov** with a safety-net version already in the form on Fri 13.
Technical plan: [`docs/llm/08-model-plan.md`](llm/08-model-plan.md). Rules: [`docs/llm/01-rules.md`](llm/01-rules.md).

## 1. Non-negotiables (everyone)
1. **No match data in any AI tool.** That includes ChatGPT/Claude/Gemini chats *and* AI features in editors (Copilot, Cursor, Gemini Code Assist) when a data file or its output is open. The Terms say "or any extracts thereof". The repo ships `.cursorignore` and `.aiexclude` for `data/`, `evaluation/gt/` and label CSVs; in VS Code, turn Copilot off while a data file or terminal output with data is on screen.
2. **Each member downloads the data from their own Drive access.** Do not forward the files to each other or upload them anywhere.
3. **No looking at the video to fix or check labels.** Watching to understand possession in general is fine.
4. **No hand labels, no tuning on the public 5 minutes**, no choosing versions by its score.
5. Nothing goes to `main` without a PR. Every method choice gets a line in `docs/llm/05-decisions-log.md`.

## 2. Onboarding (by Wed 11, each member)
- [ ] Registration confirmed with team name exactly **Cota Cero**; Drive access received (arrives up to 72 h after registering). If missing on Thu 12, tell Elena, who emails the organisers.
- [ ] GitHub username sent to Isaac; accepted the collaborator invite.
- [ ] Clone, `pip install -r requirements.txt`, `python evaluation/run_evaluation.py` runs (needs no data).
- [ ] Data unpacked into `data/tactical/` (or `MTAH_DATA_DIR`); `python starter/load_atd.py` runs locally.
- [ ] Read `CLAUDE.md`, `docs/llm/01-rules.md`, `02-task-and-data.md`, `08-model-plan.md` and the organisers' `CHALLENGE.md`.
- [ ] Google account ready (needed to upload in the form).

## 3. Roles
| Area | Owner | Backup | Deliverable |
|---|---|---|---|
| Pipeline, repo, merges, final file | Isaac | Judit | `pipeline/`, `SUBMISSIONS.md`, sha256 |
| External data (IDSSE), validation harness, decoder tuning | Judit | Isaac | `external/`, CV tables, decisions log entries |
| Football rules: what "control" is, restarts, loose balls, edge cases; review sanity numbers | Iker | Isaac | rules text for tech doc §3, edge-case list for tests |
| Technical document, compliance checklist, organiser emails, form | Elena | Iker | `docs/technical-document.md` → PDF, the form response |
| Claude Code queue (T1–T10) | Isaac | Judit | one PR per task |

## 4. How we work
- **Daily sync, 15 min, 21:30** (video call; skip if nobody is blocked). Agenda: done / next / blocked, then decisions.
- **Async update** in the group chat by 13:00 using: `Done · Next · Blocked · Decision needed`.
- **Decisions:** whoever owns the area proposes; if there is no objection by the next sync it stands, and the owner logs it in `05-decisions-log.md`. Isaac decides ties.
- **PRs:** small, one topic, template checklist filled, one reviewer (anyone but the author). No CI, so the reviewer runs the stated command.
- **BAR-ATH runs** (anything touching `data/`) are done by a human on their own machine. Only the validator's pass/fail and the sha256 are shared with Claude Code.

## 5. Day by day
| Day | Isaac | Judit | Iker | Elena |
|---|---|---|---|---|
| **Tue 10** | Merge PR #2; add collaborators; queue T1–T3 for Claude Code | Onboarding | Onboarding | Onboarding; email organisers: cut-off hour, `<team_name>` file spelling |
| **Wed 11** | Review T1 (loader) | T2: IDSSE loaded, confirm ball status + owner fields | Draft control/restart/loose-ball rules (1 page) | Tech-doc structure from the skeleton; compliance section |
| **Thu 12** | Review T3/T4 | T3/T4: CV harness, v1 scored on IDSSE; degradation | Edge cases from the rules → test cases list | Chase Drive access issues; start §2 assets |
| **Fri 13** | Run v2 on BAR-ATH, validate, log sha256 | T5/T6 review, v2 on IDSSE CV | Read v2 sanity numbers (vs IDSSE) | **Submit v2 in the form** (safety net) |
| **Sat 14** | T7/T8 decoder with Claude Code | Tune decoder on IDSSE CV → v3 candidate | Review possession rules vs implemented code | Fill §1, §3, §5 of the tech doc from the decisions log |
| **Sun 15** | Run v3 on BAR-ATH; **go/no-go 20:00**: v3 only if IDSSE CV beats v2 by ≥ 0.04 | Reproducibility test on a clean clone | Final read of the tech doc | Tech doc complete; export PDF |
| **Mon 16** | Final file, sha256, `SUBMISSIONS.md`, pin dependencies | Second clean-clone run, same sha256 | Checklist review | **Edit the form response with the final file, repo URL, PDF** |
| Tue 17 | Buffer only; no new methods | | | |

## 6. Submission runbook (Mon 16)
1. Isaac runs `python pipeline/make_submission.py --version <final>` and `python evaluation/validate_submission.py <file>`.
2. Judit regenerates on a second machine; sha256 must match. If not, stop and fix before submitting.
3. Copy the file to the agreed name (`Cota Cero.csv` unless the organisers say otherwise); same for the PDF.
4. Run `docs/llm/06-compliance-checklist.md` together (5 min).
5. Elena edits the **same** form response (one response per team, last one counts), from the same Google account that submitted on Fri 13. Screenshot the confirmation into the team chat.
6. Tag the commit: `git tag submission-final && git push --tags`.

## 7. Risks
| Risk | Mitigation |
|---|---|
| IDSSE has no usable ball-status/owner flags | Decide by Wed night: fall back to rule-based v2 with parameters from organiser docs and football rules; drop v3 tuning. |
| Someone's Drive access does not arrive | Not blocking for the team: only Isaac and Judit need the data to run BAR-ATH. |
| Data leaks into an AI tool by accident | Stop, tell Isaac, write it down; do not hide it. Ask the organisers if needed. |
| v3 late or not better | v2 is already in the form on Fri 13; ship v2. |
| File not reproducible on another machine | Deterministic code, pinned deps, LF writer; second-machine check on Sun and Mon. |
| Unclear rule | Owner asks the organisers (email or upstream issue) before building on it. |

## 8. After the Initial Challenge
If we are in the top 20: Innovation Challenge 26 Nov – 14 Jan, 10 professional matches, open question. Iker leads the football question shortlist (see `docs/llm/07-roadmap.md`); one call the week of 23 Nov to choose it.
