# Local MLOps workflow

This branch runs on your machine. Each stage is an ordinary Python command:

| Step | Code | Result |
| --- | --- | --- |
| Clean and split | `mlops/prepare.py`, using `features.py` | `train.csv`, `evaluation.csv`, `dataset.json` |
| Train | `train.py` | `model.joblib`, with the fitted encoder and numeric defaults |
| Evaluate | `mlops/evaluate.py`, using `predict.py` | `evaluation.json` with EUR metrics and file hashes |
| Track | `mlops/track.py` | A local MLflow run with settings, metrics and the two JSON reports |
| Predict | `predict.py`, `api.py`, `mlops/batch.py` | CLI, browser/API or PySpark predictions |

The small `config.py` and `files.py` helpers validate settings and handle file hashes and writes.
The scraper also uses `files.py` so an interrupted checkpoint write does not destroy a crawl.
There is no pipeline framework or deployment service to run.

## Setup

Use Python **3.13.16**. On macOS, install `libomp` with Homebrew for XGBoost.
Keep MLflow in its own environment to avoid dependency conflicts with DVC and serving.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-mlops.txt
python -m pip check
python -m venv .venv-mlflow
.venv-mlflow/bin/python -m pip install -r requirements-tracking.txt
export DVC_NO_ANALYTICS=true MLFLOW_DISABLE_TELEMETRY=true
```

## Authorized private data

Use a completed snapshot's `listings.csv`. Replace `<run-id>` below with its directory name.
Choose a separate output directory for each experiment; rerunning a stage replaces its outputs.

```bash
SNAPSHOT="data/raw/snapshots/<run-id>/listings.csv"
RUN="artifacts/private/<run-id>"
python -m mlops.prepare "$SNAPSHOT" "$RUN"
python train.py "$RUN"
python -m mlops.evaluate "$RUN"
.venv-mlflow/bin/python -m mlops.track "$RUN" --store "$RUN/tracking"
PRET_DREPT_MODEL="$RUN/model.joblib" uvicorn api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> for the form. CLI prediction uses
`python predict.py --model "$RUN/model.joblib"`. Existing private runs and model files remain
usable; the bundle format is unchanged. Only load trusted joblib files: loading executes Python code.
Keep raw data, prepared rows, models and tracking stores local. They are ignored by Git.
To repeat a private experiment, retain its source CSV, settings, code revision and environment.

## DVC demo

The checked-in DVC pipeline stays fixed to `data/sample/demo.csv`, which contains generated data.
A fresh checkout and CI can therefore reproduce it without distributing private listings.

```bash
dvc repro
dvc repro
dvc status
```

DVC runs prepare, train and evaluate in order, records their file identities in `dvc.lock`, and
caches outputs locally. Changing a dependency or parameter reruns the affected stages. A second
unchanged run skips all three. The fixture produces 101 training rows and 25 evaluation rows in
`artifacts/demo/`. Its scores check the workflow, not real-market prediction quality.

## Data contract and evaluation

Input is a UTF-8 CSV of Chișinău monthly rentals. Required columns are `price_value`, `price_unit`,
`Număr de camere`, `Suprafață totală`, `Sector` and `Autorul anunțului`.
The [sample guide](../data/sample/README.md) lists optional fields.

- Prices accept EUR, MDL and USD using the legacy fixed rates: 19.5 MDL/EUR and 0.92 EUR/USD.
  Unknown currencies and invalid prices are discarded.
- Cleaning keeps rents of €100–€2,000, areas of 10–400 m² and 1–6 rooms, with known sector and
  author type. Missing optional fields are allowed. Invalid floor pairs become missing.
- The split keeps rows sharing sector, rooms, area, floor and total floors together. It needs
  at least 20 distinct groups. Seed 42 holds out roughly 20% of groups.
- Numeric medians and categories are fitted on training rows only. XGBoost fits `log1p(price)`;
  evaluation and every prediction path reuse the saved preprocessing and model.
- Prepared files omit IDs, coordinates, photos and raw text. Asking rent is used for evaluation
  and the API comparison, never as a model input.

This is a same-snapshot development split. Similar attributes are only a rough repost key,
not verified apartment identity. Chronological evaluation requires later observations.
The target is advertised rent. Historical notebooks retain their older preprocessing and model
comparisons; they are not the current MLOps pipeline.

## MLflow

Tracking is explicit: `dvc repro` does not create MLflow runs. Track immediately after evaluation.
Each invocation creates one run and checks that the model and dataset still match the report.

```bash
.venv-mlflow/bin/python -m mlops.track artifacts/demo
.venv-mlflow/bin/mlflow server --host 127.0.0.1 --port 5000 --workers 1 \
  --backend-store-uri "sqlite:///$PWD/.mlflow/mlflow.db" --no-serve-artifacts \
  --default-artifact-root "$PWD/.mlflow/artifacts"
```

