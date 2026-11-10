"""Per-frame, team-level, identity-free features from the loader dict (BAR-ATH or IDSSE).

Distances in metres, speeds in m/s derived from positions (the file's own speed unit is not
relied on), so both sources behave the same. NaN means "not available this frame".
"""
import numpy as np

from pipeline import config


def _speed(xy, fps):
    """|Δxy|*fps between consecutive rows; NaN unless both rows are finite. Row 0 is NaN."""
    out = np.full(xy.shape[:-1], np.nan)
    step = np.linalg.norm(xy[1:] - xy[:-1], axis=-1) * fps
    out[1:] = step
    return out


def _missing_run(seen):
    """Length of the current ball-missing run at each row (0 where the ball is seen)."""
    idx = np.arange(len(seen))
    last_seen = np.maximum.accumulate(np.where(seen, idx, -1))
    return np.where(seen, 0, idx - last_seen)


def out_of_bounds(ball_xy, margin=config.OOB_MARGIN_M, pitch=config.PITCH):
    x, y = ball_xy[:, 0], ball_xy[:, 1]
    with np.errstate(invalid="ignore"):
        return (x < -margin) | (x > pitch[0] + margin) | (y < -margin) | (y > pitch[1] + margin)


def compute_features(d, r=config.R_PRESSURE_M, fps=config.FPS):
    ball = np.asarray(d["ball_xy"], dtype=float)
    pl = np.asarray(d["players_xy"], dtype=float)
    team = np.asarray(d["slot_team"])
    seen = np.asarray(d["ball_seen"], dtype=bool)

    dist = np.linalg.norm(pl - ball[:, None, :], axis=-1)  # NaN if ball or player missing
    f = {}
    for name, t in (("home", 0), ("away", 1)):
        dt = dist[:, team == t]
        with np.errstate(invalid="ignore"):
            valid = np.isfinite(dt)
            near = np.where(valid, dt, np.inf).min(axis=1) if dt.shape[1] else np.full(len(ball), np.inf)
            f["d_" + name] = np.where(np.isfinite(near), near, np.nan)
            f["n_{}_r".format(name)] = (valid & (dt <= r)).sum(axis=1)

    pspeed = _speed(pl, fps)
    for name, t in (("home", 0), ("away", 1)):
        sub = pspeed[:, team == t]
        with np.errstate(invalid="ignore"):
            cnt = np.isfinite(sub).sum(axis=1)
            tot = np.where(np.isfinite(sub), sub, 0.0).sum(axis=1)
            f["mean_speed_" + name] = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    f["gap"] = f["d_away"] - f["d_home"]

    bspeed = _speed(ball, fps)
    f["ball_speed"] = bspeed
    acc = np.full(len(ball), np.nan)
    acc[1:] = (bspeed[1:] - bspeed[:-1]) * fps
    f["ball_accel"] = acc
    disp = np.full_like(ball, np.nan)
    disp[1:] = ball[1:] - ball[:-1]
    ang = np.arctan2(disp[:, 1], disp[:, 0])
    turn = np.full(len(ball), np.nan)
    dang = np.abs((ang[1:] - ang[:-1] + np.pi) % (2 * np.pi) - np.pi)
    turn[1:] = dang
    with np.errstate(invalid="ignore"):
        slow = ~(bspeed >= config.TURN_MIN_SPEED_MS)
    turn[slow & np.isfinite(turn)] = 0.0  # direction of a near-static ball is noise
    f["ball_turn"] = turn
    f["oob"] = out_of_bounds(ball) & seen
    f["missing_run"] = _missing_run(seen)
    return f
