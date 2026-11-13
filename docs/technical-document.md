# Technical document — Team Cota Cero

Initial Challenge, More Than a Hack 2027. Task: one label per frame (`H`, `A`, `D`, `X`) for the LaLiga match BAR-ATH. Every modelling choice below has a dated entry with its source in `docs/llm/05-decisions-log.md`.

> **Draft status (13 Nov 2026).** Written from the decisions log. Items marked **[TO CONFIRM]** depend on the version that is finally submitted and on checks that only a human can run on the provided data. Fill them in before upload.

## 1. Approach

Rule-based pipeline with a temporal model; nothing is trained or fitted on the provided match.

1. **Load** the automatic tracking data (ATD): player and ball positions per frame, scaled to metres with the organisers' pitch size (105.3 x 68.0 m, 25 fps). A ball or player group with a NaN coordinate counts as missing.
2. **Per-frame signal**: team-level features that do not need player identity (speeds from a centred velocity over a few frames, team speed, distance of the ball to the nearest player of each team, ball out of bounds).
3. **Contacts**: a team *contacts* the ball when one of its players is the nearest and (a) controls it for a minimum time, or (b) the ball's velocity changes sharply next to that player (a touch).
4. **Dead ball (`D`)**: a score built from the ball leaving the pitch, a global slowdown of both teams, and a long ball-missing run that ends static, plus restart cues from Smart Tagging.
5. **Possession state machine** (versions v2 and v4): the state changes only when the other team confirms a sequence of contacts; the change is backdated to its first contact. v3 replaces the state machine with a Viterbi decoder (minimum dwell time).
6. **Output**: one label per video frame, 199 319 rows, LF line endings, checked with the organisers' `validate_submission.py`.

Versions: v1 = organisers' reference (nearest player + majority vote over +/-50 frames); v2 = sticky possession; v3 = Viterbi decoder; v4 = possession rules of our team document "Reglas de posesión" v0.2 (see section 3). **Submitted version: [TO CONFIRM].**

## 2. Assets used, and assets tried and dropped

| Asset | Use |
|---|---|
| Tactical ATD (`BAR-ATH_tactical_atd.txt` + `.xml`) | Main input: player and ball tracks, team metadata (home = first Team). |
| Smart Tagging (`..._smart_tagging.xml`) | Restart cues only: set pieces (throw-in, corner, goal kick, free kick, kick-off) and goals. Treated as evidence, not truth: it is automatic and its windows are accurate to about a second. |
| Homography | Not used for the labels. |
| Video, broadcast data | Not used. |
| Public 5-minute ground truth | Not used for any choice (see section 4). |
| **IDSSE** (Bassek et al. 2025, *Scientific Data* 12:195; owner DFL; CC BY 4.0), 7 matches | External data for validation and for setting parameters. Loaded from the Hugging Face mirror `pysport/idsse-data` through kloppy 3.18.0. |

Tried and not adopted, all on IDSSE (decisions log, 11 Nov): ball-gap interpolation (+0.000 to +0.004 spellF1), Savitzky-Golay ball smoothing (-0.003 to -0.007), a control signal without the speed condition (-0.034 to +0.013), a restart rule that ends a dead run only when the ball is struck (< 0.001), the Viterbi decoder v3 (-0.0012 against v2; it does not beat v2 by the required 0.04). A change was accepted only if it improved spellF1 by more than 0.04 with the same sign on seeds 0/1/2.

