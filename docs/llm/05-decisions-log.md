# Decisions log

One entry per method/parameter decision. Newest first. The "Source" field is mandatory and must not be "score on the public window".

Template:
```
## YYYY-MM-DD — short title
- Decision:
- Source / justification: (organiser doc §, paper, external dataset + license)
- Data used to choose it: (external only / none)
- Compliance check: (which rules from 01-rules.md were considered)
- Owner:
```

## 2026-11-10 — Public 5-minute window: not used for tuning
- Decision: treat the public window as scorer sanity / definition reading only; no parameter, feature or version choice depends on it.
- Source / justification: organisers' 10 Nov email (no training/fitting/calibrating on ground-truth possession data; no hand labels on the provided game) is stricter than `RULES.md`, which is silent on the window. Following the stricter text.
- Data used to choose it: none.
- Compliance check: rules 2 and 3 of `01-rules.md`.
- Owner: Isaac

## 2026-11-09 — v1: nearest player to ball + majority vote ±50 frames
- Decision: reuse organisers' `starter/baseline.py` steps with window ±50 frames; LF-only CSV writer.
- Source / justification: window is the one the organisers publish as best on the full match in `EVALUATION.md`; not chosen from the public 5-minute window.
- Data used to choose it: none (organiser-published figure).
- Compliance check: no training, no GT access, no video check, no data sent to AI.
- Owner: Isaac

## 2026-11-10 — ATD loader conventions (T1)
- Decision: `pipeline/data.py` scales normalised 0-1 coordinates by `games.GAMES["BAR-ATH"]["pitch"]` (105.3 x 68.0 m), indexes rows by `frame_id - 1`, and treats a ball/player group with a NaN coordinate as missing. `halves` is `(half, first_row, last_row)`; rows are video frames for BAR-ATH.
- Source / justification: organiser constants in `games.py`; `starter/baseline.py` (parsing, home = first Team).
- Data used to choose it: none (code and synthetic tests only).
- Compliance check: no BAR-ATH data read or run; no GT.
- Owner: Isaac

