import numpy as np

from external import barath_gap_stats
from external.degrade import degrade


def _clean(n=20000, slots=22, seed=1):
    rng = np.random.default_rng(seed)
    gt = np.where(np.arange(n) % 1000 < 800, rng.integers(0, 2, n) * 0 + (np.arange(n) // 500) % 2, 2)
    return {
        "ball_xy": rng.uniform(0, 100, (n, 2)), "ball_speed": rng.uniform(0, 20, n),
        "ball_seen": np.ones(n, bool),
        "players_xy": rng.uniform(0, 100, (n, slots, 2)),
        "players_speed": rng.uniform(0, 8, (n, slots)),
        "slot_team": np.array([0] * (slots // 2) + [1] * (slots // 2), dtype=np.int8),
        "gt_codes": gt.astype(np.int8), "halves": np.array([[1, 0, n // 2 - 1], [2, n // 2, n - 1]]),
    }


def _share(d):
    alive = (d["gt_codes"] == 0) | (d["gt_codes"] == 1)
    return float((~d["ball_seen"][alive]).mean())


def test_missing_share_hits_target():
    d = _clean()
    out = degrade(d, {"target_missing": 0.41}, seed=3)
    assert abs(_share(out) - 0.41) <= 0.01
    assert np.isnan(out["ball_xy"][~out["ball_seen"]]).all()


def test_gaps_are_contiguous():
    out = degrade(_clean(), {"gap_bins": [50, 100], "gap_weights": [1.0]}, seed=0)
    miss = ~out["ball_seen"]
    edges = np.diff(np.concatenate(([0], miss.astype(np.int8), [0])))
    runs = np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)
    assert runs.min() >= 1 and np.median(runs) >= 50


def test_deterministic_for_seed():
    d = _clean(5000)
    a, b, c = degrade(d, seed=7), degrade(d, seed=7), degrade(d, seed=8)
    for k in a:
        assert np.array_equal(a[k], b[k], equal_nan=True)
    assert not np.array_equal(a["ball_seen"], c["ball_seen"])


def test_gt_and_input_untouched():
    d = _clean(5000)
    snap = {k: np.array(v, copy=True) for k, v in d.items()}
    out = degrade(d, seed=2)
    for k in snap:
        assert np.array_equal(d[k], snap[k], equal_nan=True)  # input not mutated
    for k in ("gt_codes", "halves", "slot_team"):
        assert np.array_equal(out[k], snap[k])


def test_noise_and_slot_drop():
    d = _clean(5000)
    out = degrade(d, {"target_missing": 0.0, "noise_sigma_m": 0.5, "dup_prob": 0.0,
                      "target_visible_slots": 11.0}, seed=4)
    seen = out["ball_seen"]
    diff = out["ball_xy"][seen] - d["ball_xy"][seen]
    assert 0.4 < diff.std() < 0.6
    vis = np.isfinite(out["players_xy"][..., 0]).sum(axis=1).mean()
    assert abs(vis - 11.0) < 0.5


def test_gap_stats_compute():
    n = 100
    seen = np.ones(n, bool)
    seen[10:20] = False   # gap 10
    seen[50:53] = False   # gap 3
    d = {"ball_seen": seen, "players_xy": np.zeros((n, 4, 2)), "halves": np.array([[1, 0, n - 1]])}
    p = barath_gap_stats.compute(d, bins=[1, 5, 25])
    assert abs(p["target_missing"] - 0.13) < 1e-9
    assert p["gap_weights"] == [0.5, 0.5]
    assert p["target_visible_slots"] == 4.0


def test_jitter_sigma_recovers_noise_on_moving_tracks():
    rng = np.random.default_rng(0)
    t = np.arange(5000)[:, None]
    clean = np.concatenate([t * 0.2, 30 + 5 * np.sin(t / 40.0)], axis=1)  # smooth motion
    from external.degrade import jitter_sigma
    assert jitter_sigma(clean) < 0.01
    noisy = clean + rng.normal(0, 0.15, clean.shape)
    assert abs(jitter_sigma(noisy) - 0.15) < 0.01


def test_degrade_adds_only_the_missing_jitter():
    from external.degrade import jitter_sigma
    d = _clean(4000)
    t = np.arange(4000)[:, None, None]
    d["players_xy"] = np.broadcast_to(t * 0.1, (4000, 22, 2)).copy()   # smooth, no own jitter
    d["ball_xy"] = np.concatenate([np.arange(4000)[:, None] * 0.3] * 2, axis=1)
    base = {"target_missing": 0.0, "dup_prob": 0.0, "target_visible_slots": None}
    out = degrade(d, dict(base, player_jitter_m=0.2, ball_jitter_m=0.1), seed=1)
    assert abs(jitter_sigma(out["players_xy"]) - 0.2) < 0.02
    assert abs(jitter_sigma(out["ball_xy"]) - 0.1) < 0.02
    already = degrade(d, dict(base, noise_sigma_m=0.3), seed=2)       # input jitter 0.3 > target
    again = degrade(already, dict(base, player_jitter_m=0.2), seed=3)
    assert np.allclose(again["players_xy"], already["players_xy"])    # nothing added


def test_default_degrade_adds_no_noise():
    d = _clean(2000)
    out = degrade(d, {"target_missing": 0.0, "dup_prob": 0.0, "target_visible_slots": None}, seed=0)
    assert np.array_equal(out["players_xy"], d["players_xy"])


def test_gap_stats_include_jitter():
    n = 200
    d = {"ball_seen": np.ones(n, bool), "players_xy": np.zeros((n, 4, 2)),
         "ball_xy": np.zeros((n, 2)), "halves": np.array([[1, 0, n - 1]])}
    p = barath_gap_stats.compute(d, bins=[1, 5, 25])
    assert p["player_jitter_m"] == 0.0 and p["ball_jitter_m"] == 0.0
