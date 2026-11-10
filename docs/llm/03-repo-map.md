# Repo map

```
CLAUDE.md, AGENTS.md        LLM entry points
README.md                   human overview + links to organisers' docs
SUBMISSIONS.md              log: one row per CSV validated/uploaded (sha256, comment)
games.py                    asset path resolver (only place that spells filenames)
requirements*.txt           deps (-starter for notebooks)
pipeline/
  make_submission.py        our v1 generator; deterministic, LF CSV, prints sha256
evaluation/                 organisers' scorer (MIT, LICENSE-metrica-sports)
  run_evaluation.py         scores every CSV in evaluation/results/
  validate_submission.py    format/sanity check; run before any upload
  possession_metrics.py     spellF1 / macroF1
  gt/                       PUBLIC 5-min GT, scorer sanity only — not for tuning
  results/                  baselines (tracked); any other *.csv is gitignored
starter/                    organisers' loaders, baseline.py, notebooks
data/                       gated assets; only data/README.md is tracked
submissions/                our generated CSVs; gitignored
docs/llm/                   this documentation
.github/                    PR template with compliance checklist
```

Where new work goes:
- New method/features → `pipeline/` (new module + wired into a `make_submission`-style entry point; keep one command that regenerates each version).
- External training/tuning data and scripts → `external/` (raw data in `data/external/`, gitignored) (create it; document each dataset's source and license in `05-decisions-log.md`; keep raw external data out of git unless its license allows redistribution).
- Tests on synthetic data → `tests/`.
- Intermediate-step files (allowed to be provided) → `outputs/intermediate/`, only if they contain no gated data or label set; otherwise gitignored and shared via the submission form.
