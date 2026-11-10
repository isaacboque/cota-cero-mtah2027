"""Smart Tagging restart cues: EVIDENCE for dead-ball -> alive transitions, not truth.

Takes the list returned by starter.load_smart_tagging.load() (imported by callers, not copied here)
and turns SET PIECES and GOALS into sorted (frame, team_or_None, type) events. Team codes follow
the label codes: 0 = home (H), 1 = away (A), None = no team (Team N/A, e.g. throw-ins, or an
unmapped name). The XML names clubs, so the caller supplies the club -> side map, e.g. from the ATD
metadata team order (first Team = home, as in starter/baseline.py).

Frames are the instance's start_frame (= round(seconds * fps)). The tags mark a window around the
restart, so the frame is accurate to about a second; use restart_mask for a tolerant cue.
"""
import numpy as np

from pipeline import config

# Substrings (lower case) of the `Type` tag -> normalised type. Order matters: first match wins.
SET_PIECE_TYPES = (("throw", "throw_in"), ("corner", "corner"), ("goal kick", "goal_kick"),
                   ("free kick", "free_kick"), ("kick off", "kick_off"))
SET_PIECE_CODE = "set pieces"
GOAL_CODE = "goals"


def _team(tags, team_map):
    name = (tags.get("Team") or "").strip().lower()
    if not name or name in ("n/a", "na", "none"):
        return None
    for club, side in (team_map or {}).items():
        if club.strip().lower() == name:
            return side
    return None


def _set_piece_type(tags):
    t = (tags.get("Type") or "").strip().lower()
    if "(end)" in t:
        return None
    for key, norm in SET_PIECE_TYPES:
        if key in t:
            return norm
    return None


def restart_events(instances, team_map=None):
    """Sorted [(frame, team_or_None, type)] for set pieces (throw_in, corner, goal_kick,
    free_kick, kick_off) and goals (type "goal")."""
    out = []
    for ev in instances:
        code = (ev.get("code") or "").strip().lower()
        tags = ev.get("tags") or {}
        if code == SET_PIECE_CODE:
            kind = _set_piece_type(tags)
        elif code == GOAL_CODE:
            kind = "goal"
        else:
            continue
        if kind is None:
            continue
        out.append((int(ev["start_frame"]), _team(tags, team_map), kind))
    out.sort(key=lambda e: (e[0], e[2]))
    return out


def restart_mask(n, events, pre_s, fps=config.FPS):
    """Bool mask of the `pre_s` seconds just before each restart frame (dead-ball evidence)."""
    mask = np.zeros(n, dtype=bool)
    k = int(round(pre_s * fps))
    for frame, _, _ in events:
        lo, hi = max(0, frame - k), min(n, max(0, frame))
        if lo < hi:
            mask[lo:hi] = True
    return mask
