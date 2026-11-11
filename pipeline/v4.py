"""v4: possession from written football rules (team document "Reglas de posesion", draft v0.2).

What changes against v2/v3, rule by rule (section numbers are the team document's):

- Contacts, not just control runs (§3). A contact is either a CONTROL run (nearest player within
  R_CTRL_M, ball moving with him, at least T_CTRL_FRAMES) or a TOUCH (nearest player within R_CTRL_M
  while the ball's velocity changes by more than DV_TOUCH_MS). A ball that passes a player at
  constant velocity is neither: that is how an aerial ball over a player (no height in the
  tracking), or a rival standing next to the ball without touching it, is kept out (§5).
- Possession changes only on a CONFIRMED sequence of the other team (§2, §4, §5). A sequence is the
  run of consecutive contacts of one team, each within SEQ_GAP_S of the previous one. It confirms
  when it holds a control run or two contacts (a first-touch pass that reaches a teammate). A lone
  touch, a deflection, a rebound that goes back to the team in possession, or a long 50-50 where the
  teams alternate never confirms, so the last team keeps the ball.
- Confirm, then backdate (§8). The change is written from the FIRST contact of the confirming
  sequence, not from the frame where it became certain.
- Ball not visible = possession unchanged, never D (§2, §5). Where a change is hidden in a gap,
  GAP_PLACEMENT puts it when the ball reappears or in the middle of the gap (open question §10.4).
- Dead ball (§6): the v2 detector (ball out of play, everybody stopped, long gap ending with a static
  ball), plus a ball placed static for a restart when Smart Tagging has a set piece nearby (free
  kicks), plus goal -> kick-off. Each of the two new cues alone stays below DEAD_THRESHOLD, so a
  goalkeeper holding the ball is not D (§6) and a tag on its own is evidence, not truth.
- Restart (§7): a dead run lasts until the ball is put in play (it stops being static,
  BALL_STATIC_MS; a ball conducted at walking pace is already in play).
  The restarting team gets the ball at once: the team Smart Tagging names, else the taker seen in
  the tracking (throw-ins are tagged N/A), else the first team to confirm control.
- Never X. D outside the halves and before the 2nd-half kick-off. Per half, never across halftime.

Pure numpy, deterministic. Every constant is in pipeline/config.py with its source; the TUNE ones
are tuned on IDSSE only (pipeline/tune_decoder.py), never on BAR-ATH ground truth or video.
Codes: 0 H, 1 A, 2 D.
"""
import numpy as np

from pipeline import config
from pipeline.control import control_team
from pipeline.deadball import _runs, deadball_score, hard_dead, min_run
from pipeline.features import compute_features

H, A, D = 0, 1, 2


def _cfg(params):
    c = {k: getattr(config, k) for k in dir(config) if k.isupper()}
    c.update(params or {})
    return c


def _frames(seconds, fps):
    return int(round(seconds * fps))


# -- per-frame signals --------------------------------------------------------------------------

def nearest_player(d):
    """(distance in m, team 0/1) of the player nearest the ball per row; (inf, -1) if none."""
    ball = np.asarray(d["ball_xy"], dtype=float)
    pl = np.asarray(d["players_xy"], dtype=float)
    team = np.asarray(d["slot_team"])
    n = len(ball)
    if pl.shape[1] == 0:
        return np.full(n, np.inf), np.full(n, -1, dtype=np.int8)
    dist = np.linalg.norm(pl - ball[:, None, :], axis=-1)
    dist = np.where(np.isfinite(dist), dist, np.inf)
    j = np.argmin(dist, axis=1)
    dmin = dist[np.arange(n), j]
    near = np.where(np.isfinite(dmin), team[j], -1).astype(np.int8)
    return dmin, near


def ball_kinematics(ball_xy, lag, fps):
    """(velocity change, speed) per row, NaN where the ball is missing nearby.

    Velocity change = |v_after - v_before|, each measured over `lag` frames: large on a kick, a
    reception, a deflection; near zero while the ball rolls or flies past a player untouched.
    Speed is centred over 2*lag frames.
    """
    ball = np.asarray(ball_xy, dtype=float)
    n = len(ball)
    v_before = np.full((n, 2), np.nan)
    v_after = np.full((n, 2), np.nan)
    speed = np.full(n, np.nan)
    if n > lag:
        step = (ball[lag:] - ball[:-lag]) * fps / lag
        v_before[lag:] = step
        v_after[:-lag] = step
    if n > 2 * lag:
        speed[lag:n - lag] = np.linalg.norm(ball[2 * lag:] - ball[:-2 * lag], axis=1) * fps / (2 * lag)
    return np.linalg.norm(v_after - v_before, axis=1), speed


