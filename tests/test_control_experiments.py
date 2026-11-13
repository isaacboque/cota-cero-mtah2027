"""The gap-dead and taker experiment definitions, on invented data only (no BAR-ATH, no ground truth)."""
from external import control_experiments as ce
from pipeline import config


def test_with_config_applies_inside_the_call_and_restores_after():
    seen = {}

    def fn(d):
        seen["inside"] = config.MISSING_RUN_MIN_S
        return d

    before = config.MISSING_RUN_MIN_S
    ce.with_config({"MISSING_RUN_MIN_S": 99.0}, fn)("x")
    assert seen["inside"] == 99.0
    assert config.MISSING_RUN_MIN_S == before


def test_with_config_restores_after_an_error():
    def boom(d):
        raise ValueError

    before = config.W_MISSING_STATIC
    try:
        ce.with_config({"W_MISSING_STATIC": 0.0}, boom)("x")
    except ValueError:
        pass
    assert config.W_MISSING_STATIC == before


def test_gapdead_has_the_current_setting_and_the_rule_off():
    names = set(ce.predictors("gapdead"))
    assert {"v4_base", "v4_off", "v4_mrun5", "v4_mrun8", "v4_mrun12", "v4_w0.3"} <= names


def test_taker_grid_includes_the_current_setting():
    names = set(ce.predictors("taker"))
    assert "v4_r{}_w{}".format(config.R_TAKER_M, config.TAKER_WINDOW_S) in names
