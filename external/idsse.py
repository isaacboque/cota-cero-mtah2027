"""IDSSE adapter (Bassek et al. 2025, Scientific Data 12:195; DFL; CC BY 4.0; 25 fps).

Returns the same keys as pipeline.data.load_barath, plus `gt_codes`:
  0 = H (ball alive, home owns), 1 = A (alive, away owns), 2 = D (ball dead), -1 = ball state unknown.
Extra key `fps` (also returned by load_barath). Rows are the dataset's frames in order (both halves,
no gap rows); `halves` is (period, first_row, last_row) in row indices, same meaning as load_barath.
Slots: every squad player listed in the metadata (home first, then away; bench players included,
so the count varies per match, unlike BAR-ATH's 46 tracks); `slot_team` is 0/1 accordingly.

kloppy's sportec reader sets ball_owning_team to home if the raw possession flag is 1 and to AWAY
otherwise (never None), so the owner is only meaningful on alive frames. Load with only_alive=False
and take D from ball_state, never from the owner.

Matches (kloppy 3.18.0 DATA_MAP): J03WPY J03WMX J03WN1 J03WOH J03WOY J03WQQ J03WR9.
"""
import os

import numpy as np

MATCH_IDS = ("J03WPY", "J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WQQ", "J03WR9")
CODES = {"H": 0, "A": 1, "D": 2}


def filter_owner_flicks(gt_codes, halves, min_frames=25):
    """Filtered reference labels: owner changes shorter than `min_frames` do not count.

    Inside each alive stretch (consecutive H/A rows within one half), an owner run shorter than
    `min_frames` takes the owner of the nearest earlier long run, or of the first long run if none
    precedes it. Stretches with no long run, D and -1 rows are left as they are. Returns a copy.
    Source: ticket "Criterios de éxito del control" (1.3); 25 frames = 1 s at IDSSE's 25 fps.
    """
    gt = np.asarray(gt_codes)
    out = gt.copy()
    for _, a, b in np.asarray(halves).reshape(-1, 3):
        seg = gt[int(a):int(b) + 1]
        alive = (seg == 0) | (seg == 1)
        i = 0
        while i < len(seg):
            if not alive[i]:
                i += 1
                continue
            j = i
            while j < len(seg) and alive[j]:
                j += 1
            runs, k = [], i
            while k < j:
                m = k
                while m < j and seg[m] == seg[k]:
                    m += 1
                runs.append((k, m, seg[k]))
                k = m
            longs = [r for r in runs if r[1] - r[0] >= min_frames]
            if longs:
                owner = longs[0][2]
                for s, e, c in runs:
                    if e - s >= min_frames:
                        owner = c
                    else:
                        out[int(a) + s:int(a) + e] = owner
            i = j
    return out


def from_dataset(ds):
    """Convert a kloppy TrackingDataset (loaded with only_alive=False) to the loader dict."""
    teams = ds.metadata.teams
    players = list(teams[0].players) + list(teams[1].players)
    slot_team = np.array([0] * len(teams[0].players) + [1] * len(teams[1].players), dtype=np.int8)
    dims = ds.metadata.pitch_dimensions
    length, width = dims.pitch_length, dims.pitch_width  # kloppy default coords are 0-1
    n = len(ds.frames)
    out = {
        "ball_xy": np.full((n, 2), np.nan), "ball_speed": np.full(n, np.nan),
        "ball_seen": np.zeros(n, dtype=bool),
        "players_xy": np.full((n, len(players), 2), np.nan),
        "players_speed": np.full((n, len(players)), np.nan),
        "slot_team": slot_team, "gt_codes": np.full(n, -1, dtype=np.int8),
    }
    home = teams[0]
    periods = []
    for i, f in enumerate(ds.frames):
        if f.ball_coordinates is not None:
            out["ball_xy"][i] = (f.ball_coordinates.x * length, f.ball_coordinates.y * width)
            out["ball_speed"][i] = f.ball_speed if f.ball_speed is not None else np.nan
            out["ball_seen"][i] = True
        for s, p in enumerate(players):
            d = f.players_data.get(p)
            if d is not None and d.coordinates is not None:
                out["players_xy"][i, s] = (d.coordinates.x * length, d.coordinates.y * width)
                out["players_speed"][i, s] = d.speed if d.speed is not None else np.nan
        state = getattr(f.ball_state, "name", None)  # kloppy BallState enum member
        if state == "ALIVE":
            out["gt_codes"][i] = CODES["H"] if f.ball_owning_team == home else CODES["A"]
        elif state == "DEAD":
            out["gt_codes"][i] = CODES["D"]
        pid = f.period.id
        if not periods or periods[-1][0] != pid:
            periods.append([pid, i, i])
        periods[-1][2] = i
    out["halves"] = np.array(periods, dtype=np.int64).reshape(-1, 3)
    out["fps"] = np.array(float(ds.metadata.frame_rate))
    return out


def _load_raw(match_id, cache_dir):
    """Parse one match with kloppy (slow: a full-match XML). Local files `<cache_dir>/<id>_meta.xml`
    and `<id>_tracking.xml` are used if present (figshare blocks scripted downloads with a WAF
    challenge); otherwise kloppy downloads them."""
    from kloppy import sportec

    meta = os.path.join(cache_dir, "{}_meta.xml".format(match_id))
    raw = os.path.join(cache_dir, "{}_tracking.xml".format(match_id))
    if os.path.exists(meta) and os.path.exists(raw):
        ds = sportec.load_tracking(meta_data=meta, raw_data=raw, only_alive=False)
    else:
        ds = sportec.load_open_tracking_data(match_id=match_id, only_alive=False)
    return from_dataset(ds)


# Bump when from_dataset's output changes, so stale caches are not reused.
CACHE_VERSION = 1


def cache_path(match_id, cache_dir):
    return os.path.join(cache_dir, "{}_arrays_v{}.npz".format(match_id, CACHE_VERSION))


def load_idsse(match_id, cache_dir="data/external/idsse", use_cache=True):
    """Load one IDSSE match as the loader dict.

    The first call parses the XML with kloppy and saves the arrays to `<cache_dir>/<id>_arrays_vN.npz`;
    later calls read that file in seconds. The cache is rebuilt if the tracking XML is newer than
    it. Raw files and caches are external data under CC BY 4.0, kept under the gitignored data/.
    """
    npz = cache_path(match_id, cache_dir)
    raw = os.path.join(cache_dir, "{}_tracking.xml".format(match_id))
    if use_cache and os.path.exists(npz) and (
            not os.path.exists(raw) or os.path.getmtime(npz) >= os.path.getmtime(raw)):
        with np.load(npz) as z:
            return {k: z[k] for k in z.files}
    out = _load_raw(match_id, cache_dir)
    if use_cache:
        os.makedirs(cache_dir, exist_ok=True)
        tmp = npz[:-len(".npz")] + ".tmp.npz"
        np.savez_compressed(tmp, **out)
        os.replace(tmp, npz)  # never leave a half-written cache behind
    return out
