# cota-cero-mtah2027

Team Cota Cero: More Than a Hack 2027, Phase 1 (Initial Challenge). For every frame of one LaLiga match, label which team has the ball (`H`, `A`, `D`, `X`) from automatic tracking data.

**No match data is in this repository.** The assets are gated and licensed for the competition only. Put them in `data/tactical/` (gitignored) or point `MTAH_DATA_DIR` at them.

## Reproduce

```bash
pip install -r requirements.txt
python evaluation/run_evaluation.py      # scores the shipped baselines, needs no data
```

Regenerate the current submission file (needs the data in `data/tactical/`):

```bash
python pipeline/make_submission.py
python evaluation/validate_submission.py submissions/cota-cero_v1.csv
```

The CSV is always written with LF line endings, so the sha256 printed by the first command is the same on Windows, macOS and Linux.

## Layout

- `evaluation/`, `starter/`, `games.py`: organisers' scorer, loaders and baselines (MIT, see `LICENSE-metrica-sports`)
- `SUBMISSIONS.md`: log of every file validated or submitted

## Read first (organisers' documents)

Everyone on the team reads these before touching anything. They live in the official repo and are not copied here, so they stay current:

- [CHALLENGE.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/CHALLENGE.md): the task, the four labels, what counts as possession
- [RULES.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/RULES.md): what is forbidden (no hand labels on the provided match, no tuning on the public 5 minutes)
- [EVALUATION.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/EVALUATION.md): how spellF1 and macroF1 work
- [SUBMISSION.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/SUBMISSION.md): the three deliverables and the form
- [DATA.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/DATA.md): every asset and how frames line up
- [FAQ.md](https://github.com/metrica-sports/more-than-a-hack-2027/blob/main/FAQ.md)

## Data

Not in git. Each person downloads `BAR-ATH_tactical_atd.txt`, `_atd.xml`, `_homography.csv` and `_smart_tagging.xml` from the organisers' Drive folder into `data/tactical/`.

Upstream: https://github.com/metrica-sports/more-than-a-hack-2027
