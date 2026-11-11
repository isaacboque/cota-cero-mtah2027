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
    """Missing share over graded frames (rows inside the halves), as DATA.md states the 41 %."""
    inside = np.zeros(len(d["ball_seen"]), bool)
    for _, a, b in d["halves"]:
        inside[a:b + 1] = True
    return float((~d["ball_seen"][inside]).mean())


def test_missing_share_hits_target():
    d = _clean()
    out = degrade(d, {"target_missing": 0.41}, seed=3)
    assert abs(_share(out) - 0.41) <= 0.01
    assert np.isnan(out["ball_xy"][~out["ball_seen"]]).all()


def test_ball_also_drops_on_dead_frames_not_outside_halves():
    d = _clean()
    d["halves"] = np.array([[1, 0, 9999], [2, 12000, 19999]])  # 10000-11999 outside the halves
    out = degrade(d, {"target_missing": 0.41}, seed=3)
    assert abs(_share(out) - 0.41) <= 0.01
    assert (~out["ball_seen"][d["gt_codes"] == 2]).any()
    assert out["ball_seen"][10000:12000].all()


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


def test_load_params_keeps_known_keys_and_tolerates_missing_file(tmp_path):
    from external.degrade import load_params
    f = tmp_path / "p.json"
    f.write_text('{"target_missing": 0.3, "gap_bins": [1, 9], "gap_weights": [1.0], "bogus": 5}')
    p = load_params(str(f))
    assert p == {"target_missing": 0.3, "gap_bins": [1, 9], "gap_weights": [1.0]}
    assert load_params(str(tmp_path / "absent.json")) == {}


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
    already = degrade(d, dict(base, noise_sigma_m=0.3, noise_corr_frames=1), seed=2)  # white: input jitter 0.3 > target
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


def test_gap_stats_input_stats_and_dup_rate():
    n = 100
    pl = np.zeros((n, 4, 2))
    pl[:, 0, 0] = np.arange(n) * 0.2           # slot 0 moves 0.2 m per frame
    pl[:, 1, 0] = 50.0
    pl[:, 1, 0][60] = 60.0                     # slot 1: one 10 m jump out and one back
    pl[:, 2, 0] = 20.0                         # slots 2 and 3: same team, 0.1 m apart -> duplicates
    pl[:, 3, 0] = 20.1
    d = {"ball_seen": np.ones(n, bool), "players_xy": pl, "ball_xy": np.zeros((n, 2)),
         "slot_team": np.array([0, 0, 1, 1], dtype=np.int8), "halves": np.array([[1, 0, n - 1]])}
    p = barath_gap_stats.compute(d, bins=[1, 5, 25])
    s = p["input_stats"]
    assert set(s["player_step_m"]) == {"p50", "p90", "p99"}
    assert s["visible_per_team"] == [2.0, 2.0]
    assert abs(s["track_jump_rate"] - 2 / (99 * 4)) < 1e-9
    assert abs(s["dup_share"] - 0.5) < 1e-9   # 2 of 4 slots sit within 0.5 m of a teammate
    assert abs(p["dup_prob"] - 0.25) < 1e-9   # one degrade() duplicate makes two close slots
    assert p["swap_start_rate"] == s["track_jump_rate"]


def test_team_swap_takes_opponent_positions_in_runs():
    d = _clean(5000)
    d["players_xy"][:, :11] = 0.0
    d["players_xy"][:, 11:] = 100.0
    out = degrade(d, {"swap_start_rate": 0.002, "swap_len_frames": 50, "dup_prob": 0.0,
                      "target_visible_slots": None}, seed=1)
    home = out["players_xy"][:, :11, 0]
    swapped = np.isfinite(home) & (home == 100.0)
    assert swapped.any() and not swapped.all()
    assert swapped.sum() >= 0.5 * 50 * swapped[1:].__gt__(swapped[:-1]).sum()  # runs, not single frames


def test_default_degrade_has_no_team_swap():
    d = _clean(5000)
    d["players_xy"][:, :11] = 0.0
    d["players_xy"][:, 11:] = 100.0
    out = degrade(d, {"target_visible_slots": None}, seed=1)
    assert not (out["players_xy"][:, :11, 0] == 100.0).any()


def test_noise_is_temporally_correlated_but_keeps_sigma():
    d = _clean(20000)
    out = degrade(d, {"target_missing": 0.0, "noise_sigma_m": 0.3, "dup_prob": 0.0,
                      "target_visible_slots": None, "noise_corr_frames": 50}, seed=5)
    err = out["ball_xy"] - d["ball_xy"]
    assert 0.2 < err.std() < 0.4                 # marginal sigma kept
    assert np.diff(err, axis=0).std() < 0.1      # frame-to-frame jitter small => velocity noise < ~2.5 m/s at 25 fps
