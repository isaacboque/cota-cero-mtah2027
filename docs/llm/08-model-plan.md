# Model plan — Initial Challenge (v2 → final)

Status: plan, 10 Nov 2026. Target: submit **Mon 16 Nov** (17 Nov has no published hour).
Read `01-rules.md` first. Every parameter in this plan is set on **external data (IDSSE)** or from organiser documents, never on the BAR-ATH ground truth or video.

## 1. What decides the score (design drivers)
Facts from the organisers' `CHALLENGE.md`, `EVALUATION.md`, `DATA.md` and `starter/baseline.py`:

| Fact | Consequence for the model |
|---|---|
| Ranking = **spellF1**: possessions (maximal `H`/`A` runs) matched by temporal IoU, averaged over IoU 0.3–0.7. Tie-break macroF1. | Get the **number and boundaries of possessions** right. Per-frame accuracy is secondary. Flicker kills the score (raw baseline 0.05 vs smoothed 0.24). |
| 1 s late on a boundary → 0.65; 1 frame late → 1.0 | Boundaries need ~0.5 s precision, not frame precision. |
| `D` runs separate possessions (`H H D D H H` = 2 possessions) | A good **dead-ball detector** creates correct splits for free. The baseline's `D` = "ball not seen", which is wrong. |
| `X` is forward-filled with the previous label before spellF1; counts as a miss in macroF1. FAQ: going quiet through an occlusion is "safer than a guess that might split the possession"; at a transition, guess | `X` equals carrying the previous label forward, so writing that label explicitly scores the same on spellF1 and better on macroF1. **Policy: no `X` on graded frames; through ball gaps, carry the current state forward instead of guessing.** |
| Graded range = the two halves only. `games.py`: half 1 = video 11185–90651, half 2 = 110808–190197 | Outside the halves output `D` (not scored). Run all temporal models per half. |
| 2nd half graded from 110808 but kicks off at **113742** (FAQ): 2 934 graded frames, all `D` | Hard rule: `D` until the 2nd-half kick-off (detected from Smart Tagging `Kick Off (Start)` / tracking, falling back to the published frame). Free points. |
| No statistic of the full-match GT is published, so nobody can tune to it | Sanity targets (possession count, duration, D share) come from IDSSE only — never from the public window's 17 possessions / 14.2 s. |
| Ball missing on 41 % of graded frames | Missing ball ≠ dead ball. Carry possession through gaps unless strong evidence of a change or stoppage. |
| Loose ball → last team keeps it. Change only when the other team has the ball **under control**. Single touch, deflection, won aerial duel ≠ change. | Possession is a **sticky state** with a control condition and a minimum dwell, not "nearest player". |
| GT = corrected tracking's own ball-owner + ball-dead flags | External tracking with official ball-status/ball-possession flags is the closest proxy for training/tuning. |
| Tracks: 46 slots, ~20.5 visible, duplicates and swaps; team per slot from `_atd.xml` | Use team-level features (nearest home vs nearest away), never per-player identity. |
| Smart Tagging: 638 automatic phases, incl. `SET PIECES` with `Type` (throw-in, corner, goal kick, free kick, kick-off) and `Team` (N/A for throw-ins); `frame = round(s*25)` | Restart **cue** for `D` → alive transitions and for who restarts. Noisy: use as evidence, not truth. |
| Homography: tactical valid on every frame | Only needed for video work. Ball/pitch bounds come from normalised tracking coordinates (0–1, pitch 105.3 × 68 m). |

## 2. Target architecture
```
ATD (txt+xml) ──► 1. loader/cache ──► 2. features per frame ──► 3. dead-ball score ─┐
Smart Tagging ──────────────────────────────────────────────► restart cues ───────┤
                                                                                    ▼
                                           4. control events ──► 5. temporal decoder (per half)
                                                                                    ▼
                                           6. post-rules (min durations, outside halves = D)
                                                                                    ▼
                                           7. writer (LF CSV, 199 319 rows, sha256)
```

