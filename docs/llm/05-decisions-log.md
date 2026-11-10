# Decisions log

One entry per method/parameter decision. Newest first. The "Source" field is mandatory and must not be "score on the public window".

Template:
```
## YYYY-MM-DD — short title
- Decision:
- Source / justification: (organiser doc §, paper, external dataset + license)
- Data used to choose it: (external only / none)
- Compliance check: (which rules from 01-rules.md were considered)
- Owner:
```

## 2026-11-10 — Public 5-minute window: not used for tuning
- Decision: treat the public window as scorer sanity / definition reading only; no parameter, feature or version choice depends on it.
- Source / justification: organisers' 10 Nov email (no training/fitting/calibrating on ground-truth possession data; no hand labels on the provided game) is stricter than `RULES.md`, which is silent on the window. Following the stricter text.
- Data used to choose it: none.
- Compliance check: rules 2 and 3 of `01-rules.md`.
- Owner: Isaac

## 2026-11-09 — v1: nearest player to ball + majority vote ±50 frames
- Decision: reuse organisers' `starter/baseline.py` steps with window ±50 frames; LF-only CSV writer.
- Source / justification: window is the one the organisers publish as best on the full match in `EVALUATION.md`; not chosen from the public 5-minute window.
- Data used to choose it: none (organiser-published figure).
- Compliance check: no training, no GT access, no video check, no data sent to AI.
- Owner: Isaac
