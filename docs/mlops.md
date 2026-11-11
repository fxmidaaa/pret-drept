# Local MLOps workflow

This branch runs on your machine. Each stage is an ordinary Python command:

| Step | Code | Result |
| --- | --- | --- |
| Select original input | `mlops/dataset.py` | Verified copy in `data/dataset/`, then `dvc add` records its version |
| Clean and split | `mlops/prepare.py`, using `features.py` | `train.csv`, `evaluation.csv`, `dataset.json` |
| Train | `train.py` | `model.joblib`, with the fitted encoder and numeric defaults |
| Evaluate | `mlops/evaluate.py`, using `predict.py` | `evaluation.json` with EUR metrics and file hashes |
| Track | `mlops/track.py` | A local MLflow run, evaluated model artifacts and optional registry version |
| Predict | `predict.py`, `api.py`, `mlops/batch.py` | CLI, browser/API or PySpark predictions |

DVC runs preparation, training and evaluation in order. Tracking and prediction are separate
commands. Each script can also run directly. `params.json` holds the split and model settings;
CSV, joblib and JSON files connect the stages.

When reading the code, start with `prepare()`, `train()`, `evaluate()`, `track()` and
`score_csv()`. Each file's `main()` just reads command-line arguments and calls that function.
In `track.py`, the run's workflow comes first; the helpers below flatten nested parameters
and package the saved predictor for MLflow. The small predictor classes in `models.py` give
MLflow its required `predict()` method and reuse the existing feature preparation.

Preparation reads the local CSV directly, then saves only the prepared feature columns and
target. Batch prediction selects the saved model's features, scores Pandas batches with the
shared functions in `predict.py`, and adds `predicted_rent_eur` to the output. Neither path
saves raw ad text or identifiers; batch output can retain an explicit `listing_key` for
matching predictions.

Run preparation, evaluation and tracking from the project root. They use the local
`params.json`, `requirements.txt` and source files directly. Exported predictors still load
from their packaged files and can run outside the repository.

Generated outputs are unlinked before writing to protect DVC's cached copies. Dataset selection
and scraper checkpoints use temporary files followed by replacement. Keep these few filesystem
operations when changing a stage: writing through a DVC cache link can corrupt an older version.

## Setup

Use Python **3.13.16**. On macOS, install `libomp` with Homebrew for XGBoost.
The main workflow uses one virtual environment and one requirements file.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

`requirements.txt` contains the API, training, DVC, MLflow, PySpark, plotting and test
dependencies. Pandas is pinned to **2.3.3**, which satisfies MLflow 3.14's `pandas<3`
requirement. Docker and CI install the same file. Indirect dependencies are resolved by pip.

| Environment | Use |
| --- | --- |
| `.venv` | All commands in this guide, including the MLflow server, tracking and registry |
| `.venv-catboost` | Existing CatBoost experiments with their original package versions |
| `.venv-tabpfn` | Existing TabPFN experiments, including PyTorch and their original package versions |

