"""v2: sticky possession (08-model-plan.md sections 1, 2.4, 2.6).

Per half: the state changes H<->A only when the other team gains control; goes to D on the
dead-ball decision (pipeline/deadball.py, which also forces D before the 2nd-half kick-off); leaves
D to the first team that gains control; carries through ball-missing frames. D outside the halves.
Never writes X. Codes: 0 H, 1 A, 2 D.
"""
import numpy as np

from pipeline import config
from pipeline.control import control_team
from pipeline.deadball import dead_mask
from pipeline.features import compute_features

H, A, D = 0, 1, 2


def predict_v2(d, kickoff_2nd=config.KICKOFF_2ND):
    n = len(d["ball_seen"])
    dead = dead_mask(d, compute_features(d), kickoff_2nd)
    ctrl, _ = control_team(d)
    out = np.full(n, D, dtype=np.int8)
    for _, a, b in np.asarray(d["halves"]).reshape(-1, 3):
        state = D
        for i in range(int(a), int(b) + 1):
            if dead[i]:
                state = D
            elif ctrl[i] >= 0:
                state = int(ctrl[i])  # a control run of the other team (or the first after D)
            out[i] = state
    return out