**Validation protocol.** IDSSE is complete (ball seen on every frame), so before scoring we degrade it to the conditions of the BAR-ATH input: contiguous ball gaps until about 41 % of alive frames are missing, track duplicates and swaps, and position jitter. Scoring is leave-one-match-out spellF1 against the raw IDSSE labels and against labels with owner runs shorter than 1 s absorbed into the neighbour. The degradation parameters come from aggregate statistics of the BAR-ATH *input* tracking (gaps, jitter, duplicates), computed by a human with `external/barath_gap_stats.py`; they involve no ground truth and no video. **[TO CONFIRM: ticket #25, whether this run has been done and recorded.]**

## 3. Possession rules

Our definition of **control**: the nearest player is within 2.0 m of the ball, the ball's speed relative to that player stays below 3.0 m/s, for at least 5 frames (0.2 s). A **touch** is the nearest player within 2.0 m while the ball's velocity changes by more than 4.0 m/s. A ball passing a player at constant velocity is not a contact; this covers an aerial ball over a player (the tracking has no height) and a rival next to the ball who does not touch it.

- **Change of possession.** Only when the other team confirms a sequence: consecutive contacts of one team (within a gap limit), confirmed by one control run or by two contacts (a pass to a teammate). Lone touches, deflections, rebounds back to the team in possession and long 50-50 duels never confirm. The change is written at the first contact of the confirming sequence.
- **Loose balls.** The team that last had possession keeps it (organiser rule); the state does not change without a confirmed sequence.
- **Challenges and duels.** A challenge produces a change only when the rival's sequence is confirmed as above; long 50-50 duels and lone touches never confirm.
- **Restarts** (kick-off, throw-in, corner, goal kick, free kick). After a dead run, the restarting team takes possession as soon as the ball is put back in play: the Smart Tagging team if present, otherwise the taker found in the tracking (nearest player to the static ball, throw-ins are tagged N/A in Smart Tagging), otherwise the first team to confirm a sequence.
- **Dead ball (`D`).** Score from: ball out of bounds (margin 0.25 m, with hysteresis), the median speed of each team below 2.5 m/s (median, not mean, because one duplicated or switched track reads 50+ m/s), a long ball-missing run that ends static, and a static ball with a Smart Tagging set-piece or goal cue near it (each cue alone stays below the threshold, so a goalkeeper holding the ball is not `D`). A dead run lasts while the ball stays static, capped at 5 s. `D` is also written outside the graded halves and from the start of the 2nd-half grading (frame 110 808) to its kick-off (113 742), as the FAQ specifies.
- **Fouls and offside.** No whistle detection; possession is kept until the stoppage is visible in the tracking.
- **Missing ball (41 % of graded frames).** Possession is carried through the gap and never set to `D` by the gap alone. The change, if the other team appears with the ball, is written when the ball reappears (`GAP_PLACEMENT = "reappear"`).
- **Use of `X`.** None: `X` would be filled with the previous label by spellF1 and costs on a real change, so we always give an answer.

Sources: IFAB Laws 8 and 9; organisers' CHALLENGE, RULES, EVALUATION, FAQ and `starter/01_smart_tagging.ipynb` (tags open about 3.5 s before the restart). Every threshold is a named constant in `pipeline/config.py` with its source; constants for the Smart Tagging cues cannot be tuned on IDSSE (no Smart Tagging there) and keep their documented value.

**Evidence on IDSSE (degraded, leave-one-match-out, spellF1).** v1 about 0.19. v4 reached 0.303 before and 0.387 after the dead-ball fixes of ticket #23 (+0.08 on every seed); on clean IDSSE 0.462 and 0.579. The dead-ball share predicted went from 33 % to 55 % degraded against a reference of 45 %. These are IDSSE numbers; the BAR-ATH score is not known to the team. **[TO CONFIRM: final IDSSE table for the submitted version.]**

## 4. Compliance statement

- No hand labels and no manual annotation of the provided match; no comparison of any output against the video.
- No training, fitting, calibration or model selection on the ground truth (including the public 5-minute window) or on the provided video. The public window was used only to read the metric definitions; no parameter, feature or version depends on it (decision of 10 Nov).
- Every parameter comes from an organiser document, the Laws of the Game, the literature, or the external IDSSE dataset (CC BY 4.0, cited above).
- The only BAR-ATH-derived inputs to the process are aggregate statistics of the input tracking (section 2), computed by a human and never shown to an AI service.
- No provided data, extract or label set was uploaded to any AI service. AI coding assistants worked only from code, documentation, IDSSE output and synthetic data; they never ran anything on the provided match. The repository contains no match data.
- Version-by-version compliance checks are in the decisions log.

## 5. Limitations

- The ball is missing on 41 % of graded frames, so a possession change inside a gap is detected late (at reappearance).
- No ball height: an aerial ball passing over a player cannot be told apart from a touch except by the velocity change.
- No whistle detection; foul and offside stoppages are detected only when the tracking shows them, so `D` starts late.
- Smart Tagging is automatic, with false positives and negatives and about one second of timing error.
- IDSSE is a different league and tracking system; the degradation reproduces gaps, duplicates and jitter but not every property of the BAR-ATH tracking.
- Under degradation the control rule covers few frames, so the pipeline tends to under-segment (about 100-120 possessions per match against about 450 in the IDSSE reference for v2/v3). **[TO CONFIRM: figure for v4.]**
- Thresholds were set on IDSSE; the result is not tuned to BAR-ATH on purpose, so some loss against a model fitted to it is expected.

## 6. Reproduction

Environment: Python 3.11 or 3.12; `pip install -r requirements.txt` pins numpy and pandas (`numpy==1.24.4`/`pandas==2.0.3` below Python 3.12, `numpy==2.2.6`/`pandas==2.2.3` from 3.12). Only the IDSSE tools need `requirements-starter.txt` (`kloppy==3.18.0`).

Data: put the four tactical assets in `data/tactical/` or set `MTAH_DATA_DIR`.

```bash
git clone https://github.com/isaacboque/cota-cero-mtah2027 && cd cota-cero-mtah2027
pip install -r requirements.txt
python pipeline/make_submission.py --version <vN>     # writes submissions/cota-cero_<vN>.csv, prints sha256
python evaluation/validate_submission.py submissions/cota-cero_<vN>.csv
```

The output is deterministic (fixed seeds, LF line endings, no wall-clock input). Expected sha256 of the submitted file: **[TO CONFIRM, see `SUBMISSIONS.md`]**. Tests use synthetic data only: `python -m pytest -q`. The IDSSE experiments are `python external/control_experiments.py base|noise|touch|dead|deadstart|signal` and `python pipeline/tune_decoder.py` (they read IDSSE from `data/external/idsse/` and never touch the BAR-ATH data).
