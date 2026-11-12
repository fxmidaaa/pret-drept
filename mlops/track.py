"""Read an evaluation, log a new MLflow run, and optionally register its model."""

import argparse
import json
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path

import mlflow
from mlflow.models import ModelSignature

from mlops.models import model_artifact, model_type
from mlops.registry import local_client, register

ROOT = Path.cwd()  # Run tracking commands from the project root.


def track(directory: Path, store: Path, dataset_directory: Path | None = None) -> str:
    """Read reports, choose the experiment, and log one run with its saved predictor."""
    report_path = directory / "evaluation.json"
    report = json.loads(report_path.read_text())
    if dataset_directory is None:
        dataset_directory = (
            directory if (directory / "dataset.json").is_file() else directory.parent
        )
    dataset_path = dataset_directory / "dataset.json"
    dataset = json.loads(dataset_path.read_text())
    dataset_kind = report["dataset"]
    if (
        dataset_kind not in {"synthetic", "private"}
        or dataset_kind != dataset["dataset"]
    ):
        raise ValueError("Expected matching synthetic or private dataset reports.")

    client = local_client(store)
    experiment_name = f"pret-drept-{dataset_kind}"
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        artifact_dir = store.resolve() / "artifacts" / dataset_kind
        artifact_dir.mkdir(parents=True, exist_ok=True)
        experiment_id = client.create_experiment(
            experiment_name, artifact_location=artifact_dir.as_uri()
        )
    else:
        experiment_id = experiment.experiment_id

    parameters = report["parameters"]
    # Legacy XGBoost reports already nest model parameters; other reports are flat.
    if "model" not in parameters:
        parameters = {"model": parameters}
    parameters = {**parameters, "split": dataset["split"]}
    if "model_version" in report:
        parameters["library_version"] = report["model_version"]
    if "runtime" in report:
        parameters["runtime"] = report["runtime"]
    specification = model_artifact(report)
    model_kind = model_type(report)
    tags = {
        "dataset": dataset_kind,
        "model_type": model_kind,
        "model_ready": "true" if specification is not None else "false",
        "evaluation_sha256": dataset["evaluation_sha256"],
        **report.get("lineage", {}),
    }
    with mlflow.start_run(
        experiment_id=experiment_id,
        run_name=f"{model_kind} · {dataset_kind}",
        tags=tags,
    ) as run:
        mlflow.log_params(flatten_params(parameters))
        mlflow.log_artifact(str(report_path))
        mlflow.log_artifact(str(dataset_path))
        if specification is not None:
            info = log_model(directory, specification)
            mlflow.set_tags({"model_uri": info.model_uri, "model_id": info.model_id})
            mlflow.log_metrics(report["metrics"], model_id=info.model_id)
        else:
            mlflow.log_metrics(report["metrics"])
    return run.info.run_id


def flatten_params(values: dict, prefix: str = "") -> dict:
    """Turn nested settings into MLflow columns such as model.depth and split.seed."""
    result = {}
    for name, value in values.items():
        key = f"{prefix}.{name}" if prefix else name
        if isinstance(value, dict):
            result.update(flatten_params(value, key))
        else:
            if value is None or isinstance(value, (list, bool)):
                value = json.dumps(value, sort_keys=True)
            result[key] = value
    return result


def log_model(directory: Path, specification: dict):
    """Package weights, loader code and requirements without importing model libraries."""
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        bundle = work / "bundle"
        bundle.mkdir()
        packaged = {**specification, "files": {}}
        if not specification["files"]:
            raise ValueError("A registered predictor needs a saved model file.")
        for name, entry in specification["files"].items():
            if Path(name).name != name or name in {"", ".", "..", "model.json"}:
                raise ValueError("Model artifact names must be plain filenames.")
            source = directory / entry["path"]
            if sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Model artifact {name} changed after evaluation.")
            shutil.copy2(source, bundle / name)
            packaged["files"][name] = {**entry, "path": name}
        (bundle / "model.json").write_text(
            json.dumps(packaged, indent=2), encoding="utf-8"
        )

        # Preserve package folders so the exported loader also works outside this repo.
        code = work / "code"
        code.mkdir()
        for relative in specification.get("code_paths", []):
            source = (ROOT / relative).resolve()
            if not source.is_relative_to(ROOT) or not source.is_file():
                raise ValueError(
                    "code_paths must name source files inside the repository."
                )
            destination = code / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        signature = specification.get("signature")
        # PyFunc imports NumPy and pandas even for a custom predictor with no
        # additional dependencies. Preserve any model-specific version pins.
        requirements = [
            f"mlflow-skinny=={mlflow.__version__}",
            *specification["requirements"],
        ]
        for package in ("numpy", "pandas"):
            if not any(item.split("==", 1)[0] == package for item in requirements):
                requirements.append(package)
        return mlflow.pyfunc.log_model(
            name="model",
            loader_module=specification["loader_module"],
            data_path=str(bundle),
            code_paths=[str(path) for path in sorted(code.iterdir())],
            # The inference-only package also supports the model environments'
            # pandas versions, while the full MLflow server requires pandas < 3.
            pip_requirements=requirements,
            metadata={"target_unit": "EUR/month"},
            signature=ModelSignature.from_dict(signature) if signature else None,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record evaluated models in local MLflow."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--dataset-dir", type=Path, help="Directory containing the shared dataset.json."
    )
    parser.add_argument("--store", type=Path, default=Path(".mlflow"))
    parser.add_argument(
        "--register", action="store_true", help="Also register the saved predictor."
    )
    args = parser.parse_args()
    run_id = track(args.directory, args.store, args.dataset_dir)
    if args.register:
        version = register(run_id, args.store)
        print(f"{run_id} models:/{version.name}/{version.version}")
    else:
        print(run_id)


if __name__ == "__main__":
    main()
