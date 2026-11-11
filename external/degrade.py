"""Degrade clean external tracking (IDSSE) so it looks like the BAR-ATH input.

Operates on the array dict of pipeline.data / external.idsse. Never touches `gt_codes`, `halves`,
`slot_team` or `fps`. Fully deterministic for a given (params, seed).

Steps, in order:
  1. ball dropout on ALIVE frames in contiguous gaps, gap lengths drawn from a histogram, until the
     missing share of alive frames reaches `target_missing` (last gap truncated to land on it);
  2. Gaussian position noise (sigma in metres) on every visible ball and player position;
  3. player slots randomly dropped (down to `target_visible_slots` per frame if given, else
     `drop_prob`) and duplicated (a slot takes another same-team slot's position, `dup_prob`).

DEFAULT_PARAMS are placeholders from organiser docs (DATA.md: ball missing on 41 % of graded
frames; ~20.5 visible slots per frame, 46 tracks) and a made-up gap histogram. The real histogram
and slot count come from external/barath_gap_stats.py, run by a human -> data/cache/degrade_params.json.
"""
import numpy as np

# Source of each value: target_missing = DATA.md (41 % of graded frames); target_visible_slots =
# 08-model-plan.md section 1 (~20.5 visible); noise_sigma_m, dup_prob, gap_* = placeholders to be
# replaced by degrade_params.json (aggregate BAR-ATH input stats, computed by a human).
DEFAULT_PARAMS = {
    "target_missing": 0.41,
    "gap_bins": [1, 5, 25, 125, 625, 3125],      # frame-length bin edges [lo, hi)
    "gap_weights": [0.20, 0.25, 0.25, 0.20, 0.10],  # relative frequency of gaps per bin
    "noise_sigma_m": 0.3,
    "noise_corr_frames": 50,  # noise is a moving average over this many frames (2 s); 1 = white noise
    "target_visible_slots": 20.5,
    "drop_prob": 0.0,
    "dup_prob": 0.02,
}
_PASSTHROUGH = ("gt_codes", "halves", "slot_team", "fps")


def load_params(path):
    """Read degrade params from a JSON file (e.g. data/cache/degrade_params.json). Only keys of
    DEFAULT_PARAMS are kept; a missing file gives {}. Values are never printed or logged."""
    import json
    import os
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        raw = json.load(fh)
    return {k: v for k, v in raw.items() if k in DEFAULT_PARAMS}


def _alive(d):
    if "gt_codes" in d:
        g = np.asarray(d["gt_codes"])
        return (g == 0) | (g == 1)
    return np.ones(len(d["ball_seen"]), dtype=bool)


def _noise(shape, sigma, corr, rng):
    """Gaussian noise of std `sigma`, correlated in time (axis 0) by a moving average of `corr`
    frames. Independent per-frame noise gives ~10 m/s velocity jitter at 25 fps, which tracking
    data does not have (and which no velocity-based rule could survive)."""
    corr = max(1, int(corr))
    n = shape[0]
    white = rng.normal(0.0, 1.0, (n + corr - 1,) + tuple(shape[1:]))
    c = np.cumsum(white, axis=0)
    c = np.concatenate([np.zeros((1,) + c.shape[1:]), c], axis=0)
    return sigma * (c[corr:] - c[:-corr]) / np.sqrt(corr)


def _drop_ball(d, out, params, rng):
    alive = _alive(d)
    seen = out["ball_seen"]
    n_alive = int(alive.sum())
    if n_alive == 0:
        return
    target = int(round(params["target_missing"] * n_alive))
    missing = int((alive & ~seen).sum())
    bins = np.asarray(params["gap_bins"], dtype=np.int64)
    w = np.asarray(params["gap_weights"], dtype=float)
    w = w / w.sum()
    n = len(seen)
    alive_idx = np.flatnonzero(alive)
    guard = 0
    while missing < target and guard < 1_000_000:
        guard += 1
        b = rng.choice(len(w), p=w)
        length = int(rng.integers(bins[b], bins[b + 1]))
        start = int(alive_idx[rng.integers(0, len(alive_idx))])
        rows = np.arange(start, min(n, start + length))
        new = alive[rows] & seen[rows]
        csum = np.cumsum(new)
        need = target - missing
        if csum[-1] > need:  # truncate so the share lands on the target
            rows = rows[: int(np.searchsorted(csum, need)) + 1]
            new = alive[rows] & seen[rows]
        missing += int(new.sum())
        seen[rows] = False
        out["ball_xy"][rows] = np.nan
        out["ball_speed"][rows] = np.nan


def degrade(d, params=None, seed=0):
    """Return a degraded copy of `d`; `d` and its `gt_codes` are left unchanged."""
    p = dict(DEFAULT_PARAMS)
    p.update(params or {})
    rng = np.random.default_rng(seed)
    out = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v) for k, v in d.items()}
    out["ball_xy"] = out["ball_xy"].astype(float)
    out["players_xy"] = out["players_xy"].astype(float)
    if "players_speed" not in out:
        out["players_speed"] = np.full(out["players_xy"].shape[:2], np.nan)
    if "ball_speed" not in out:
        out["ball_speed"] = np.full(len(out["ball_seen"]), np.nan)

    _drop_ball(d, out, p, rng)

    sigma = float(p["noise_sigma_m"])
    if sigma > 0:
        corr = p["noise_corr_frames"]
        out["ball_xy"] += _noise(out["ball_xy"].shape, sigma, corr, rng)  # NaN stays NaN
        out["players_xy"] += _noise(out["players_xy"].shape, sigma, corr, rng)

    pl, ps = out["players_xy"], out["players_speed"]
    n, s = pl.shape[:2]
    team = np.asarray(d["slot_team"])
    # duplicates: slot takes a random other same-team slot's position
    dup = rng.random((n, s)) < p["dup_prob"]
    src = np.empty((n, s), dtype=np.int64)
    for t in np.unique(team):
        members = np.flatnonzero(team == t)
        cols = np.flatnonzero(team == t)
        src[:, cols] = members[rng.integers(0, len(members), (n, len(cols)))]
    rows = np.arange(n)[:, None]
    dup_xy = pl[rows, src]
    dup_sp = ps[rows, src]
    pl = np.where(dup[..., None], dup_xy, pl)
    ps = np.where(dup, dup_sp, ps)
    # drops
    drop_prob = float(p["drop_prob"])
    tv = p.get("target_visible_slots")
    if tv is not None:
        visible = float(np.mean(np.isfinite(pl[..., 0]).sum(axis=1)))
        if visible > 0:
            drop_prob = max(drop_prob, 1.0 - float(tv) / visible)
    drop = rng.random((n, s)) < drop_prob
    pl = np.where(drop[..., None], np.nan, pl)
    ps = np.where(drop, np.nan, ps)
    out["players_xy"], out["players_speed"] = pl, ps
    for k in _PASSTHROUGH:
        if k in d:
            out[k] = np.array(d[k], copy=True) if isinstance(d[k], np.ndarray) else d[k]
    return out
