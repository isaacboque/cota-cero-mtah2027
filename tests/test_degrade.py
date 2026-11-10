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