The optional model environments preserve earlier experiments. Their NumPy/pandas versions differ
from the main environment; consolidate them only after checking saved-model loading and predictions.
The shared MLflow store works independently of which environment trained a model.
See the [directory map](../README.md#whats-where) for source files and generated local folders.

## Configuration

Create `.env` once if it is missing, then edit it for your machine. It is ignored by Git and
excluded from Docker builds. Keep your existing settings when updating the project.

```bash
test -f .env || cp .env.example .env
```

At the start of each terminal session, run these commands from the project root:

```bash
source .venv/bin/activate
set -a
source .env
set +a
```

`set -a` exports the file's assignments to subsequent commands. Python does not read `.env`
automatically. Inline environment assignments and explicit CLI arguments can still override
settings for one command.

| Setting | Location | Meaning |
| --- | --- | --- |
| `PRET_DREPT_MODEL` | `.env` | Local trusted bundle; the example selects `artifacts/real/model.joblib` |
| `PRET_DREPT_TABPFN_DEVICE` | Optional in `.env` | `auto`, `cpu` or `mps` for saved TabPFN inference |
| `DVC_NO_ANALYTICS`, `MLFLOW_DISABLE_TELEMETRY` | `.env` | Disable tool telemetry |
| Seed, evaluation fraction and model hyperparameters | `params.json` | Versioned training inputs, read directly by preparation and training |
| Python logging, Matplotlib cache and Spark address | Dockerfile | Defaults needed by the container runtime |
| MLflow store | `--store PATH` | Optional override of the existing `.mlflow` default |

MLflow telemetry is configured by `.env` locally and by the CI environment.

Docker uses `/models/model.joblib` inside the image. Keep the local `.env` in the terminal;
passing it to `docker run --env-file` would replace that path with a host-relative one.

## Daily workflow

With the original dataset already selected, run:

```bash
dvc repro
python -m mlops.track artifacts/real --register
uvicorn api:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> for the form. DVC runs preparation, training and evaluation;
tracking is explicit, and the last command serves the bundle selected in `.env`.
For a single CLI example, run `python predict.py`. Existing commands such as
`python predict.py --model artifacts/real/model.joblib` also work.
See [MLflow](#mlflow-tracking-and-local-model-registry) to open the comparison UI and
[Docker and batch prediction](#docker-and-batch-prediction) for container commands.

## Select or restore a dataset

The default DVC pipeline uses the original scraped data, not the synthetic fixture.
Select a completed snapshot and add the current input directory to DVC:

```bash
python -m mlops.dataset data/raw/snapshots/<run-id>
dvc add data/dataset
dvc repro
```

The selection command validates the scraper's completion status, CSV SHA-256 and row count
before replacing the current input. It copies the original CSV and snapshot manifest byte for
byte into `data/dataset/`; the scraper archive remains unchanged. Atomic file replacement
avoids modifying any file linked to DVC's cache in place.

DVC versions the two original input files together through `data/dataset.dvc`.
The root `dvc.yaml` prepares that CSV, trains XGBoost, and evaluates it in
`artifacts/real/`. Preparation also verifies the selected snapshot manifest.
Derived CSVs, the model bundle and evaluation report are cached and identified in `dvc.lock`.
A second unchanged run skips the stages.

| Item | Git | DVC cache / local workspace |
| --- | --- | --- |
| `data/dataset.dvc`, `dvc.yaml`, `dvc.lock` | Metadata, hashes and pipeline commands | — |
| `data/dataset/listings.csv`, `data/dataset/snapshot.json` | Ignored | Original private input |
| `artifacts/real/` stage outputs | Ignored | Prepared rows, model and report |
| `data/raw/snapshots/` | Ignored | Original scraper archive |

Review and commit the DVC metadata together with the matching code and parameters to record a
version in Git. The CSV contents never need to enter Git. To select a newer dataset, repeat
the selection, `dvc add data/dataset` and `dvc repro` commands. The pointer changes to the new
directory hash while the previous version remains in the local cache.

To restore the selected raw dataset from an existing local cache:

```bash
dvc checkout data/dataset.dvc
```

To return to an earlier project version, first select its Git revision in a clean working
tree, then run `dvc checkout` to restore its cached input and outputs. Keep any uncommitted
work before changing revisions. No DVC remote is configured: sharing or restoring data on a
different machine requires a separate private storage configuration. Back up the local DVC
cache if it is your only copy of earlier dataset versions.

Existing private experiment directories and bundles remain usable. To run an independent
experiment without replacing the DVC pipeline's outputs, use a separate local directory:

```bash
RUN="artifacts/private/<experiment>"
python -m mlops.prepare data/dataset/listings.csv "$RUN" --snapshot data/dataset/snapshot.json
python train.py "$RUN"
python -m mlops.evaluate "$RUN"
python -m mlops.track "$RUN" --register
```

Load only trusted joblib files: loading can execute Python code.

## Test fixture and CI

`data/sample/demo.csv` is a small generated test fixture. It is not the source of the
default DVC pipeline. CI validates the DVC metadata without downloading private data, then
runs the same Python stage implementations directly against this fixture:

```bash
dvc stage list --all --fail
python -m mlops.prepare data/sample/demo.csv artifacts/demo --synthetic
python train.py artifacts/demo
python -m mlops.evaluate artifacts/demo
PRET_DREPT_MODEL=artifacts/demo/model.joblib python -m pytest -q
```

This creates 101 training rows and 25 evaluation rows in `artifacts/demo/` for tests.
These synthetic scores check code behavior; they do not measure market prediction quality.
The real-data DVC reproduction is checked locally where the private input is available.

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

## MLflow tracking and local model registry

Tracking and registration are explicit; DVC still runs prepare, train and evaluate only.
All algorithms use the same local store by default, with separate experiments and registered
model names for synthetic and private data.

```bash
mlflow server --host 127.0.0.1 --port 5000 --workers 1 \
  --backend-store-uri "sqlite:///$PWD/.mlflow/mlflow.db" --no-serve-artifacts \
  --default-artifact-root "$PWD/.mlflow/artifacts"
```

Open <http://127.0.0.1:5000>. In **Experiments**, select `pret-drept-private` for real data
or `pret-drept-synthetic` for the fixture. Select runs and click **Compare** to inspect
`mae_eur`, `rmse_eur`, parameters and tags. Useful columns are `model_type`, `model_ready`,
`model.*`, `split.*`, `dataset_sha256` and `evaluation_sha256`.

These are aggregate scores on held-out advertised rents, not live production monitoring.
Compare models on the same evaluation partition and target definition. A later real snapshot
needs a fresh evaluation and tracking invocation to add new results.

For previously evaluated private experiments, set RUN to the directory containing
`dataset.json` and use the same default store:

```bash
python -m mlops.track "$RUN" --register
python -m mlops.track "$RUN/catboost" --register
python -m mlops.track "$RUN/tabpfn"
```

Here RUN is an existing experiment directory; the last two commands apply when those
benchmark directories exist. A child directory finds its parent's dataset manifest
automatically; `--dataset-dir PATH` handles other layouts.
Existing reports are read without rewriting their results. Earlier per-experiment tracking
databases remain usable; recording reports in the common store does not move or delete them.
An explicit `--store PATH` still selects an independent local store.

Each run contains:

- The original `dataset.json` and `evaluation.json`, metrics and generic model parameters.
- Algorithm and library version when supplied, split settings, hashes, and reported runtime.
- A complete MLflow PyFunc model when the evaluation declares saved model artifacts. The model
  includes weights/bundle, preprocessing, a snapshot of its loader code, and requirements.
- `model_ready=false` for a score-only benchmark. Such a run can be compared in the UI but
  cannot be registered until a fitted predictor has actually been saved.

`track` reads the reports, selects an experiment, and logs parameters, metrics and artifacts.
`log_model` copies a complete predictor and its inference code into MLflow without loading
the model in the tracking environment. Files are checked against their evaluated hashes once,
when packaging them. Export and loading use those saved copies.

Every tracking call creates a new run, even for an unchanged report. Every registration
creates a new version. The evaluation split hash identifies runs evaluated on the same partition.

Keep preparation, training and evaluation together through `dvc repro`. Independent experiment
reports are trusted when logging: changing a manifest after evaluation is no longer detected
by a second set of dataset hash checks in the tracker.

Keep the SQLite database and its artifact directory together at their recorded absolute paths.
To back up the store, stop the local server/writers and copy the whole `.mlflow` directory.
Model dependencies describe the inference environment. New XGBoost packages select the prediction
libraries from `requirements.txt`; API, DVC, Spark and test tools stay in the project environment.
Existing registered versions retain their original requirements and packaged source.

### Versions, aliases and export

In **Models / Registered Models**, open `pret-drept-private` or `pret-drept-synthetic`.
Versions link to their source runs and can have aliases and tags. Different algorithms can
share a registered name when they implement the same input and EUR output contract.
Synthetic and private versions use separate registered names. Registration never automatically
changes the working model.

```bash
python -m mlops.registry list pret-drept-private
python -m mlops.registry alias pret-drept-private 1 champion
python -m mlops.registry export pret-drept-private \
  --alias champion --output artifacts/selected
```

Use an existing version from the list. Reassigning `champion` to an earlier version is a rollback.
Export resolves an alias once, pins the numeric version, copies the saved model and writes
`registry.json` recording that selection. Existing output directories are refused.
Use `--version N` instead of `--alias` to select an explicit version.
The registry's global `--store PATH` option goes before the subcommand.

An exported XGBoost model also contains the original bundle usable by the CLI, API and Docker:

```bash
python predict.py --model artifacts/selected/data/bundle/model.joblib
PRET_DREPT_MODEL=artifacts/selected/data/bundle/model.joblib \
  uvicorn api:app --host 127.0.0.1 --port 8000
```

Restart the API after selecting another bundle. Its browser categories and SHAP explanations
currently use the XGBoost bundle interface. CatBoost and saved TabPFN predictors use the MLflow
PyFunc adapters; their runtime needs the model's requirements. In such an environment,
`mlflow.pyfunc.load_model("models:/pret-drept-private/N").predict(feature_frame)` returns EUR
predictions. Exported model directories also support `mlflow.pyfunc.load_model(local_path)`.
Changing a registry alias alone does not replace a model already loaded by an application.

### Add another algorithm

The common evaluation report has `dataset`, `model_type`, `parameters`, `metrics` and
`lineage.dataset_sha256`. Parameters may be nested dictionaries; they become `model.*`
columns. Split settings are read from the dataset manifest, independently of the
algorithm. Existing XGBoost reports with nested model settings remain supported.

For a saved predictor, add `model_artifact` to that report:

```json
{
  "loader_module": "custom.loader",
  "files": {
    "weights.bin": {"path": "weights.bin", "sha256": "<evaluated-file-hash>"},
    "preprocessing.json": {"path": "preprocessing.json", "sha256": "<evaluated-file-hash>"}
  },
  "code_paths": ["custom/__init__.py", "custom/loader.py"],
  "requirements": ["my-model-library==1.2.3"]
}
```

File paths are relative to the evaluation directory; absolute local paths are also accepted.
Artifact names are plain filenames. List every file needed to reproduce inference and its
evaluated hash. Code paths name individual repository source files; their package structure
is preserved. The loader implements `_load_pyfunc(data_path)` and returns an object with
`predict(feature_frame)`. It can read the packaged `model.json` for metadata, and it must
produce the advertised EUR output. An optional `signature` uses MLflow's serialized
ModelSignature format. No algorithm-specific branch is required in `track.py`.
An explicit `"model_artifact": null` records only results.

The project supplies loaders for its XGBoost bundles, native CatBoost models, and fitted
TabPFN 9.2.0 state. Existing XGBoost/CatBoost reports are recognized for compatibility.
Model libraries are imported only when loading their format. Joblib is imported inside
`load_bundle()` so native CatBoost inference can reuse the feature builder without it.
The historical TabPFN benchmark saved scores and a foundation checkpoint, not the fitted
estimator. Its results are tracked, but that checkpoint alone is not a registry version.

For future TabPFN evaluations, save the estimator immediately after scoring, while it is
still in memory in `.venv-tabpfn`:

```python
import json

from mlops.models import save_tabpfn_artifact

report["model_artifact"] = save_tabpfn_artifact(model, output_directory, checkpoint, report)
report_path = output_directory / "evaluation.json"
report_path.unlink(missing_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
```

The report needs its existing preprocessing, target transform and evaluated checkpoint hash.
The helper saves fitted state and declares both that state and the checkpoint as model files.
Its inference requirements are explicitly pinned in `save_tabpfn_artifact` to the existing
`.venv-tabpfn` versions. Update those pins if that environment changes; no installed-package
version discovery runs when saving the model.
Then run the ordinary tracking command with `--register`. The packaged TabPFN loader relocates
the checkpoint reference; `PRET_DREPT_TABPFN_DEVICE=cpu` (or `mps`) overrides its automatic
device selection. Load only trusted model packages and fitted states.

## Docker and batch prediction

One image contains Python, Java, the API and PySpark. The default command starts the API;
override it for batch prediction. It runs as UID 10001, with data and models mounted at runtime.
Java makes it larger than an API-only image, but avoids maintaining separate builds.
The Dockerfile installs dependencies first, then uses `COPY . .`. The `.dockerignore`
allowlist limits that copy to the API, batch code and their runtime files.

The container smoke script uses `.venv/bin/python` for validation on the host, or `python3`
in CI where `.venv` is absent. It checks host imports before starting the container, so the local
environment does not need to be activated separately.

```bash
docker build -t pret-drept:local .
bash scripts/smoke_container.sh pret-drept:local artifacts/real/model.joblib
install -m 0644 artifacts/real/model.joblib artifacts/real/serving-model.joblib
docker run --rm --publish 127.0.0.1:8000:8000 \
  --mount "type=bind,source=$PWD/artifacts/real/serving-model.joblib,target=/models/model.joblib,readonly" \
  pret-drept:local
```

For a private model, mount its path instead. The container user needs read access to that file;
use a dedicated serving copy with suitable permissions if necessary.

Batch input uses prepared feature names (`rooms`, `area`, `sector`, `author`, etc.), not raw scraper
columns. Output CSV parts contain the input features and `predicted_rent_eur`, preserve
`listing_key` when supplied, and omit target price. Existing output directories are refused.

```bash
install -m 0644 artifacts/real/evaluation.csv artifacts/real/batch-input.csv
docker run --name pret-drept-batch \
  --mount "type=bind,source=$PWD/artifacts/real/serving-model.joblib,target=/models/model.joblib,readonly" \
  --mount "type=bind,source=$PWD/artifacts/real/batch-input.csv,target=/data/input.csv,readonly" \
  pret-drept:local python -m mlops.batch --input /data/input.csv --output /tmp/predictions
docker cp pret-drept-batch:/tmp/predictions artifacts/real/batch-predictions
docker rm pret-drept-batch
```

Without Docker, install `requirements.txt` in `.venv` and Java 17, then run
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
python -m ruff format --check mlops *.py tests
dvc repro
dvc repro
dvc status --json
python -m mlops.prepare data/sample/demo.csv artifacts/demo --synthetic
python train.py artifacts/demo
python -m mlops.evaluate artifacts/demo
PRET_DREPT_MODEL=artifacts/real/model.joblib python -m pytest -q -ra
python predict.py --model artifacts/real/model.joblib
actionlint -shellcheck= -pyflakes=
bash -n scripts/smoke_container.sh
```

[GitHub Actions](../.github/workflows/ci.yml) validates DVC metadata, runs fixture-based stage checks,
checks MLflow read-back and registry behaviour through `tests/test_registry.py`, exercises
the tracking CLI, then tests API and Spark predictions in the Docker image.
It does not reproduce the private-data DVC pipeline. Its permissions are read-only.
It does not publish images, scrape, deploy, or transfer private data.

For HTTP 503, check `PRET_DREPT_MODEL` and model permissions. `/health` reports liveness;
`/options` and `/predict` check readiness. Restart the API after replacing its model.
If DVC cannot write its system cache, set `DVC_SITE_CACHE_DIR` to a writable directory.

Registry tests use a temporary SQLite store and verify tracking, registration, aliases, rollback,
export and predictions from packaged source outside the repository. They also cover custom loaders
and score-only benchmarks. They use `.venv` and leave the normal `.mlflow` history unchanged.

To exercise the tracking CLI separately without adding runs to the normal store:

```bash
CHECK_STORE=$(mktemp -d)
python -m mlops.track artifacts/demo --store "$CHECK_STORE" --register
```

If DVC cannot access its system cache in a restricted session, retry with:

```bash
DVC_SITE_CACHE_DIR="${TMPDIR:-/tmp}/pret-drept-dvc" dvc repro
```

Docker needs access to the local daemon. If that access is unavailable, run the build and
container smoke commands above in a Docker-enabled terminal. Java 17 is required to run Spark
outside the image; the container includes it. On macOS, install a missing actionlint with
`brew install actionlint`, then rerun `actionlint -shellcheck= -pyflakes=`.

## Local cleanup

Python bytecode, `.pytest_cache/`, `.ruff_cache/` and disposable `artifacts/checks/` outputs can
be recreated. Use temporary directories for one-off checks so they do not accumulate in the project.
Keep `artifacts/demo/` when running tests directly; the fixture stage commands recreate it.

Preserve `.dvc/cache/`, `.mlflow/`, original snapshots, experiment results and model checkpoints.
The older `artifacts/private/.../tracking/` directories are also MLflow stores. Their recorded
artifact paths are absolute, so keep those stores and their artifacts at their existing locations.
