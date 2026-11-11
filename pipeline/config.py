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
OOB_MARGIN_M = 0.25       # RULE: ball out when wholly over the line (radius ~0.11 m); margin absorbs tracking noise. IDSSE CV ctrl_deadstart_flat (ticket #23): 0 and 0.25 within 0.01; 0.25 kept for unmeasured BAR-ATH noise (#25)
OOB_ENTER_FRAMES = 5      # TUNE: consecutive out-of-bounds frames before the hysteresis turns on
OOB_EXIT_FRAMES = 10      # TUNE: consecutive in-bounds frames before it turns off
SLOW_TEAM_SPEED_MS = 2.5  # both teams' MEDIAN player speed under this = global slowdown. IDSSE CV ctrl_deadstart_flat (ticket #23): flat 2.0-3.0, middle taken
SLOW_MIN_S = 4.0          # TUNE: slowdown must last at least this long
BALL_STATIC_MS = 1.0      # TUNE: ball slower than this counts as static
MISSING_RUN_MIN_S = 3.0   # TUNE: ball-missing run at least this long can be a stoppage
STATIC_WINDOW_FRAMES = 12 # TUNE: frames after the ball reappears used to test "static"
W_OOB = 1.0               # TUNE: score weight of rule 1 (strongest evidence)
W_SLOW = 0.6              # TUNE: score weight of rule 2
W_MISSING_STATIC = 0.6    # TUNE: score weight of rule 3
DEAD_THRESHOLD = 0.5      # TUNE: score at or above this = dead
KICKOFF_2ND = 113742      # ORGANISER: FAQ, 2nd-half kick-off video frame (graded D from 110808 until then)

# v4 (pipeline/v4.py). DOC = team document "Reglas de posesion" draft v0.2, section given.
# Also uses R_CTRL_M, V_CTRL_MS, T_CTRL_FRAMES (control), the dead-ball constants above and DEAD_THRESHOLD.
# NO-IDSSE = IDSSE has no Smart Tagging, so the leave-one-match-out grid cannot tune it; it keeps
# the value justified here and is reported as such in the technical document.
VEL_LAG_FRAMES = 3        # TUNE: frames each side used to measure ball velocity before/after a row (0.12 s)
DV_TOUCH_MS = 4.0         # TUNE: ball velocity change that is a touch when a player is within R_CTRL_M (DOC 3 "el balon va con el"); above position-noise level
TOUCH_MERGE_FRAMES = 2    # TUNE: same-team contacts this close are one contact
SEQ_GAP_S = 3.0           # TUNE: same-team contacts this close form one sequence: a pass that reaches a teammate (DOC 3 "pase al primer toque")
GAP_PLACEMENT = "reappear"  # TUNE: change hidden in a ball-missing gap goes "reappear" (DOC 8, simplest) or "midpoint" (DOC 10.4)
GAP_MIN_S = 0.4           # TUNE: missing run shorter than this is not treated as a hiding gap ("midpoint" only)
STATIC_MIN_S = 1.5        # TUNE: ball seen and static this long = placed for a restart (DOC 6, "balon quieto en un sitio tipico")
W_STATIC = 0.3            # DOC 6: below DEAD_THRESHOLD alone on purpose, a goalkeeper holding the ball is in play
W_CUE = 0.3               # DOC 6 + NO-IDSSE: Smart Tagging set piece nearby; below DEAD_THRESHOLD alone (evidence, not truth)
CUE_WINDOW_S = 5.0        # ORGANISER (starter/01_smart_tagging.ipynb: tags are ~5 s windows that open ~3.5 s before the restart) + NO-IDSSE
RESTART_MAX_EXT_S = 5.0   # TUNE: longest a dead run is extended while the ball stays static (BALL_STATIC_MS) waiting for the restart (DOC 7)
RESTART_KICK_MS = None    # TUNE (ticket #23): a dead run ends when the ball moves faster than this (struck); None = BALL_STATIC_MS (old rule)
R_TAKER_M = 3.0           # TUNE: restarting team = nearest player within this at the restart (DOC 7, throw-ins are tagged N/A)
TAKER_WINDOW_S = 1.0      # TUNE: how long after the restart the taker is searched for
GOAL_MAX_S = 180.0        # RULE + NO-IDSSE: a kick-off cue later than this after a goal cue is not its restart
MIN_RUN_FRAMES = 5        # TUNE: H/A runs shorter than this inside a live stretch join the previous team (0.2 s)