## 2026-11-10 — IDSSE adopted as external tuning data
- Decision: use IDSSE (Bassek et al. 2025, *Scientific Data* 12:195; owner DFL; **CC BY 4.0**, cite it) as the external dataset for tuning/CV, via `external/idsse.py`. `gt_codes`: H/A = ball alive and owner home/away, D = ball dead, -1 = unknown (kloppy `ball_state`).
- Source / justification: `08-model-plan.md` §3; kloppy 3.18.0 sportec reader exposes per-frame `ball_state` and `ball_owning_team`. Its owner is home if the raw flag is 1 else away (never None), so the owner is only used on alive frames. Match IDs per kloppy: `J03WPY J03WMX J03WN1 J03WOH J03WOY J03WQQ J03WR9` (the plan's `J03WPF`/`J03WQF` do not exist there).
- Data used to choose it: external only (IDSSE); nothing from BAR-ATH.
- Dependency: kloppy is pinned in `requirements-starter.txt` (`kloppy==3.18.0`), not in `requirements.txt`; it is imported lazily and the IDSSE test is skipped in CI.
- Compliance check: rules 1-5 of `CLAUDE.md` respected: no GT, no video, no match data sent to AI. Figshare answers scripted downloads with a WAF challenge, so raw files may need a manual browser download into `data/external/idsse/<id>_meta.xml` and `<id>_tracking.xml`.
- Owner: Isaac

## 2026-11-10 — Validation harness (T3)
- Decision: `pipeline/cv.py` scores with `evaluation/possession_metrics.py` (imported, not copied), temporal metrics per half, IDSSE `gt_codes == -1` treated as X (not graded). `baseline_v1` reproduces starter/baseline.py (nearest player, majority vote +/-50, ties to home) on the array dict. Leave-one-match-out writes `external/results/cv_<name>.csv` (gitignored).
- Source / justification: `08-model-plan.md` section 3 protocol; organiser metric code.
- Data used to choose it: none (synthetic tests only); first real IDSSE CV run is for an interactive session.
- Compliance check: no BAR-ATH data, no `evaluation/gt/`, no run of `run_evaluation.py`.
- Owner: Isaac

## 2026-11-10 — IDSSE degradation to BAR-ATH input conditions (T4)
- Decision: `external/degrade.py` removes the ball on alive frames in contiguous gaps (gap-length histogram as parameter) until 41% of alive frames are missing, adds Gaussian position noise and drops/duplicates player slots; deterministic per seed; `gt_codes` never touched. `external/barath_gap_stats.py` (run by a human only) writes `data/cache/degrade_params.json`.
- Source / justification: DATA.md (ball missing on 41% of graded frames), `08-model-plan.md` section 3: degradation parameters come from aggregate statistics of the BAR-ATH input tracking (allowed automatic check; never GT or video), computed by a human; nothing is pasted into an AI. Defaults in `DEFAULT_PARAMS` (noise sigma, duplicate rate, gap bins) are placeholders until that file exists.
- Data used to choose it: none (synthetic tests only).
- Compliance check: no BAR-ATH data read or run by Claude Code; no GT, no video.
- Owner: Isaac

## 2026-11-10 — Features and dead-ball detector constants (T5)
- Decision: `pipeline/features.py` (team-level, identity-free features; speeds derived from positions) and `pipeline/deadball.py` (score = weighted sum of: out of bounds with hysteresis, global slowdown, long ball-missing run ending static; hard D outside the halves and from 2nd-half grading start to kick-off). All constants in `pipeline/config.py`.
- Source per constant: `FPS`, `PITCH`, `KICKOFF_2ND`=113742 = organiser (games.py, FAQ). `OOB_MARGIN_M`=0.5 = Laws of the Game (ball out when wholly over the line) plus tracking-noise margin, to tune. To tune on IDSSE leave-one-match-out CV (placeholders until then, not set from BAR-ATH GT or video): `R_PRESSURE_M`=5.0, `TURN_MIN_SPEED_MS`=2.0, `OOB_ENTER_FRAMES`=5, `OOB_EXIT_FRAMES`=10, `SLOW_TEAM_SPEED_MS`=1.0, `SLOW_MIN_S`=4.0, `BALL_STATIC_MS`=1.0, `MISSING_RUN_MIN_S`=3.0, `STATIC_WINDOW_FRAMES`=12, `W_OOB`=1.0, `W_SLOW`=0.6, `W_MISSING_STATIC`=0.6, `DEAD_THRESHOLD`=0.5.
- Data used to choose it: none (synthetic tests only).
- Compliance check: no BAR-ATH data read or run; no GT; Smart Tagging cues not used here (T7).
- Owner: Isaac

## 2026-11-10 — v2 sticky possession (T6)
- Decision: `pipeline/control.py` (control = nearest player within `R_CTRL_M`=2.0 m, ball speed relative to that player under `V_CTRL_MS`=3.0 m/s, for at least `T_CTRL_FRAMES`=5 frames), `pipeline/v2.py` (state changes H/A only when the other team has a qualifying control run; D on the dead-ball decision, left to the first team gaining control; carried through ball-missing frames; D outside halves and before the 2nd-half kick-off; never X), `--version v1|v2` in `make_submission.py` (default stays v1), `pipeline/report.py` (sanity numbers).
- Source / justification: `08-model-plan.md` sections 1, 2.4, 2.6. The three control constants are placeholders to tune on IDSSE CV (source: our written control definition), not set from BAR-ATH.
- Data used to choose it: none; synthetic tests only. The IDSSE CV table for v1 vs v2 is pending: no IDSSE files were available in the unattended run.
- Compliance check: no BAR-ATH data read or run; v2 on BAR-ATH is generated and validated by a human.
- Owner: Isaac