### 2.1 Loader and cache (`pipeline/data.py`)
- Stream `_atd.txt` once (format `frame:p1;p2;…:ball`, groups `x,y,speed`, `NaN` missing) into numpy arrays: `ball_xy[n,2]`, `ball_speed[n]`, `ball_seen[n]`, `players_xy[n,46,2]`, `players_speed[n,46]`, `slot_team[46]`. Coordinates in metres (×105.3, ×68).
- Cache to `data/cache/*.npz` (gitignored with `data/*`). Never publish: frame-level tracking exports count as redistribution (`RULES.md`).
- Same interface for the external dataset (§3) so every later step runs on both.

### 2.2 Per-frame features (`pipeline/features.py`)
Team-level, identity-free:
- `d_home`, `d_away`: distance ball → nearest player of each team; `gap = d_away - d_home`.
- `n_home_r`, `n_away_r`: players of each team within r m of the ball (pressure).
- Ball speed, ball acceleration, ball direction change (kick/touch detector: speed jump or sharp turn).
- Relative speed ball vs nearest player of each team (dribble = small relative speed while close).
- Ball out of bounds: `x < 0 | x > L | y < 0 | y > W` with a margin.
- Ball-missing run length so far; position/time of last sighting.
- Team motion: mean player speed of each team (collapses at stoppages), players' spread.
- Smart Tagging flags per frame: inside a `SET PIECES` interval, its `Type`, its `Team`.

### 2.3 Dead-ball score (`pipeline/deadball.py`)
Evidence for `D` combined into one score per frame:
1. Ball out of bounds (strongest), with hysteresis.
2. Global slowdown: both teams' mean speed under a threshold for ≥ k s, ball static or missing.
3. Long ball-missing run that ends with the ball reappearing static near a line/spot (throw-in, corner, goal kick, centre spot).
4. Smart Tagging set-piece start: the `D` run ends at or just before the restart frame.
5. Goals (Smart Tagging `GOALS`): dead until kick-off.
Output: alive/dead probability or a rule decision. Thresholds come from IDSSE (§3).

### 2.4 Control events (`pipeline/control.py`)
Our written definition of **control** (goes into the technical document): a team gains control when one of its players is within `r_ctrl` m of the ball, the ball's speed relative to that player is under `v_ctrl` m/s, for at least `t_ctrl` frames, and no opponent is closer. Exclusions: one-frame touches, a deflection that keeps the ball's trajectory, aerial balls (if a height proxy is unavailable, require ground-speed consistency after contact).
Output: a sparse list of candidate change events `(frame, team, confidence)` and restart events `(frame, team)` from set pieces.

