"""Every tunable constant of the pipeline, each with the source of its value.

Sources: ORGANISER = organiser document; RULE = Laws of the Game; TUNE = placeholder, to be tuned
on IDSSE leave-one-match-out CV (never on BAR-ATH GT/video). Each is logged in
docs/llm/05-decisions-log.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import games  # noqa: E402

FPS = 25                                   # ORGANISER: games.py (tactical source)
PITCH = games.GAMES[games.GAME]["pitch"]   # ORGANISER: games.py, 105.3 x 68.0 m

# Features (pipeline/features.py)
R_PRESSURE_M = 5.0        # TUNE: radius for "players near the ball" counts
TURN_MIN_SPEED_MS = 2.0   # TUNE: below this ball speed the direction change is noise, set to 0

# Control events (pipeline/control.py, 08-model-plan.md section 2.4: our written definition of control)
R_CTRL_M = 2.0            # TUNE: nearest player must be within this distance of the ball
V_CTRL_MS = 3.0           # TUNE: ball speed relative to that player under this
T_CTRL_FRAMES = 5         # TUNE: ... for at least this many consecutive frames (0.2 s); 1-frame touches never count

# Decoder v3 (pipeline/decode.py). MIN_DWELL_HA_S, LOG_SWITCH_FAR and LOG_TO_D: SOURCE = CV run
# idsse-cv-20261111-degraded-seed0 (pipeline/tune_decoder.py, degraded IDSSE, leave-one-match-out;
# docs/llm/05-decisions-log.md, 2026-11-11). The grid is flat (all 27 settings within 0.002 mean spellF1),
# so the centre of the grid was kept, not the maximum. The other constants below are untuned placeholders.
MIN_DWELL_HA_S = 1.0      # TUNE: minimum H/A run (organisers: ~0.5 s boundary precision, flicker kills spellF1)
MIN_DWELL_D_S = 1.0       # TUNE: minimum D run
LOG_SWITCH_NEAR = -1.0    # TUNE: log cost of H<->A with a control event of the new team nearby
LOG_SWITCH_FAR = -8.0     # TUNE: ... without one
LOG_TO_D = -3.0           # TUNE: log cost of alive -> D (the dead-ball score drives it through emissions)
LOG_EXIT_CUE = -0.5       # TUNE: D -> team that the Smart Tagging restart cue names (or any team if cue has none)
LOG_EXIT_FAR = -4.0       # TUNE: D -> team with no cue nearby (nearby control event uses LOG_SWITCH_NEAR)
NEAR_EVENT_S = 1.0        # TUNE: "nearby" window, seconds either side
P_CTRL = 0.85             # TUNE: emission probability that the team in control is the possessor
DEAD_P_CLIP = 0.02        # TUNE: clip of the dead-ball score before taking logs
LOG_HARD = -50.0          # structural: alive emission on hard-D frames (outside halves / pre-kick-off)

# Dead-ball detector (pipeline/deadball.py)
OOB_MARGIN_M = 0.5        # RULE: ball is out when wholly over the line (ball radius ~0.11 m); margin absorbs tracking noise -> TUNE
OOB_ENTER_FRAMES = 5      # TUNE: consecutive out-of-bounds frames before the hysteresis turns on
OOB_EXIT_FRAMES = 10      # TUNE: consecutive in-bounds frames before it turns off
SLOW_TEAM_SPEED_MS = 1.0  # TUNE: both teams' mean player speed under this = global slowdown
SLOW_MIN_S = 4.0          # TUNE: slowdown must last at least this long
BALL_STATIC_MS = 1.0      # TUNE: ball slower than this counts as static
MISSING_RUN_MIN_S = 3.0   # TUNE: ball-missing run at least this long can be a stoppage
STATIC_WINDOW_FRAMES = 12 # TUNE: frames after the ball reappears used to test "static"
W_OOB = 1.0               # TUNE: score weight of rule 1 (strongest evidence)
W_SLOW = 0.6              # TUNE: score weight of rule 2
W_MISSING_STATIC = 0.6    # TUNE: score weight of rule 3
DEAD_THRESHOLD = 0.5      # TUNE: score at or above this = dead
KICKOFF_2ND = 113742      # ORGANISER: FAQ, 2nd-half kick-off video frame (graded D from 110808 until then)