def _team_runs(codes):
    """[(start, stop, team)] runs of equal non-negative codes."""
    codes = np.asarray(codes)
    out = []
    if len(codes) == 0:
        return out
    cut = np.flatnonzero(codes[1:] != codes[:-1]) + 1
    bounds = np.concatenate(([0], cut, [len(codes)]))
    for a, b in zip(bounds[:-1], bounds[1:]):
        if codes[a] >= 0:
            out.append((int(a), int(b), int(codes[a])))
    return out


def contacts(d, dead, c):
    """Sorted [(start, stop, team, is_control)] contacts outside dead frames (§3)."""
    fps = c["FPS"]
    seen = np.asarray(d["ball_seen"], dtype=bool)
    dmin, near = nearest_player(d)
    dv, _ = ball_kinematics(d["ball_xy"], c["VEL_LAG_FRAMES"], fps)
    with np.errstate(invalid="ignore"):
        touch = seen & (dmin <= c["R_CTRL_M"]) & (dv > c["DV_TOUCH_MS"])
    items = [(a, b, t, False) for a, b, t in _team_runs(np.where(touch, near, -1))]
    _, runs = control_team(d, r=c["R_CTRL_M"], v_max=c["V_CTRL_MS"], t_min=c["T_CTRL_FRAMES"],
                           fps=fps, lag=c["VEL_LAG_FRAMES"])
    items += [(a, b, t, True) for a, b, t in runs]

    merged = []
    for a, b, t, ctl in sorted(items):
        if merged and merged[-1][2] == t and a - merged[-1][1] <= c["TOUCH_MERGE_FRAMES"]:
            pa, pb, _, pc = merged[-1]
            merged[-1] = (pa, max(pb, b), t, pc or ctl)
        else:
            merged.append((a, b, t, ctl))
    return [m for m in merged if not dead[m[0]]]


def sequences(cs, gap_frames):
    """Group consecutive same-team contacts into sequences; mark the confirming ones (§3, §5)."""
    seqs = []
    for a, b, t, ctl in cs:
        last = seqs[-1] if seqs else None
        if last is not None and last["team"] == t and a - last["end"] <= gap_frames:
            last["end"] = max(last["end"], b)
            last["n"] += 1
            last["control"] = last["control"] or ctl
        else:
            seqs.append({"start": a, "end": b, "team": t, "n": 1, "control": ctl})
    for q in seqs:
        q["confirmed"] = q["control"] or q["n"] >= 2
    return seqs


# -- dead ball ------------------------------------------------------------------------------------

def _window_mask(n, frames, w):
    out = np.zeros(n, dtype=bool)
    for f in frames:
        lo, hi = max(0, f - w), min(n, f + w + 1)
        if lo < hi:
            out[lo:hi] = True
    return out


def dead_mask(d, cues, c, kickoff_2nd):
    """Dead-ball decision per row (§6), with every dead run extended until the ball is put in
    play (§7)."""
    n = len(d["ball_seen"])
    fps = c["FPS"]
    seen = np.asarray(d["ball_seen"], dtype=bool)
    feats = compute_features(d)
    _, speed = ball_kinematics(d["ball_xy"], c["VEL_LAG_FRAMES"], fps)
    w = _frames(c["CUE_WINDOW_S"], fps)
    set_pieces = [f for f, _, kind in cues if kind != "goal"]

    score = deadball_score(d, feats, kickoff_2nd)
    with np.errstate(invalid="ignore"):
        static = seen & (speed < c["BALL_STATIC_MS"])
    score = score + c["W_STATIC"] * min_run(static, _frames(c["STATIC_MIN_S"], fps))
    score = score + c["W_CUE"] * _window_mask(n, set_pieces, w)
    hard = hard_dead(n, d["halves"], kickoff_2nd)
    dead = (score >= c["DEAD_THRESHOLD"]) | hard

    # Goal -> dead from the first dead frame after the goal cue until the next kick-off cue.
    kickoffs = sorted(f for f, _, kind in cues if kind == "kick_off")
    for g in sorted(f for f, _, kind in cues if kind == "goal"):
        nxt = [k for k in kickoffs if g < k <= g + _frames(c["GOAL_MAX_S"], fps)]
        if not nxt:
            continue
        lo, hi = max(0, g - w), min(n, nxt[0])
        hit = np.flatnonzero(dead[lo:hi])
        if len(hit):
            dead[lo + hit[0]:hi] = True

    # Extend each dead run while the ball has not been put in play: still static, or missing and
    # reappearing static. A ball moving at walking pace is in play (a player conducting it), so
    # the test is BALL_STATIC_MS. Capped, and never past the end of its half.
    cap = _frames(c["RESTART_MAX_EXT_S"], fps)
    lag = c["VEL_LAG_FRAMES"]
    # restart = ball struck (RESTART_KICK_MS); None keeps the old test "ball no longer static"
    kick = c.get("RESTART_KICK_MS") or c["BALL_STATIC_MS"]

    def first_speed(j, limit):
        # speed right after the ball reappears is NaN for `lag` rows; take the first finite one
        for k in range(j, min(limit, j + 2 * lag + 1)):
            if seen[k] and np.isfinite(speed[k]):
                return speed[k]
        return np.nan

    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        a, b = int(a), int(b) + 1
        for _, stop in _runs(dead[a:b]):
            i = a + stop
            limit = min(b, i + cap)
            while i < limit:
                if seen[i]:
                    if np.isfinite(speed[i]) and speed[i] >= kick:
                        break
                    i += 1
                    continue
                j = i
                while j < limit and not seen[j]:
                    j += 1
                v = first_speed(j, limit) if j < limit else np.nan
                if not (np.isfinite(v) and v < kick):
                    break
                i = j
            dead[a + stop:i] = True
    return dead


