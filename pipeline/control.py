"""Control events (08-model-plan.md section 2.4).

A team gains control when its player is the nearest to the ball (so no opponent is closer), within
R_CTRL_M, with the ball's speed relative to that player under V_CTRL_MS, for at least T_CTRL_FRAMES
consecutive frames. Ball-missing frames never count. Constants in pipeline/config.py.
"""
import numpy as np

from pipeline import config


def _velocity(xy, fps):
    v = np.full(xy.shape, np.nan)
    v[1:] = (xy[1:] - xy[:-1]) * fps
    return v


def control_team(d, r=config.R_CTRL_M, v_max=config.V_CTRL_MS, t_min=config.T_CTRL_FRAMES,
                 fps=config.FPS):
    """Per row: team (0/1) in control during a qualifying run, else -1. Also returns the
    per-row nearest distance. Returns (team array int8, run list [(start, stop, team)])."""
    ball = np.asarray(d["ball_xy"], dtype=float)
    pl = np.asarray(d["players_xy"], dtype=float)
    team = np.asarray(d["slot_team"])
    n = len(ball)
    dist = np.linalg.norm(pl - ball[:, None, :], axis=-1)
    dist = np.where(np.isfinite(dist), dist, np.inf)
    j = np.argmin(dist, axis=1)
    rows = np.arange(n)
    dmin = dist[rows, j]
    rel = np.linalg.norm(_velocity(ball, fps) - _velocity(pl, fps)[rows, j], axis=-1)
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(dmin) & (dmin <= r) & (rel < v_max)
    cand = np.where(ok, team[j], -1).astype(np.int8)

    out = np.full(n, -1, dtype=np.int8)
    runs = []
    i = 0
    while i < n:
        if cand[i] < 0:
            i += 1
            continue
        k = i
        while k < n and cand[k] == cand[i]:
            k += 1
        if k - i >= t_min:
            out[i:k] = cand[i]
            runs.append((i, k, int(cand[i])))
        i = k
    return out, runs


def control_events(d, **kw):
    """Sparse events (frame, team, confidence): the first frame of each qualifying control run;
    confidence = run length over 4*T_CTRL_FRAMES, capped at 1."""
    _, runs = control_team(d, **kw)
    t_min = kw.get("t_min", config.T_CTRL_FRAMES)
    return [(a, t, min(1.0, (b - a) / (4.0 * t_min))) for a, b, t in runs]
