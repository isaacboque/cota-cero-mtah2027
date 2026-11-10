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