# -- restart and labelling ------------------------------------------------------------------------

def restart_team(s, e, cues, dmin, near, seen, c):
    """Team that restarts play at row s (§7): Smart Tagging team, else the taker, else None."""
    fps = c["FPS"]
    w = _frames(c["CUE_WINDOW_S"], fps)
    named = [(abs(f - s), t) for f, t, kind in cues if t is not None and kind != "goal"
             and abs(f - s) <= w]
    if named:
        return min(named)[1]
    lo = max(0, s - c["VEL_LAG_FRAMES"])
    hi = min(e, s + _frames(c["TAKER_WINDOW_S"], fps))
    for i in range(lo, hi):
        if seen[i] and dmin[i] <= c["R_TAKER_M"] and near[i] >= 0:
            return int(near[i])
    return None


def _place_change(prev_end, start, seen, c):
    """Frame where a change to a newly confirmed team is written (§8, §10.4)."""
    if c["GAP_PLACEMENT"] != "midpoint" or start <= prev_end:
        return start
    gaps = [(b - a, a, b) for a, b in _runs(~seen[prev_end:start])]
    gaps = [g for g in gaps if g[0] >= _frames(c["GAP_MIN_S"], c["FPS"])]
    if not gaps:
        return start
    _, a, b = max(gaps)
    return prev_end + (a + b) // 2


def label_segment(s, e, initial, seqs, seen, carry, c):
    """Labels for one live stretch [s, e). `initial` = restarting team or None; `carry` = team
    before the stoppage, used only if nobody ever confirms control."""
    out = np.full(e - s, D, dtype=np.int8)
    changes = []
    cur = initial
    prev_end = s
    for q in seqs:
        if q["confirmed"] and q["team"] != cur:
            f = s if cur is None else max(s, _place_change(prev_end, q["start"], seen, c))
            changes.append((f, q["team"]))
            cur = q["team"]
        prev_end = max(prev_end, q["end"])
    first = initial if initial is not None else (carry if not changes else None)
    pos, team = s, first
    for f, t in changes:
        if team is not None:
            out[pos - s:f - s] = team
        pos, team = f, t
    if team is not None:
        out[pos - s:] = team

    # H/A runs shorter than MIN_RUN_FRAMES join the previous team (no flicker, §8).
    k = c["MIN_RUN_FRAMES"]
    if k > 1:
        runs = _team_runs(out)
        for idx in range(1, len(runs)):
            a, b, _ = runs[idx]
            if b - a < k and runs[idx - 1][2] in (H, A):
                out[a:b] = out[a - 1]
    return out


def predict_v4(d, kickoff_2nd=config.KICKOFF_2ND, restarts=None, params=None):
    """Labels per row (0 H, 1 A, 2 D). `restarts` = pipeline.restarts.restart_events output
    (evidence only; None or [] for sources without Smart Tagging, e.g. IDSSE)."""
    c = _cfg(params)
    cues = list(restarts or [])
    n = len(d["ball_seen"])
    seen = np.asarray(d["ball_seen"], dtype=bool)
    dead = dead_mask(d, cues, c, kickoff_2nd)
    dmin, near = nearest_player(d)
    seqs_all = sequences(contacts(d, dead, c), _frames(c["SEQ_GAP_S"], c["FPS"]))

    out = np.full(n, D, dtype=np.int8)
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        a, b = int(a), int(b) + 1
        carry = None
        for start, stop in _runs(~dead[a:b]):
            s, e = a + start, a + stop
            seqs = [q for q in seqs_all if s <= q["start"] < e]
            initial = restart_team(s, e, cues, dmin, near, seen, c)
            seg = label_segment(s, e, initial, seqs, seen, carry, c)
            out[s:e] = seg
            alive = seg[seg != D]
            if len(alive):
                carry = int(alive[-1])
    return out
