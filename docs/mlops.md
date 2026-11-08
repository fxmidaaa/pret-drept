# Pret-Drept MLOps

This branch builds a small, independent workflow on the July 2026 app at `e08344d`.
It preserves the HTTP interface, browser form and trusted July model loader.

| Acceptance criterion | Check |
| --- | --- |
| The safe workflow rebuilds from Git and skips unchanged stages | `dvc repro` twice and `dvc status --json` |
| Evaluation reloads the fitted serving bundle | Model and API tests with the DVC outputs |
| Tracking records a local run with parameters, metrics and lineage | MLflow read-back in CI |
| The inference image loads the demo bundle as non-root | Docker build and container smoke script |
| GitHub CI uses safe data and read-only permissions | `actionlint -shellcheck= -pyflakes=` |

The quality checks cover feature lineage (Q04), EUR evaluation and asking-rent semantics
(Q05–Q06), rebuild and reload (Q07), artifact boundaries and manual delivery (Q08–Q09),
and proportionate maintenance (Q12). Real chronological and property-disjoint evaluation
(Q01–Q02) requires a suitable authorized dataset. Capacity and operational or harness
benchmarking (Q03, Q10–Q11) are outside the demo.

## Lifecycle

| Component | Input | Output |
| --- | --- | --- |
| Prepare | Legacy-format listing CSV and split settings | `train.csv`, `evaluation.csv`, `dataset.json` |
| Train | `train.csv` and XGBoost settings | `model.joblib` with fitted defaults, encoder and model |
| Evaluate | Held-out CSV and the saved bundle | `evaluation.json` with EUR metrics and hashes |
| Track | Evaluation report and matching artifact identities | Local MLflow run and two JSON artifacts |
| Serve | The same trusted bundle | CLI example, FastAPI endpoints and browser UI |

Git stores source, settings, the generated input fixture and the DVC lock. DVC hashes stage
dependencies and outputs, caches generated demo files locally and reruns a stage when its inputs
change. A fresh checkout can rebuild from the Git fixture without a DVC remote or shared cache.
MLflow records the input and model SHA-256, the Git commit and dirty state observed at logging,
and the DVC lock SHA-256 for the demo. Track immediately after reproduction so those checkout
observations describe the run. Exact artifact bytes can vary by runtime and platform. Retain a
reviewed bundle and its hash when an exact restoration matters.

The legacy snapshot contains an EDA preview of individual listing features. This branch clears
the saved preview and keeps the notebook code. Historical commits retain their original content.

## Safe demo from a clean checkout

Use Git and Python **3.13.16** on macOS or glibc Linux. Install the native XGBoost dependency
with `brew install libomp` on macOS. Package installation needs a reachable package index.
The serving closure pins transitive Python versions. DVC, MLflow and the test tools use direct
pins. Tracking uses its own environment.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-mlops.txt
python -m pip check
python -m venv .venv-mlflow
.venv-mlflow/bin/python -m pip install -r requirements-tracking.txt

export DVC_NO_ANALYTICS=true MLFLOW_DISABLE_TELEMETRY=true
dvc repro
dvc repro
dvc status
.venv-mlflow/bin/python -m mlops.track artifacts/demo
python predict.py --model artifacts/demo/model.joblib
```

The 126 generated rows yield 101 training rows and 25 evaluation rows with the checked-in
settings. The first reproduction creates files under `artifacts/demo/`. The second should skip
all three stages. Read `artifacts/demo/evaluation.json` for MAE and RMSE in EUR per month. The
prediction prints the estimate, asking-price comparison and drivers. Demo scores cover generated data.

Open <http://127.0.0.1:5000> after starting the local UI. In **pret-drept-synthetic**, select the
printed run ID to see its parameters, metrics, tags, `dataset.json` and `evaluation.json`.

```bash
.venv-mlflow/bin/mlflow server --host 127.0.0.1 --port 5000 --workers 1 \
  --backend-store-uri "sqlite:///$PWD/.mlflow/mlflow.db" --no-serve-artifacts \
  --default-artifact-root "$PWD/.mlflow/artifacts"
