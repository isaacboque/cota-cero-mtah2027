"""Loader and cache for the ATD tracking (FIFA/EPTS) as numpy arrays, indexed by submission row.

Row i holds frame_id i + 1 (frame ids count from 1, submissions from 0), as in starter/baseline.py.
Coordinates in the file are normalised 0-1 and are scaled to metres here. Paths come only from the
caller's arguments (callers use games.asset_paths); nothing here knows where the data lives.

Raw line: "<frame>:<slot>;<slot>;...:<ball>", each group "x,y,speed", NaN where missing.
Cache files are frame-level tracking: keep them under the gitignored data/ and never publish them.
"""
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import games  # noqa: E402

HOME, AWAY = 0, 1
DEFAULT_PITCH = (105.3, 68.0)
_KEYS = ("ball_xy", "ball_speed", "ball_seen", "players_xy", "players_speed", "slot_team", "halves")


def slot_teams(meta_path):
    """int8 per track slot: 0 home, 1 away. The first Team in the metadata is home."""
    root = ET.parse(meta_path).getroot()
    team_ids = [t.get("id") for t in root.iter("Team")]
    if len(team_ids) != 2:
        raise ValueError("{}: expected 2 teams, found {}".format(meta_path, len(team_ids)))
    slots = [p.get("teamId") for p in root.iter("Player")]
    if not slots:
        raise ValueError("{}: no Player entries".format(meta_path))
    return np.array([HOME if t == team_ids[0] else AWAY for t in slots], dtype=np.int8)


def _group(text):
    """(x, y, speed) floats from 'x,y,speed'; NaNs if the group is missing or short."""
    if not text or text[0] == "N":
        return None
    vals = text.split(",")
    return float(vals[0]), float(vals[1]), float(vals[2]) if len(vals) > 2 else np.nan


def load_barath(meta_path, raw_path, pitch=DEFAULT_PITCH, n_frames=None):
    """Parse one ATD source into arrays indexed by `frame_id - 1`.

    n_frames=None sizes the arrays to the highest frame id in the file. Frames absent from the file
    stay NaN with ball_seen False. Lines that do not split into 3 fields are skipped.
    """
    slot_team = slot_teams(meta_path)
    n_slots = len(slot_team)
    length, width = pitch
    rows = []  # (index, ball or None, [group or None])
    with open(raw_path) as handle:
        for line in handle:
            parts = line.rstrip("\r\n").split(":")
            if len(parts) != 3:
                continue
            groups = parts[1].split(";")
            if len(groups) != n_slots:
                raise ValueError("frame {}: {} slots, metadata has {}".format(
                    parts[0], len(groups), n_slots))
            rows.append((int(parts[0]) - 1, _group(parts[2]), [_group(g) for g in groups]))

    if n_frames is None:
        n_frames = max((r[0] for r in rows), default=-1) + 1
    ball_xy = np.full((n_frames, 2), np.nan)
    ball_speed = np.full(n_frames, np.nan)
    ball_seen = np.zeros(n_frames, dtype=bool)
    players_xy = np.full((n_frames, n_slots, 2), np.nan)
    players_speed = np.full((n_frames, n_slots), np.nan)

    for idx, ball, groups in rows:
        if not 0 <= idx < n_frames:
            continue
        if ball is not None:
            ball_xy[idx] = (ball[0] * length, ball[1] * width)
            ball_speed[idx] = ball[2]
            ball_seen[idx] = True
        for slot, g in enumerate(groups):
            if g is not None:
                players_xy[idx, slot] = (g[0] * length, g[1] * width)
                players_speed[idx, slot] = g[2]

    halves = np.array(games.half_video_blocks(games.GAME), dtype=np.int64)
    return {"ball_xy": ball_xy, "ball_speed": ball_speed, "ball_seen": ball_seen,
            "players_xy": players_xy, "players_speed": players_speed,
            "slot_team": slot_team, "halves": halves}


def save_cache(d, path):
    """Write the arrays to a compressed .npz (frame-level tracking: never commit or publish)."""
    np.savez_compressed(path, **{k: d[k] for k in d})


def load_cache(path):
    with np.load(path) as z:
        return {k: z[k] for k in z.files}
