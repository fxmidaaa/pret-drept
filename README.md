# Pret-Drept

Estimate monthly apartment rent in Chișinău, compare it with an asking price, and explain
the prediction through a browser form or HTTP API. The local MLOps pipeline prepares one
dataset and trains and evaluates XGBoost, CatBoost and TabPFN on the same split.

Start with the [local workflow guide](docs/mlops.md) for environment setup, selecting data,
DVC, MLflow, Docker and batch prediction. The [July 2026 analysis](docs/history.md) records
the original project, market charts and model comparison.

## Run locally

After following the guide's setup and selecting a completed local snapshot, run these commands
from the project root:

```bash
source .venv/bin/activate
test -f .env || cp .env.example .env
set -a
source .env
set +a
dvc repro evaluate
uvicorn api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> for the form. `.env` selects the trusted XGBoost bundle at
`artifacts/real/model.joblib`. `params.json` contains training settings.

Use `dvc repro evaluate_catboost` or `dvc repro evaluate_tabpfn` for another algorithm.
`dvc repro` considers all three and requires the two model environments and the local
TabPFN checkpoint. Tracking is explicit:

```bash
python -m mlops.track artifacts/real --register
```

## Project map

| Path | Purpose |
| --- | --- |
| `api.py`, `app/` | HTTP API and browser form |
| `predict.py`, `features.py` | Shared prediction, listing parsing and feature rules |
| `train.py` | XGBoost training entry point |
| `mlops/` | Dataset selection, preparation, training, evaluation, tracking, registry and Spark batch commands |
| `dvc.yaml`, `dvc.lock`, `data/dataset.dvc` | Pipeline and data version metadata |
| `params.json`, `.env.example` | Training configuration and local runtime template |
| `data/sample/demo.csv` | Synthetic input fixture for tests and CI; see the [column guide](data/sample/README.md) |
| `tests/` | Tests that build their synthetic models in temporary directories |
| `scripts/`, `.github/workflows/` | Container smoke check and read-only CI |
| `requirements.txt`, `Dockerfile`, `.dockerignore` | Main Python environment and API/Spark image |
| `scrape.py` | Explicit collection of dated snapshots |
| `docs/mlops.md` | Current setup, commands, data contract and checks |
| `docs/history.md`, `docs/images/`, `notebooks/` | Historical analysis, its illustrations and notebooks |

Generated local files have separate roles and stay outside Git:

```text
data/
  raw/snapshots/<run-id>/       original scraper archive
  dataset/                      selected original input for DVC
artifacts/
  real/                         current DVC split, models and evaluations
    catboost/
    tabpfn/
  checkpoints/                  pretrained TabPFN weights
  experiments/<experiment>/     previous or independent experiment results
.mlflow/                        shared tracking database and packaged model versions
.venv/                          main Python environment
.venv-catboost/                  CatBoost environment
.venv-tabpfn/                    TabPFN environment
.dvc/cache/                     cached data and pipeline versions
```

Both `real/` and `experiments/` contain private results. Tests and one-off checks use temporary
directories, so no persistent `artifacts/demo/` is required. Keep MLflow stores with their
artifacts at their recorded paths, and preserve the DVC cache and original snapshots.

## Checks

```bash
python -m ruff check mlops *.py tests
python -m ruff format --check mlops *.py tests
python -m pytest -q
```

Pytest creates its own fixture model; it does not require a dataset or a prebuilt demo directory.
Set `PRET_DREPT_MODEL=artifacts/real/model.joblib` to additionally check the current real-data
XGBoost evaluation and API. Optional CatBoost and TabPFN integration tests use their own
environments. The guide lists the full [DVC, tracking and container checks](docs/mlops.md#checks).
