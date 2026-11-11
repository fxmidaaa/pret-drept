# Pret-Drept simple MLOps

This branch starts from the July 2026 rent app. Keep the prediction API and browser form usable.
Use [docs/mlops.md](docs/mlops.md) for the data contract, stage commands and review criteria.

- `features.py` owns listing parsing and shared floor flags. `mlops/prepare.py` creates the split.
- `train.py` fits one XGBoost model on the training partition. `predict.py` owns bundle loading and
  transformation for evaluation, the CLI and the API. `mlops/track.py` records an evaluation.
- DVC versions the selected original snapshot in `data/dataset/` and runs on it by default.
  Use the checked-in synthetic CSV only for tests and CI. Keep real inputs, derived rows,
  model bundles, caches and tracking stores local. Load only trusted joblib artifacts.
- Track `data/dataset.dvc` and pipeline metadata in Git, never the raw CSV or snapshot contents.
  Keep CI read-only and use its explicit fixture commands without pulling private data. Publishing, scraping and
  deployment need separate authorization.
- Run `dvc repro`, its unchanged skip check, and `PRET_DREPT_MODEL=artifacts/real/model.joblib python -m pytest -q` after
  relevant changes. Run the guide's lint and tracking checks and exercise the container when
  Docker is available. Record unavailable checks and their recovery commands.