Open <http://127.0.0.1:5000>. Experiments are `pret-drept-synthetic` and `pret-drept-private`.
For the private run above, use `$PWD/$RUN/tracking/mlflow.db` as the UI database and
`$PWD/$RUN/tracking/artifacts` as its artifact root. Keep the database and artifacts together.
If moving a store invalidates its recorded artifact paths, choose a new store.

Runs contain settings, MAE/RMSE, row counts, input/model hashes, `dataset.json` and
`evaluation.json`. Git revision, dirty state and the demo's DVC lock are observations at logging
time. The trained model stays in its run directory; tracking does not upload it.

## Docker and batch prediction

One image contains Python, Java, the API and PySpark. The default command starts the API;
override it for batch prediction. It runs as UID 10001, with data and models mounted at runtime.
Java makes it larger than an API-only image, but avoids maintaining separate builds.

```bash
docker build -t pret-drept:local .
bash scripts/smoke_container.sh pret-drept:local artifacts/demo/model.joblib
install -m 0644 artifacts/demo/model.joblib artifacts/demo/serving-model.joblib
docker run --rm --publish 127.0.0.1:8000:8000 \
  --mount "type=bind,source=$PWD/artifacts/demo/serving-model.joblib,target=/models/model.joblib,readonly" \
  pret-drept:local
```

For a private model, mount its path instead. The container user needs read access to that file;
use a dedicated serving copy with suitable permissions if necessary.

Batch input uses prepared feature names (`rooms`, `area`, `sector`, `author`, etc.), not raw scraper
columns. Output CSV parts contain the input features and `predicted_rent_eur`, preserve
`listing_key` when supplied, and omit target price. Existing output directories are refused.

```bash
install -m 0644 artifacts/demo/evaluation.csv artifacts/demo/batch-input.csv
docker run --name pret-drept-batch \
  --mount "type=bind,source=$PWD/artifacts/demo/serving-model.joblib,target=/models/model.joblib,readonly" \
  --mount "type=bind,source=$PWD/artifacts/demo/batch-input.csv,target=/data/input.csv,readonly" \
  pret-drept:local python -m mlops.batch --input /data/input.csv --output /tmp/predictions
docker cp pret-drept-batch:/tmp/predictions artifacts/demo/batch-predictions
docker rm pret-drept-batch
```

Without Docker, install `requirements-batch.txt` in `.venv` and Java 17, then run
`python -m mlops.batch --input "$RUN/evaluation.csv" --model "$RUN/model.joblib" --output "$RUN/predictions"`.
Spark uses two local workers and the same model as the API. A `_SUCCESS` file marks completed
output. If a batch fails, remove its incomplete output directory before retrying.

## Collect a private snapshot

Scraping is a separate, explicit action:

```bash
python scrape.py --limit 100
python scrape.py
python scrape.py --resume "<run-id>"
```

The default cap is 6,000 unique ads checked, including unavailable and out-of-scope ads.
A fresh run writes `data/raw/snapshots/<run-id>/`. Use the CSV only when `snapshot.json` says
`complete`. The manifest records counts, the crawl window and the CSV hash. `observed_at` is
collection time, not publication time. Resume within the intended observation window; an
interrupted run keeps its original cap and checkpoint.

## Checks

```bash
python -m ruff check mlops *.py tests
python -m ruff format --check mlops train.py tests/test_workflow.py
dvc repro
dvc repro
dvc status --json
PRET_DREPT_MODEL=artifacts/demo/model.joblib python -m pytest -q -ra
python predict.py --model artifacts/demo/model.joblib
actionlint -shellcheck= -pyflakes=
bash -n scripts/smoke_container.sh
```

[GitHub Actions](../.github/workflows/ci.yml) performs the fixture-based checks, reads back an MLflow
run, then tests API and Spark predictions in the Docker image. Its permissions are read-only.
It does not publish images, scrape, deploy, or transfer private data.

For HTTP 503, check `PRET_DREPT_MODEL` and model permissions. `/health` reports liveness;
`/options` and `/predict` check readiness. Restart the API after replacing its model.
If DVC cannot write its system cache, set `DVC_SITE_CACHE_DIR` to a writable directory.

Local verification passed: 46 tests, Ruff, DVC rebuild and skip checks, and MLflow read-back.
The generated fixture and existing real snapshot produced the same prepared CSV bytes, split
manifests, predictions and EUR metrics as before the simplification.

Docker/Spark integration could not run in this session because daemon access was denied and the
host has no Java runtime. Run the build and smoke commands above on a Docker-enabled host.
The smoke script checks both API and actual Spark execution. Actionlint was not installed;
rerun its command above once it is available. Workflow YAML and shell syntax were checked locally.
