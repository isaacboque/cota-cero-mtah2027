"""Rule-based dead-ball score (08-model-plan.md section 2.3, rules 1-3 plus the hard D rules).

score in [0, 1] per row; `dead_mask` thresholds it. Smart Tagging cues (rules 4-5) are not wired
here (T7). Constants live in pipeline/config.py.
"""
import numpy as np

from pipeline import config
from pipeline.features import compute_features


def _runs(mask):
    """(start, stop) half-open runs of True."""
    edges = np.diff(np.concatenate(([0], np.asarray(mask, dtype=np.int8), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist()))


def min_run(mask, k):
    """Keep only the True runs of length >= k."""
    out = np.zeros(len(mask), dtype=bool)
    for a, b in _runs(mask):
        if b - a >= k:
            out[a:b] = True
    return out


def hysteresis(raw, n_on, n_off):
    """On after n_on consecutive True; off after n_off consecutive False. The on-run is marked
    from its first True frame (look-back), the off-run stays on until its last False is counted."""
    raw = np.asarray(raw, dtype=bool)
    out = np.zeros(len(raw), dtype=bool)
    on, run_t, run_f = False, 0, 0
    for i, v in enumerate(raw):
        if v:
            run_t += 1
            run_f = 0
            if not on and run_t >= n_on:
                on = True
                out[i - run_t + 1:i + 1] = True
        else:
            run_f += 1
            run_t = 0
            if on and run_f >= n_off:
                on = False
                out[i - run_f + 1:i + 1] = False  # the sustained in-bounds run is not dead
        if on:
            out[i] = True
    return out


def hard_dead(n, halves, kickoff_2nd=config.KICKOFF_2ND):
    """True outside the halves, and in the last half from its first row up to `kickoff_2nd`
    (None disables the second rule, e.g. for IDSSE where rows are not video frames)."""
    hard = np.ones(n, dtype=bool)
    hs = np.asarray(halves).reshape(-1, 3)
    for _, a, b in hs:
        hard[a:b + 1] = False
    if kickoff_2nd is not None and len(hs) >= 2:
        a, b = int(hs[-1][1]), int(hs[-1][2])
        if a < kickoff_2nd <= b:
            hard[a:kickoff_2nd] = True
    return hard


def deadball_score(d, feats=None, kickoff_2nd=config.KICKOFF_2ND):
    f = feats if feats is not None else compute_features(d)
    n = len(d["ball_seen"])
    fps = config.FPS
    seen = np.asarray(d["ball_seen"], dtype=bool)
    score = np.zeros(n)

    # 1. out of bounds with hysteresis
    oob = hysteresis(f["oob"], config.OOB_ENTER_FRAMES, config.OOB_EXIT_FRAMES)
    score += config.W_OOB * oob

    # 2. global slowdown: both teams slow, ball static or missing, for >= SLOW_MIN_S
    with np.errstate(invalid="ignore"):
        slow = (f["mean_speed_home"] < config.SLOW_TEAM_SPEED_MS) & \
               (f["mean_speed_away"] < config.SLOW_TEAM_SPEED_MS)
        static = ~seen | (f["ball_speed"] < config.BALL_STATIC_MS)
    score += config.W_SLOW * min_run(slow & static, int(config.SLOW_MIN_S * fps))

    # 3. long missing run that ends with the ball reappearing static
    ms = np.zeros(n, dtype=bool)
    w = config.STATIC_WINDOW_FRAMES
    ball = np.asarray(d["ball_xy"], dtype=float)
    for a, b in _runs(~seen):
        if b - a < int(config.MISSING_RUN_MIN_S * fps) or b + w >= n:
            continue
        if seen[b] and seen[b + w]:
            v = np.linalg.norm(ball[b + w] - ball[b]) * fps / w
            if v < config.BALL_STATIC_MS:
                ms[a:b] = True
    score += config.W_MISSING_STATIC * ms

    score = np.minimum(score, 1.0)
    score[hard_dead(n, d["halves"], kickoff_2nd)] = 1.0
    return score


def dead_mask(d, feats=None, kickoff_2nd=config.KICKOFF_2ND):
    return deadball_score(d, feats, kickoff_2nd) >= config.DEAD_THRESHOLD
