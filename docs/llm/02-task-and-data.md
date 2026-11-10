# Task and data

Short orientation. Authoritative definitions are in the organisers' `CHALLENGE.md`, `DATA.md`, `EVALUATION.md` (linked from `README.md`); this file only points the way.

## Task
For every frame of one LaLiga match (**BAR-ATH**, tactical recording) output one label per frame. Source: upstream `CHALLENGE.md` (read 10 Nov 2026).

| Label | Meaning |
|---|---|
| `H` | Home team in possession, ball alive |
| `A` | Away team in possession, ball alive |
| `D` | Dead ball (ball not in play). Always `D` when dead, even if tracking names a team; dead-ball ownership is not scored |
| `X` | No answer: abstain, or the frame has no ground truth |

- The video has 199 319 frames at 25 fps (about 2 h 15 min). Only **158 857 frames (~106 min of play)** are graded; kickoff lead-in, halftime and post-whistle frames are never scored (an `X` there costs nothing).

| | first video frame | last | graded |
|---|---|---|---|
| before the match | 0 | 11 184 | no |
| 1st half | **11 185** (= kickoff) | **90 651** | yes |
| halftime | 90 652 | 110 807 | no |
| 2nd half | **110 808** | **190 197** | yes |
| after the whistle | 190 198 | 199 318 | no |

**Trap (FAQ):** the 2nd half is graded from 110 808 but kicks off at **113 742**: those 2 934 graded frames are all `D`. `games.half_video_blocks("BAR-ATH")` returns the halves.
- Home = **FC Barcelona** (`H`), away = **Athletic Club** (`A`); LaLiga 2024-25, matchday 2.
- Inputs are automatic and uncorrected: **the ball is missing on 41 % of graded frames.**
- Ground truth has only three states (`H`, `A`, `D`); no "contested", "transition" or "unknown". It comes from *corrected tracking data*, not human annotation or event data, with no smoothing or interpolation.
- A possession is a continuous run of one team with the ball alive: `H H H A A` = two possessions; `H H D D H H` = two possessions separated by a stoppage. Dead ball is a stoppage, never a possession.

Possession rules (organisers):
- Ball in play is decided by the referee. While it is in play exactly one team has possession; in loose-ball situations the team that last had possession keeps it.
- After any restart (kickoff, throw-in, corner, goal kick, free kick) one team clearly has possession. The hard part is detecting *changes* of possession.
- A change happens when a player of the other team has the ball **under control**. "Control" is left open: define and justify our own criterion in the technical document.
- Not a change: a single touch without control; a deflected pass that is not intercepted; an aerial duel won without controlling the ball.
- The public 5-minute ground truth (17 possessions) is "the authority" if our reading disagrees with it; report the disagreement rather than tuning to it.

Output: CSV `frame,label`, UTF-8, header `frame,label`, row *i* = frame *i* (0…199318) of `BAR-ATH_tactical.mp4`, **199 319 rows**, no blank cells, LF line endings (ours), validated by `evaluation/validate_submission.py`. 25 fps (±50 frames = ±2 s).

## Competition context
Organisers: Mobile World Capital Barcelona, Barça Innovation Hub, Metrica Sports. Teams of 3–5. Initial Challenge ranking is automatic and objective. Only the top 20 go on to the Innovation Challenge, only the top 5 to the final. Schedule and Round 2 outline: [07-roadmap.md](07-roadmap.md).

## Metrics
Ranking is by **spellF1**; first tie-break is **macroF1**. They can rank the same files differently: smoothing windows that barely move macroF1 change spellF1 a lot. Details: upstream `EVALUATION.md`.

How `X` is scored:
- macroF1 counts `X` as a miss, like a wrong answer.
- spellF1 fills each `X` with the last label given in that half *before* matching possessions. An `X` in the middle of a possession costs little; an `X` across a real change of possession can cost a lot (the old label carries into the new state). Abstain only where we are confident no change happens.
- Frames whose ground truth is `X` are not scored.

## Assets (gated, never committed, never sent to AI)
Live in `data/tactical/` or `$MTAH_DATA_DIR`:
- `BAR-ATH_tactical.mp4` (~5.2 GB) — reference timeline (video)
- `BAR-ATH_tactical_atd.txt` (~195 MB) / `_atd.xml` — automatic tracking data, players + ball, and its metadata
- `BAR-ATH_tactical_homography.csv` (~23 MB) — one 3×3 matrix per frame
- `BAR-ATH_tactical_smart_tagging.xml` — 638 tactical phases and set pieces
- `data/broadcast/*` (video ~14 GB, atd.txt ~142 MB, homography ~15 MB) — optional, **not** synchronised to the tactical timeline

Ball present on 56.9 % of all frames, 59.3 % of graded ones; ATD raw line `frame:p1;…;p46:ball`, each group `x,y,speed`, normalised 0–1 (pitch 105.3 × 68.0 m in `games.py`), `NaN` when missing. Index alignment: ATD `frame_id` 1…199 319 → row `frame_id - 1`; Smart Tagging seconds → `round(s*25)`; homography `frame` is already the row. While the ball is dead the corrected tracking still names a team (who restarts or touched last); the ground truth discards it and writes `D`. Smart Tagging set-piece types: Throw-in 26, Corner Kick 12, Goal Kick 10, Free Kick 5, Kick Off (After Goal) 4, Kick Off (Start) 2 (match case-insensitively).

Provenance: tracking and Smart Tagging come from Metrica Sports; video from Barça Innovation Hub. The organisers say no detection, identification or camera calibration needs to be built — tracking and homography are given.

All paths are derived in `games.py` (`asset_paths(source="tactical"|"broadcast")`). Never hard-code a path elsewhere.

## Ground truth
- Full-match GT is held by the organisers. A 5-minute **public** window is in `evaluation/gt/` for scorer sanity only. Both are off-limits for training, fitting, calibration and model selection (see `01-rules.md`).

## Current baseline
v1 = nearest tracked player to the ball + majority vote ±50 frames (organisers' published best on the full match, spellF1 ≈ 0.2433). Byte-identical to `baseline_smooth50`. Improvements must come from inputs we are allowed to use and parameters justified by external data or organiser documentation.