### 2.5 Temporal decoder (`pipeline/decode.py`) — the core
Three states `H`, `A`, `D`, decoded **per half** with Viterbi (HMM), extended with minimum dwell times (semi-Markov or state-duplication trick):
- Emissions: from §2.2–2.4 (calibrated probabilities, or a small classifier's outputs in v4).
- Transitions: `H↔A` cheap only near a control event; `alive→D` driven by the dead-ball score; `D→H/A` decided by the restart cue (Smart Tagging team, otherwise first team to gain control after the restart).
- Ball-missing frames: neutral emissions, so the state carries through ("loose ball → last team keeps it").
- Minimum durations for `H`/`A` and `D` runs; final step merges micro-runs shorter than the minimum into neighbours.
Pure numpy; no new dependency needed.

### 2.6 Post-rules and writer
- Frames outside the two halves → `D`. Graded frames before the 2nd-half kick-off (110808 … kick-off) → `D`. No `X` on graded frames.
- Reuse `pipeline/make_submission.py`'s writer (LF, deterministic, sha256). Add `--version` so each version is one command.
- Output name: `submissions/cota-cero_vN.csv`; the upload copy is named `<team_name>.csv` (spelling still to confirm).

## 3. External data: where every parameter is learned
**IDSSE** — Bassek et al. 2025, *Scientific Data* 12:195, 7 full Bundesliga 2022/23 matches, TRACAB 25 fps tracking + official events, owner DFL, **CC BY 4.0** (cite it). Loads with kloppy (already in `requirements-starter.txt`): `kloppy.sportec.load_open_tracking_data(match_id=...)`, IDs `J03WPY, J03WMX, J03WN1, J03WOH, J03WOY, J03WPF, J03WQF`.
- Check first (task E1): that the IDSSE tracking exposes per-frame **ball status (alive/dead)** and **ball-owning team**. If yes, that is a ground truth with the same structure as ours (tracking-derived owner + dead flag), so we can build `H/A/D` labels and score with our own copy of `possession_metrics.py`.
- **Degrade IDSSE to look like BAR-ATH input:** remove the ball on ~41 % of alive frames in contiguous gaps, add position noise, drop/duplicate/swap player slots. The degradation parameters may be matched to **aggregate statistics of the BAR-ATH input tracking** (ball-gap lengths, slots per frame). That is an automatic check on provided data, allowed; it never touches the BAR-ATH ground truth or video.
- Protocol: leave-one-match-out over the 7 matches; tune on 6, report spellF1/macroF1 on the 7th; select by mean CV spellF1 (differences < 0.04 are noise, per the organisers). Results go in `docs/llm/05-decisions-log.md`.
- Known shift: TRACAB/DFL's possession flag may not use the same "control" definition as Metrica's corrected tracking. Treat IDSSE as a proxy; prefer robust settings (flat region of the CV curve) over the CV maximum.
- Backup source, only if its licence allows it: Metrica's public sample games (`metrica-sports/sample-data`). Licence: unverified, check before use.
- `data/external/` is gitignored; commit only the loader and degradation code.

## 4. Version ladder
| Version | Content | Selection evidence |
|---|---|---|
| v1 (done) | nearest player + majority ±50 | organiser floor, spellF1 0.2433 full match |
| v2 | §2.1–2.3 + sticky possession with simple control rule + outside-halves `D` + no `X` | IDSSE CV ≥ v1 on IDSSE |
| v3 | §2.4–2.5: HMM/semi-Markov decoder, Smart Tagging restart cues, parameters tuned on IDSSE | IDSSE CV > v2 by ≥ 0.04, or equal and simpler |
| v4 (optional, only if time) | gradient-boosted frame classifier trained on degraded IDSSE, used as HMM emissions | IDSSE CV > v3 by ≥ 0.04 |

The final choice uses IDSSE CV plus the BAR-ATH sanity checks below. Running the public window is allowed as a **correctness check** (does the file score, do the boundaries look misaligned by a constant offset?). It never chooses between versions.

## 5. Sanity checks on BAR-ATH (no ground truth needed)
Printed by `validate_submission.py` and a new `pipeline/report.py`, run and read **by a human only** (these are extracts; not pasted into any AI), and compared against the IDSSE distributions (never against GT):
- Number of possessions and mean duration per half, compared with IDSSE.
- Share of `D` frames and number of stoppages, compared with IDSSE.
- Home share of alive frames (Barcelona at home should be high; sanity only).
- Fragmentation: runs shorter than 1 s (should be ~0 after post-rules).
- Determinism: two runs give the same sha256.

## 6. Work split
No fixed roles; anyone takes any stream or task (see [`docs/team-plan.md`](../team-plan.md)). Streams: A pipeline/loader/writer/report · B IDSSE, degradation, validation harness · C dead-ball, control, decoder · D football rules for control/restarts/loose balls + edge-case tests · E technical document, checklist, organiser emails, form.

## 7. Timeline (Europe/Madrid)
| Day | Milestone |
|---|---|
| Tue 10 | Plan merged. Elena emails the organisers: exact `<team_name>` file spelling and the 17 Nov cut-off hour. |
| Wed 11 | A: loader + cache + report. B/E1: IDSSE loaded, ball status/owner confirmed, `H/A/D` labels built. D: draft control/restart rules. |
| Thu 12 | B: degradation + CV harness scoring v1 on IDSSE. C: dead-ball detector. |
| Fri 13 | **v2** generated on BAR-ATH, validated, logged in `SUBMISSIONS.md`. First form submission with v2 as a safety net. |
| Sat 14 | C: decoder + tuning on IDSSE → **v3**. |
| Sun 15 | Freeze method. Tech doc complete. Reproducibility check on a clean clone (second machine if possible). |
| Mon 16 | Final file, sha256, checklist, edit the form response. Done. |

Rule: if v3 is not clearly better on IDSSE CV by Sunday, ship v2.

## 8. Rules for Claude Code (read before any task)
1. Claude Code is a hosted LLM. The Terms forbid giving it the data "or any extracts thereof". **It never opens or runs anything on BAR-ATH data** (`data/**`, `evaluation/gt/**`): no reads, no printouts, no running the pipeline on it, no aggregate statistics of it. It develops and tests on IDSSE and synthetic data only. A human runs every BAR-ATH command; the only results that may come back to Claude Code are the validator's pass/fail and the sha256.
2. Never read `evaluation/gt/*` and never import it from `pipeline/` or `external/`. Do not run `run_evaluation.py` to compare versions.
3. Every tunable constant lives in one `pipeline/config.py` with a comment giving its source (IDSSE CV run id, organiser doc, or football rule).
4. Each task ends with: tests on synthetic data (`tests/`), a line in `05-decisions-log.md`, a PR with the template filled. No new dependency without noting it.

## 9. Claude Code task queue (in order; each one is a PR)
- **T1 Loader/cache.** `pipeline/data.py`: `load_match(source="barath"|"idsse", ...)` → dict of arrays as in §2.1, plus `halves`. Cache `.npz`. Test on a synthetic 3-line ATD file. Acceptance: shapes, NaN handling, frame offset (`frame_id - 1`).
- **T2 IDSSE adapter (E1).** `external/idsse.py` with kloppy: same array interface, plus `gt_codes` (`H/A/D`) from ball status + owning team (home = first team). Report: share of frames with owner/status present. Acceptance: one match loads and its label counts print.
- **T3 Metric harness.** `pipeline/cv.py`: score any label array against IDSSE `gt_codes` with `evaluation/possession_metrics.py` (import, do not copy), leave-one-match-out loop, results table to `external/results/` (gitignored). Acceptance: v1 logic scored on 7 IDSSE matches.
- **T4 Degradation.** `external/degrade.py`: ball dropout in contiguous gaps (gap-length distribution as a parameter), position noise, slot drop/duplicate. A separate script `external/barath_gap_stats.py` computes the BAR-ATH ball-gap histogram and writes the degradation parameters straight to a local, gitignored `data/cache/degrade_params.json`; a human runs it and nobody pastes its output into an AI. Acceptance: degraded IDSSE has ~41 % ball-missing on alive frames.
- **T5 Features + dead-ball.** `features.py`, `deadball.py` per §2.2–2.3; dead-ball F1 on IDSSE in the CV table.
- **T6 v2.** Sticky possession + control rule + outside-halves `D` + 2nd-half pre-kick-off `D` + no `X`; `make_submission.py --version v2`; `pipeline/report.py` sanity numbers. Acceptance: CV ≥ v1 on degraded IDSSE; deterministic sha256.
- **T7 Smart Tagging cues.** Parse with `starter/load_smart_tagging.py`; restart events `(frame, team|None)`.
- **T8 Decoder v3.** `decode.py` Viterbi with minimum dwell per half; grid search of decoder parameters on IDSSE CV only. Acceptance: CV table + chosen setting in the decisions log.
- **T9 (optional) v4 classifier** on degraded IDSSE (scikit-learn or LightGBM, pinned), used as emissions.
- **T10 Reproducibility.** Pin all used dependencies, README "Reproduce" updated, clean-clone run instructions, final technical document filled from the decisions log.
