"""v3 decoder: Viterbi over H / A / D per half with minimum dwell (08-model-plan.md section 2.5).

Pure numpy. Minimum dwell uses the state-duplication trick: each state is a chain of m copies that
must be walked through before the chain can be left, so no run is shorter than m frames.
Codes: 0 H, 1 A, 2 D. Constants in pipeline/config.py (overridable via `params` for grid search).
"""
import numpy as np

from pipeline import config
from pipeline.control import control_team
from pipeline.deadball import deadball_score, hard_dead
from pipeline.features import compute_features

H, A, D = 0, 1, 2
NEG = -1e18


def viterbi_dwell(emis, m_ha, m_d, sw, ex, to_d):
    """Best H/A/D path with minimum dwell.

    emis (n,3) log emissions; sw (n,2) log cost of entering H / A from the other team at frame t;
    ex (n,2) log cost of entering H / A from D; to_d scalar log cost of alive -> D.
    Runs are at least m_ha (H, A) / m_d (D) frames long, except none are cut at the array ends.
    """
    n = len(emis)
    sizes = (max(1, int(m_ha)), max(1, int(m_ha)), max(1, int(m_d)))
    starts = (0, sizes[0], sizes[0] + sizes[1])
    ends = tuple(s + L - 1 for s, L in zip(starts, sizes))
    S = sum(sizes)
    state_of = np.repeat(np.arange(3), sizes)
    delta = np.full(S, NEG)
    for c in range(3):
        delta[starts[c]] = emis[0, c]
    back = np.zeros((n, S), dtype=np.int32)
    for t in range(1, n):
        new = np.full(S, NEG)
        src = np.arange(S, dtype=np.int32)
        for c in range(3):
            s0, L, e = starts[c], sizes[c], ends[c]
            if L > 1:
                new[s0 + 1:s0 + L] = delta[s0:s0 + L - 1]
                src[s0 + 1:s0 + L] = np.arange(s0, s0 + L - 1)
                if delta[e] > new[e]:
                    new[e] = delta[e]
                    src[e] = e
            else:
                new[s0] = delta[s0]
                src[s0] = s0
            # entering chain c from the end of another chain
            for o in range(3):
                if o == c:
                    continue
                if c == D:
                    cost = to_d
                elif o == D:
                    cost = ex[t, c]
                else:
                    cost = sw[t, c]
                v = delta[ends[o]] + cost
                if v > new[s0]:
                    new[s0] = v
                    src[s0] = ends[o]
        new += emis[t][state_of]
        back[t] = src
        delta = new
    cur = max(ends, key=lambda e: delta[e])
    path = np.empty(n, dtype=np.int8)
    for t in range(n - 1, -1, -1):
        path[t] = state_of[cur]
        cur = back[t, cur]
    return path


def merge_short_runs(path, min_len):
    """Merge every run shorter than min_len into its longer neighbour, shortest first."""
    path = path.copy()
    while True:
        cut = np.flatnonzero(path[1:] != path[:-1]) + 1
        b = np.concatenate(([0], cut, [len(path)]))
        lens = np.diff(b)
        short = [i for i in np.argsort(lens, kind="stable") if lens[i] < min_len]
        if not short or len(b) <= 2:
            return path
        i = short[0]
        left = lens[i - 1] if i > 0 else -1
        right = lens[i + 1] if i + 1 < len(lens) else -1
        path[b[i]:b[i + 1]] = path[b[i - 1]] if left >= right else path[b[i + 1]]


def _near(n, frames, w):
    out = np.zeros(n, dtype=bool)
    for f in frames:
        out[max(0, f - w):min(n, f + w + 1)] = True
    return out


def _cfg(params):
    c = {k: getattr(config, k) for k in dir(config) if k.isupper()}
    c.update(params or {})
    return c


def predict_v3(d, kickoff_2nd=config.KICKOFF_2ND, restarts=None, params=None):
    """Decode every half of `d`. `restarts` = [(frame, team_or_None, type)] from
    pipeline.restarts.restart_events (evidence only). Never writes X; D outside the halves."""
    c = _cfg(params)
    n = len(d["ball_seen"])
    fps = c["FPS"]
    w = int(round(c["NEAR_EVENT_S"] * fps))
    feats = compute_features(d)
    score = deadball_score(d, feats, kickoff_2nd)
    hard = hard_dead(n, d["halves"], kickoff_2nd)
    ctrl, runs = control_team(d)

    p = np.clip(score, c["DEAD_P_CLIP"], 1 - c["DEAD_P_CLIP"])
    emis = np.zeros((n, 3))
    emis[:, D] = np.log(p)
    emis[:, H] = emis[:, A] = np.log(1 - p)
    for team in (H, A):
        on = ctrl == team
        off = ctrl == 1 - team
        emis[on, team] += np.log(c["P_CTRL"])
        emis[off, team] += np.log(1 - c["P_CTRL"])
    emis[hard, H] = emis[hard, A] = c["LOG_HARD"]
    emis[hard, D] = 0.0

    near_ctrl = [_near(n, [a for a, _, t in runs if t == team], w) for team in (H, A)]
    cues = restarts or []
    near_cue = [_near(n, [f for f, t, _ in cues if t in (team, None)], w) for team in (H, A)]
    sw = np.stack([np.where(near_ctrl[t], c["LOG_SWITCH_NEAR"], c["LOG_SWITCH_FAR"])
                   for t in (H, A)], axis=1)
    ex = np.stack([np.where(near_cue[t], c["LOG_EXIT_CUE"],
                            np.where(near_ctrl[t], c["LOG_SWITCH_NEAR"], c["LOG_EXIT_FAR"]))
                   for t in (H, A)], axis=1)

    out = np.full(n, D, dtype=np.int8)
    m_ha = int(round(c["MIN_DWELL_HA_S"] * fps))
    m_d = int(round(c["MIN_DWELL_D_S"] * fps))
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        a, b = int(a), int(b) + 1
        path = viterbi_dwell(emis[a:b], m_ha, m_d, sw[a:b], ex[a:b], c["LOG_TO_D"])
        path = merge_short_runs(path, min(m_ha, m_d))
        out[a:b] = path
    return out
