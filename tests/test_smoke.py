"""Smoke test: the shared constants module imports and agrees with the submission contract."""
import games


def test_half_video_blocks():
    assert games.half_video_blocks("BAR-ATH") == [(1, 11185, 90651), (2, 110808, 190197)]


def test_source_frames():
    assert games.source_frames("tactical") == 199319


def test_make_submission_imports_without_data():
    # Import only: nothing is read or run (main() is guarded).
    import pipeline.make_submission as ms
    assert callable(ms.main)
