# Claude Code playbook — how we use it on this repo

How Claude Code (CC) builds the tasks in [`08-model-plan.md`](08-model-plan.md) §9 without ever touching the match data. Read [`01-rules.md`](01-rules.md) first.

## 1. The one constraint that shapes everything
The Terms forbid giving any hosted LLM the data "or any extracts thereof". CC is a hosted LLM. So:
- **CC never runs anything on BAR-ATH**, never reads `data/`, `evaluation/gt/`, `submissions/` or label CSVs, and never runs the scorer, validator, starter scripts or notebooks (the scorer prints public-GT scores, which are extracts too).
- CC works on **code, tests with synthetic data, and IDSSE** (external, CC BY 4.0).
- **Humans** run every command that touches BAR-ATH and keep its output out of AI tools. The only things that may go back to CC: "validator passed/failed" and a sha256.

Three layers enforce this:
1. **Physical:** CC works in a clone with **no data inside**. Keep the data outside every clone (e.g. `C:\Users\isboq\mtah-data\tactical\`) and point to it with `MTAH_DATA_DIR`, set only in the terminal where a human runs BAR-ATH commands, never globally.
2. **Permissions:** `.claude/settings.json` (committed) denies reading `data/`, ground truth, submissions and reports, and denies the commands that run on the match (`make_submission`, `run_evaluation`, `validate_submission`, `starter/`, `barath_gap_stats`, `jupyter`).
3. **Instructions:** `CLAUDE.md` rule 1 and every queued task repeat it.

## 2. Two ways to run CC
| Mode | When | How |
|---|---|---|
| **Unattended handoff** (PC lane) | Well-defined code tasks with tests; you are away | Append to `Projects/_handoff/TASKS.md`; the hourly `ClaudeCode-HandoffCheck` runs CC headless (max 45 min per run). It can edit, run `pytest`, commit to a work branch, push and open a PR. It cannot run other scripts, so it proves work with tests only. Results: `_handoff/DIGEST.md`, phone notification, vault `Handoff Digest`. |
| **Interactive session** | Exploratory work, IDSSE runs, CV tables, debugging; anyone on the team with Claude Code | Open CC in your data-free clone and paste the kickoff prompt (§6). Run BAR-ATH commands yourself in a separate, non-CC terminal. |

**Cloud lane (vault `_System/Queue.md`): not used for now.** Its rules exclude public repos, and this repo must be public. Lifting that for this repo (it holds nothing private) is Isaac's call; until then, use the PC lane or interactive sessions.

## 3. One-time setup (Isaac, ~15 min)
1. Move the match data out of the repo folder: `C:\Users\isboq\cota-cero-mtah2027\data\tactical\*` → `C:\Users\isboq\mtah-data\tactical\`. Check `...\cota-cero-mtah2027\data\` holds only `README.md`.
2. Create the agent clone the handoff runner can reach: `git clone https://github.com/isaacboque/cota-cero-mtah2027 C:\Users\isboq\OneDrive\Escriptori\Projects\cota-cero-mtah2027`. No data there, ever.
3. Add the repo → vault note mapping in `Projects/CLAUDE.md`: `cota-cero-mtah2027` → `Projects/Hackathons 2026-27.md`.
4. For BAR-ATH runs use a plain terminal (not a CC terminal): `$env:MTAH_DATA_DIR = "C:\Users\isboq\mtah-data"`, then the commands in §5.
5. Merge T0 (CI) first. With a passing CI check the runner may merge its own PRs (your rule); without CI every PR waits for you.
Teammates: same idea with their own clone; data outside it; `.claude/settings.json` comes with the repo.

## 4. Batches (queue a batch once the previous one is merged; each item = one PR)
Dependencies: T0 → everything · T1 → T3, T5, T6 · T2 → T3 → T4 → T8 · T5, T7 → T6 → T8.

| Batch | Queue on | Items | Human step after |
|---|---|---|---|
| 1 | Tue 10 | T0 CI, T1 loader, T2 IDSSE adapter | Review/merge; run the T1 loader on BAR-ATH yourself (it should print only shapes) |
| 2 | Wed 11 | T3 validation harness, T4 degradation, T5 features + dead-ball | Run `external/barath_gap_stats.py` (writes `data/cache/degrade_params.json`); run the IDSSE CV in an interactive session |
| 3 | Thu 12 | T6 v2 + report, T7 Smart Tagging cues | **Fri 13:** run v2 on BAR-ATH, validate, log sha256, submit the form |
| 4 | Fri 13 | T8 decoder + tuning grid on IDSSE | Sat/Sun: tuning runs (interactive); go/no-go Sun 20:00 |
| 5 | Sun 15 | T10 reproducibility, README, pinned deps for anything added | Mon 16: final run on two machines, submit |

T9 (classifier) only if Batch 4 lands early. A task that does not fit in one 45-minute run gets split before queuing.

## 5. Human-only commands (never in CC)
```powershell
$env:MTAH_DATA_DIR = "C:\Users\isboq\mtah-data"
python pipeline/make_submission.py --version v2
python evaluation/validate_submission.py submissions/cota-cero_v2.csv
python external/barath_gap_stats.py              # writes data/cache/degrade_params.json
python evaluation/run_evaluation.py              # public window = correctness check only, never selection
```
Share back with CC only: pass/fail and the sha256. Sanity numbers from `pipeline/report.py` stay with the team.

## 6. Kickoff prompt for an interactive session
```
Read CLAUDE.md and docs/llm/01-rules.md, 08-model-plan.md, 09-claude-code-playbook.md.
You must not read data/, evaluation/gt/, submissions/ or label CSVs, and must not run
anything on BAR-ATH. Work only with code, synthetic tests and IDSSE.
Task: <Tn from 08-model-plan.md §9, or a description>.
Branch: feat/<slug> from an up-to-date main. Done = tests pass (python -m pytest -q),
a line in docs/llm/05-decisions-log.md for any parameter, PR opened with the template filled.
If a modelling or rules decision comes up, take the smallest reasonable option and flag it in the PR.
```

## 7. Handoff task template (for `TASKS.md`)
Every item stands alone (the run has no memory):
```
- [ ] cota-cero-mtah2027: <Tn title>. Read CLAUDE.md, docs/llm/01-rules.md and 08-model-plan.md §<x> first.
  Never read data/, evaluation/gt/, submissions/ or label CSVs; never run pipeline, scorer, validator or starter scripts.
  Goal: <exact goal>. Files: <paths>. Follow: <existing pattern>.
  Verify: python -m pytest -q <tests>. Done = branch feat/<slug> pushed, PR with template filled,
  decisions-log line if a parameter was set. Product/rules decision → smallest option, flag it in RESULTS.md.
```

## 8. Reading results and reviewing
- Phone: notification + vault `Handoff Digest`. PC: `_handoff/DIGEST.md`, detail in `RESULTS.md`.
- Review each PR against `06-compliance-checklist.md`: in particular, no code path in `pipeline/` or `external/` reads `evaluation/gt/`, and new constants have a source in `pipeline/config.py`.
- Blocked items get `[blocked YYYY-MM-DD]`; answer the question, then remove the tag to retry.
