# Compliance checklist

Copy into the PR description (the PR template already does) and tick before merging or submitting.

- [ ] No file under `data/`, no video, no `*_possession_gt*`, no full-match label CSV is staged (`git status`, `git diff --cached --stat`).
- [ ] No gated data was pasted into any AI chat/tool for this change.
- [ ] Nothing in `pipeline/` reads `evaluation/gt/` or any ground truth.
- [ ] No parameter or model was tuned/trained on ground truth or on the provided video; any tuning/training used external data only.
- [ ] External datasets used: name, source URL, **license** recorded in `05-decisions-log.md`. (None: write "none".)
- [ ] No hand labels or manual per-frame corrections on the provided match.
- [ ] No output was checked against the video.
- [ ] The version choice does not depend on its public-window score.
- [ ] `validate_submission.py` passes; sha256 and comment added to `SUBMISSIONS.md`.
- [ ] Team name in any form is exactly **Cota Cero**.
- [ ] Repo is public and contains no gated or redistributable-restricted content.