```

Each explicit tracking command creates a run. DVC reproduction leaves the run history alone.
Keep the SQLite database and artifact directory together. After moving a checkout, use a new
store if the experiment refers to the old artifact path.

## Data contract and evaluation

Use a UTF-8 CSV with one Chișinău monthly rental listing per row. Required headers are
`price_value`, `price_unit`, `Număr de camere`, `Suprafață totală`, `Sector`, and
`Autorul anunțului` (author type). Prices must be numeric in `UNIT_EUR`, `UNIT_MDL`, or
`UNIT_USD`. The legacy fixed rates are 19.5 MDL per EUR and 0.92 EUR per USD. Optional
headers are in the [sample data guide](../data/sample/README.md). Supply a snapshot already
filtered to the target geography and rental period.

Preparation reuses the legacy parsers. It drops unusable currencies and prices, requires sector
and author type, and keeps the €100–€2,000 monthly rent segment, 10–400 m², and 1–6 rooms.
Optional listing text can supply condition, bathrooms, utility and finish flags. Prepared CSVs
contain model features and rent. IDs, coordinates, raw text and photo URLs are omitted. Invalid
floor pairs become missing.

The split uses seed 42 and holds out about 20% of groups. The key of sector, rooms, area, floor
and total floors keeps coarse repost matches together regardless of asking price. It requires at
least 20 distinct keys. Physical apartments can recur under changed attributes, and different
apartments may share a key. This is a same-snapshot development split. A real quality claim needs
reviewed property identity and later observations. The target is advertised rent.

The fit step reads the training CSV and settings. It fits numeric medians and one-hot categories
there. Fully missing optional numeric columns use fixed fallbacks in `train.py`. One CPU worker
fits XGBoost in log space. Evaluation and serving reuse the fitted preprocessing and convert the
output back to EUR. The new model omits the target-derived market-rate feature, exact geography
and photo counts. Asking price drives the response comparison only.

### Authorized private data

Place an authorized export at the ignored `data/raw/listings.csv` or pass its local path. Run
one pipeline process per output directory. Repeating commands replaces that run's generated
files. The committed DVC pipeline always reads the generated fixture.

The previous `python train.py` combined cleaning, fitting and evaluation. Use the commands below
for the same lifecycle with separate stages, then point serving at the resulting bundle.
Historical notebooks and the scraper can use `requirements.txt` in a separate environment.

```bash
python -m mlops.prepare data/raw/listings.csv artifacts/private
python train.py artifacts/private
python -m mlops.evaluate artifacts/private
.venv-mlflow/bin/python -m mlops.track artifacts/private --store artifacts/private/tracking
PRET_DREPT_MODEL=artifacts/private/model.joblib uvicorn api:app --host 127.0.0.1 --port 8000
```

Prepared private files still contain individual rows. A model can encode information about its
training data. Keep the snapshot, derived rows, model and tracking store private. Reproduce a
private run with the same source revision, settings, environment and input SHA-256. Use an
authorized private DVC project and storage if remote dataset restoration is required.

## Serve the demo

```bash
PRET_DREPT_MODEL=artifacts/demo/model.joblib uvicorn api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> or run the following in a second terminal.

```bash
curl --fail http://127.0.0.1:8000/options
curl --fail http://127.0.0.1:8000/predict -H 'Content-Type: application/json' \
  -d '{"rooms":2,"area":55,"floor":3,"total_floors":9,"sector":"centru","author":"agenție","price":700}'
```

The app keeps `/`, `/health`, `/options`, and `/predict`. Options come from fitted categories.
Omit `price` for an estimate without comparison. Legacy coordinate fields remain accepted.
The new bundle uses sector for location. Select a trusted July bundle with `PRET_DREPT_MODEL`
or use the existing root `model.joblib` default outside Docker. Restart after replacing the
bundle. `/health` checks liveness. `/options` and a prediction check model readiness. A missing
bundle produces HTTP 503.

