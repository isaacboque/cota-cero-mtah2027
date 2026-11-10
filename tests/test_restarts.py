import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starter"))
import load_smart_tagging as lst  # noqa: E402

from pipeline import restarts  # noqa: E402

INSTANCES = [
    ("SET PIECES", 100.0, 105.0, {"Type": "Throw-in", "Team": "N/A"}),
    ("SET PIECES", 10.0, 14.0, {"Type": "Corner", "Team": "Blue FC"}),
    ("SET PIECES", 50.2, 55.0, {"Type": "Goal Kick", "Team": "Red FC"}),
    ("SET PIECES", 70.0, 75.0, {"Type": "Free Kick", "Team": "Blue FC"}),
    ("SET PIECES", 5.0, 9.0, {"Type": "Kick Off (Start)", "Team": "Red FC"}),
    ("GOALS", 80.0, 85.0, {"Team": "Blue FC"}),
    ("BUILD UP", 20.0, 30.0, {"Team": "Blue FC"}),                      # not a restart
    ("SET PIECES", 90.0, 92.0, {"Type": "Penalty??", "Team": "Blue FC"}),  # unknown type
]


def _write(tmp_path):
    folder = tmp_path / "tactical"
    folder.mkdir()
    parts = ["<file><ALL_INSTANCES>"]
    for code, s, e, tags in INSTANCES:
        labels = "".join("<label><group>{}</group><text>{}</text></label>".format(g, t)
                         for g, t in tags.items())
        parts.append("<instance><ID>1</ID><start>{}</start><end>{}</end><code>{}</code>{}</instance>"
                     .format(s, e, code, labels))
    parts.append("</ALL_INSTANCES></file>")
    (folder / "BAR-ATH_tactical_smart_tagging.xml").write_text("".join(parts))
    return str(tmp_path)


def test_events_frames_teams_sorted(tmp_path):
    inst = lst.load(data_dir=_write(tmp_path))
    ev = restarts.restart_events(inst, {"Blue FC": 0, "Red FC": 1})
    assert ev == [
        (125, 1, "kick_off"), (250, 0, "corner"), (1255, 1, "goal_kick"),
        (1750, 0, "free_kick"), (2000, 0, "goal"), (2500, None, "throw_in"),
    ]
    assert [e[0] for e in ev] == sorted(e[0] for e in ev)


def test_throw_in_has_no_team_and_unmapped_club_is_none(tmp_path):
    inst = lst.load(data_dir=_write(tmp_path))
    ev = restarts.restart_events(inst)  # no team map: every team None
    assert all(t is None for _, t, _ in ev)
    assert ev[-1] == (2500, None, "throw_in")


def test_restart_mask_window():
    mask = restarts.restart_mask(300, [(100, 0, "corner"), (5, None, "throw_in")], pre_s=1.0)
    assert mask[75:100].all() and not mask[100] and not mask[74]
    assert mask[:5].all() and mask.sum() == 25 + 5
    assert not restarts.restart_mask(10, [], 2.0).any()
