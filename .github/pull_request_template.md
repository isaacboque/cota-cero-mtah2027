## What and why

## Source of any method/parameter choice
(organiser doc, paper, external dataset + license — not the public-window score)

## Compliance checklist (see docs/llm/06-compliance-checklist.md)
- [ ] No gated data, video, or ground-truth files committed
- [ ] No gated data sent to any AI service
- [ ] Nothing in `pipeline/` reads ground truth; no tuning/training on GT or the provided video
- [ ] External data used (if any) is licensed and logged in `docs/llm/05-decisions-log.md`
- [ ] No hand labels / no output checked against the video
- [ ] Version choice not based on the public-window score
- [ ] If a submission: validated, sha256 logged in `SUBMISSIONS.md`