## Docker and manual delivery

The image builds with a running Docker daemon. It contains inference code and CPU dependencies,
runs as UID 10001, and takes a read-only model mount. Joblib deserialization can execute code.
Mount only a trusted bundle.

```bash
docker build -t pret-drept:demo .
bash scripts/smoke_container.sh pret-drept:demo artifacts/demo/model.joblib
install -m 0644 artifacts/demo/model.joblib artifacts/demo/serving-model.joblib
docker run --rm --publish 127.0.0.1:8000:8000 \
  --mount "type=bind,source=$PWD/artifacts/demo/serving-model.joblib,target=/models/model.joblib,readonly" \
  pret-drept:demo
```

[CI](../.github/workflows/ci.yml) runs on push, pull request and manual dispatch where enabled.
It checks linting, tests, DVC reproduction and repeat behavior, CLI inference, MLflow logging
and read-back, and a Docker prediction with the same generated model. GitHub permissions are
read-only. Delivery to a host is manual.

1. Build and smoke-test the reviewed revision and trusted model on the target architecture.
   Record the Git SHA, image ID and model SHA-256.
2. When an authorized target is available, export with
   `docker save -o pret-drept-image.tar pret-drept:demo`. Transfer the image tar and reviewed
   bundle through the approved channel, verify checksums, and run `docker load -i pret-drept-image.tar`.
3. Start the image with the reviewed model mounted read-only. Grant only the runtime UID or
   group access to a private bundle. Check `/options` and an authorized prediction before
   switching traffic. Keep the previous image and model for rollback and rerun the checks
   after restoring them.

## Verification and troubleshooting

```bash
python -m ruff check mlops train.py predict.py api.py tests/test_workflow.py
python -m ruff format --check mlops train.py tests/test_workflow.py
PRET_DREPT_MODEL=artifacts/demo/model.joblib python -m pytest -q -ra
actionlint -shellcheck= -pyflakes=
bash -n scripts/smoke_container.sh
```

- Set `DVC_SITE_CACHE_DIR` to a writable path if the system cache is unavailable. Run
  `dvc repro --force --no-run-cache` for a fresh rebuild. It replaces the demo outputs.
- Install `libomp` if XGBoost fails to load OpenMP on macOS.
- For HTTP 503, check `PRET_DREPT_MODEL` and serving process read permissions. For Docker,
  confirm the mount target is `/models/model.joblib`.
- For missing MLflow runs, check that the UI and tracker use the same absolute SQLite path.
  Re-evaluate if tracking reports stale artifact identities.
- If `docker version` reports a missing socket, start or select the daemon, then build and
  run the smoke script.

### Local results

The reconstructed checkout used macOS ARM64, CPython 3.13.16, DVC 3.67.1 and generated data.

| Check | Result |
| --- | --- |
| `dvc repro`, repeated `dvc repro`, `dvc status --json` | Passed. Three stages built successfully, then all three skipped. Status was empty. |
| `PRET_DREPT_MODEL=artifacts/demo/model.joblib python -m pytest -q -ra` | 40 passed. Starlette emitted its httpx deprecation warning. |
| `python predict.py --model artifacts/demo/model.joblib` | Passed. The CLI returned a price, verdict and five drivers. Synthetic evaluation yielded €45.26 MAE and €58.93 RMSE. |
| Ruff, actionlint, `bash -n`, and frontend script via `node --check` | Passed. |
| `.venv-mlflow/bin/python -m mlops.track artifacts/demo` | Unavailable. MLflow is absent and PyPI could not be reached. Install `requirements-tracking.txt` on a connected machine, track the demo, then inspect the run in the UI. |
| `docker build -t pret-drept:demo .` and smoke script | Unavailable in this environment. Docker denied the daemon connection. Run the build and smoke script from a Docker-enabled environment. |
| Hosted CI, deployment and private-data runs | Skipped. Follow the prerequisites in the relevant sections for those separate checks. |
