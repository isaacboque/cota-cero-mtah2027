"""Degrade clean external tracking (IDSSE) so it looks like the BAR-ATH input.

Operates on the array dict of pipeline.data / external.idsse. Never touches `gt_codes`, `halves`,
`slot_team` or `fps`. Fully deterministic for a given (params, seed).

Steps, in order:
  1. ball dropout on GRADED frames (rows inside the halves, alive or dead) in contiguous gaps, gap
     lengths drawn from a histogram, until the missing share of graded frames reaches
     `target_missing` (last gap truncated to land on it). DATA.md states the 41 % over graded frames,
     and on BAR-ATH alive frames cannot be told apart without the ground truth;
  2. Gaussian position noise (sigma in metres) on every visible ball and player position;
  3. optional cross-team identity swaps (`swap_start_rate`, `swap_len_frames`; off by default);
  4. player slots randomly dropped (down to `target_visible_slots` per frame if given, else
     `drop_prob`) and duplicated (a slot takes another same-team slot's position, `dup_prob`).

DEFAULT_PARAMS are placeholders from organiser docs (DATA.md: ball missing on 41 % of graded
frames; ~20.5 visible slots per frame, 46 tracks) and a made-up gap histogram. The real histogram
and slot count come from external/barath_gap_stats.py, run by a human -> data/cache/degrade_params.json.
"""
import numpy as np

# Source of each value: target_missing = DATA.md (41 % of graded frames); target_visible_slots =
# 08-model-plan.md section 1 (~20.5 visible); noise_sigma_m, dup_prob, gap_* = placeholders to be
# replaced by degrade_params.json (aggregate BAR-ATH input stats, computed by a human).
#
# Position noise: if `player_jitter_m` / `ball_jitter_m` are given (the BAR-ATH frame-to-frame jitter
# measured by barath_gap_stats.py), only the noise IDSSE is missing is added:
# sqrt(max(0, target^2 - own^2)), own = jitter_sigma() of the clean input. Otherwise `noise_sigma_m`
# is added as is. Its default is 0: an unmeasured 0.3 m of independent per-frame noise made every
# 1-frame velocity useless (10+ m/s of fake speed) and broke v2/v3 in the first IDSSE run (11 Nov).
DEFAULT_PARAMS = {
    "target_missing": 0.41,
    "gap_bins": [1, 5, 25, 125, 625, 3125],      # frame-length bin edges [lo, hi)
    "gap_weights": [0.20, 0.25, 0.25, 0.20, 0.10],  # relative frequency of gaps per bin
    "noise_sigma_m": 0.0,
    "player_jitter_m": None,
    "ball_jitter_m": None,
    "target_visible_slots": 20.5,
    "drop_prob": 0.0,
    "dup_prob": 0.02,
    "swap_start_rate": 0.0,   # per slot-frame; > 0 only from barath_gap_stats (track_jump_rate)
    "swap_len_frames": 50,    # placeholder: 2 s per identity swap
}
_PASSTHROUGH = ("gt_codes", "halves", "slot_team", "fps")


def jitter_sigma(xy):
    """Robust per-frame position noise (m) from second differences along rows.

    For independent noise of sigma per coordinate, x[t+1] - 2x[t] + x[t-1] has std sqrt(6)*sigma,
    while real motion adds only acceleration/fps^2 (a few mm at 25 fps). The median absolute
    deviation keeps kicks and track swaps from inflating it. 0.0 if there is too little data.
    """
    xy = np.asarray(xy, dtype=float)
    if len(xy) < 3:
        return 0.0
    d2 = xy[2:] - 2.0 * xy[1:-1] + xy[:-2]
    v = d2[np.isfinite(d2)]
    if v.size < 10:
        return 0.0
    mad = np.median(np.abs(v - np.median(v)))
    return float(1.4826 * mad / np.sqrt(6.0))


def _added_sigma(target, own, fallback):
    if target is None:
        return float(fallback)
    return float(np.sqrt(max(0.0, float(target) ** 2 - own ** 2)))


def _graded(d):
    n = len(d["ball_seen"])
    if "halves" not in d:
        return np.ones(n, dtype=bool)
    inside = np.zeros(n, dtype=bool)
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        inside[int(a):int(b) + 1] = True
    return inside


def _drop_ball(d, out, params, rng):
    alive = _graded(d)  # rows eligible for dropout
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
        rows = rows[alive[rows]]
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

    sigma_ball = _added_sigma(p.get("ball_jitter_m"), jitter_sigma(d["ball_xy"]), p["noise_sigma_m"])
    sigma_pl = _added_sigma(p.get("player_jitter_m"), jitter_sigma(d["players_xy"]), p["noise_sigma_m"])
    if sigma_ball > 0:
        out["ball_xy"] += rng.normal(0.0, sigma_ball, out["ball_xy"].shape)  # NaN stays NaN
    if sigma_pl > 0:
        out["players_xy"] += rng.normal(0.0, sigma_pl, out["players_xy"].shape)

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
    # team swaps: from a random start, a slot shows a random opponent's track for swap_len_frames
    # (an identity switch across teams; switches within a team do not change team-level control)
    rate = float(p.get("swap_start_rate") or 0.0)
    if rate > 0:
        length = int(p.get("swap_len_frames", 50))
        for f, sl in zip(*np.nonzero(rng.random((n, s)) < rate)):
            opp = np.flatnonzero(team != team[sl])
            if len(opp) == 0:
                continue
            o = opp[rng.integers(0, len(opp))]
            pl[f:f + length, sl] = pl[f:f + length, o]
            ps[f:f + length, sl] = ps[f:f + length, o]
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
