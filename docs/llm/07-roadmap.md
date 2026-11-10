# Roadmap, approaches and open questions

## Schedule (Europe/Madrid)
| Phase | Dates | Who |
|---|---|---|
| Registration | 1 Oct – **10 Nov 2026** (closed for us: team *Cota Cero*) | all |
| **Initial Challenge** (this repo's focus) | 20 Oct – **17 Nov 2026** (exact cut-off hour: confirm in `SUBMISSION.md`) | all registered teams |
| Innovation Challenge | 26 Nov 2026 – 14 Jan 2027, online | top 20 |
| Final Pitch | 2 Mar 2027, on-site at Talent Arena, Barcelona, professional jury | top 5 |

Teams under 3 members cannot advance past the Initial Challenge. Prizes: travel/stay for the final, FC Barcelona shirts and experience; no cash.

## Approach ladder for the Initial Challenge
Each rung must be justified by an organiser document, literature or **external** data (see `01-rules.md`). Log each in `05-decisions-log.md`.

1. **v1 (done):** nearest tracked player to the ball, majority vote ±50 frames.
2. **Better frame-level signal, no fitting:** distance of the ball to the nearest player of each team, ball speed/height proxies from tracking, ball-in-play handling, tracking gaps. Rule-based or with thresholds taken from organiser docs or external data.
3. **Temporal model for spells:** the metric `spellF1` rewards correct segments, not just frames, so flicker is costly. Options: HMM/Viterbi smoothing, minimum-spell-duration rules, hysteresis. **Transition/emission parameters may not be fitted on the ground truth or the provided video.** Set them from domain priors, organiser statistics or external tracking data we have rights to.
4. **Use of Smart Tagging:** `smart_tagging.xml` is generated data and allowed as input (638 phases and set pieces); check what its fields mean in `DATA.md` before relying on it.
5. **Learned classifier:** only if trained on **external** tracking/event data with a compatible license. Any plan of the form "train on the labels we are given" is forbidden here.
6. **Reproducibility:** every version regenerable with one command; sha256 in `SUBMISSIONS.md`.

Related methods worth referencing in the decisions log: homography use for pitch coordinates, Kalman-style smoothing of the ball track, nearest-neighbour assignment between ball and players, packing/xT-style features for Round 2.

## Round 2 outline (Innovation Challenge, only if top 20)
- Data: 10 professional matches; open-ended analytical/tactical question chosen by the team; specialised technical mentoring.
- The same compliance mindset applies until the organisers publish Round 2 rules; assume nothing carries over as allowed.
- Candidate questions (ideas only, none chosen): pressing and ball recovery after turnovers; defensive shape and compaction by possession state; threat from tracking (xT with all 22 players, off-ball runs). Each should end in a decision a coach could act on.

## Open questions (Unconfirmed — do not guess)
- Exact meaning of labels `H`, `A`, `D`, `X` and what counts as possession: read upstream `CHALLENGE.md`.
- Exact cut-off time on 17 Nov and the submission form fields: upstream `SUBMISSION.md` (organisers said instructions would follow).
- Whether the full-match score is shown to teams or only the public window: check `EVALUATION.md` / `FAQ.md`.
- External datasets we could legitimately use for training/tuning (name, license) — none recorded yet.
- Contact for rule doubts: hackathon.talentarena@mobileworldcapital.com. In a gray area, ask before building.
