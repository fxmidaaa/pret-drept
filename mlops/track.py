import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from mlops.files import sha256, write_json
from mlops.models import model_artifact, model_type, verify_files

ROOT = Path(__file__).resolve().parents[1]


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(ROOT), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def local_client(store: Path):
    os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
    import mlflow

    store = store.resolve()
    store.mkdir(parents=True, exist_ok=True)
    uri = f"sqlite:///{store / 'mlflow.db'}"
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    return mlflow.MlflowClient(tracking_uri=uri, registry_uri=uri)


def flatten_params(values: dict, prefix: str = "") -> dict:
    result = {}
    for name, value in values.items():
        key = f"{prefix}.{name}" if prefix else name
        if isinstance(value, dict):
            result.update(flatten_params(value, key))
        else:
            result[key] = (
                json.dumps(value, sort_keys=True)
                if value is None or isinstance(value, (list, bool))
                else value
            )
    return result


def read_result(directory: Path, dataset_directory: Path | None = None) -> tuple:
    report = json.loads((directory / "evaluation.json").read_text())
    if dataset_directory is None:
        dataset_directory = (
            directory if (directory / "dataset.json").is_file() else directory.parent
        )
    dataset_path = dataset_directory / "dataset.json"
    dataset = json.loads(dataset_path.read_text())
    if (
        report["dataset"] not in {"synthetic", "private"}
        or report["dataset"] != dataset["dataset"]
    ):
        raise ValueError("Expected matching synthetic or private dataset reports.")
    if report["lineage"]["dataset_sha256"] != sha256(dataset_path):
        raise ValueError("The dataset changed after evaluation. Evaluate it again.")
    for key in ("input_sha256", "training_sha256", "evaluation_sha256"):
        if key in report["lineage"] and report["lineage"][key] != dataset[key]:
            raise ValueError("The evaluation report uses a different dataset split.")
    for name, value in report["metrics"].items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Metric {name} must be a finite number.")
    specification = model_artifact(directory, report)
    if specification is not None:
        verify_files(directory, specification)
    return report, dataset, dataset_path, specification


def log_model(directory: Path, specification: dict):
    """Copy a complete predictor into MLflow without loading it in this environment."""
    import mlflow
    from mlflow.models import ModelSignature

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        bundle = work / "bundle"
        bundle.mkdir()
        packaged = {**specification, "files": {}}
        for name, source in verify_files(directory, specification).items():
            shutil.copy2(source, bundle / name)
            expected = specification["files"][name]["sha256"]
            if sha256(bundle / name) != expected:
                raise ValueError(f"Model artifact {name} changed while copying.")
            packaged["files"][name] = {"path": name, "sha256": expected}
        write_json(bundle / "model.json", packaged)
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
        return mlflow.pyfunc.log_model(
            name="model",
            loader_module=specification["loader_module"],
            data_path=str(bundle),
            code_paths=[str(path) for path in sorted(code.iterdir())],
            pip_requirements=[
                f"mlflow=={mlflow.__version__}",
                *specification["requirements"],
            ],
            metadata={"target_unit": "EUR/month"},
            signature=ModelSignature.from_dict(specification["signature"])
            if specification.get("signature")
            else None,
        )


def track(directory: Path, store: Path, dataset_directory: Path | None = None) -> str:
    # Validate inputs before creating a run or importing a model library.
    report, dataset, dataset_path, specification = read_result(
        directory, dataset_directory
    )
    client = local_client(store)
    import mlflow

    dataset_kind = report["dataset"]
    experiment_name = f"pret-drept-{dataset_kind}"
    artifact_dir = store.resolve() / "artifacts" / dataset_kind
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        experiment_id = client.create_experiment(
            experiment_name, artifact_location=artifact_dir.as_uri()
        )
    else:
        if experiment.artifact_location != artifact_dir.as_uri():
            raise ValueError(
                "MLflow experiment points outside this store. Choose a new --store."
            )
        experiment_id = experiment.experiment_id

    code_hashes = {
        relative: sha256(ROOT / relative)
        for relative in (specification or {}).get("code_paths", [])
    }
    identity = hashlib.sha256(
        json.dumps(
            {
                "report": sha256(directory / "evaluation.json"),
                "model_artifact": specification,
                "inference_code_at_logging": code_hashes,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    matching = client.search_runs(
        [experiment_id],
        filter_string=f"tags.result_sha256 = '{identity}' and attributes.status = 'FINISHED'",
        max_results=1,
    )
    if matching:
        return matching[0].info.run_id

    kind = model_type(report)
    status = git_value("status", "--porcelain")
    tags = {
        "dataset": dataset_kind,
        "model_type": kind,
        "model_ready": str(specification is not None).lower(),
        "result_sha256": identity,
        "evaluation_report_sha256": sha256(directory / "evaluation.json"),
        "evaluation_sha256": dataset["evaluation_sha256"],
        "git_commit_at_logging": git_value("rev-parse", "HEAD"),
        "git_worktree_at_logging": status
        if status == "unavailable"
        else ("dirty" if status else "clean"),
        **report["lineage"],
    }
    if (
        directory.resolve() == ROOT / "artifacts" / "real"
        and (ROOT / "dvc.lock").is_file()
    ):
        tags["dvc_lock_sha256_at_logging"] = sha256(ROOT / "dvc.lock")
        if (ROOT / "data" / "dataset.dvc").is_file():
            tags["input_dvc_sha256_at_logging"] = sha256(ROOT / "data" / "dataset.dvc")

    parameters = report["parameters"]
    # Legacy XGBoost reports already nest model parameters; other reports are flat.
    if "model" not in parameters:
        parameters = {"model": parameters}
    parameters = {**parameters, "split": dataset["split"]}
    if "model_version" in report:
        parameters["library_version"] = report["model_version"]
    if "runtime" in report:
        parameters["runtime"] = report["runtime"]
    with mlflow.start_run(
        experiment_id=experiment_id, run_name=f"{kind} · {dataset_kind}", tags=tags
    ) as run:
        mlflow.log_params(flatten_params(parameters))
        mlflow.log_artifact(str(directory / "evaluation.json"))
        mlflow.log_artifact(str(dataset_path))
        if specification is not None:
            info = log_model(directory, specification)
            mlflow.set_tags({"model_uri": info.model_uri, "model_id": info.model_id})
            mlflow.log_metrics(report["metrics"], model_id=info.model_id)
        else:
            mlflow.log_metrics(report["metrics"])
    return run.info.run_id


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
        from mlops.registry import register

        version = register(run_id, args.store)
        print(f"{run_id} models:/{version.name}/{version.version}")
    else:
        print(run_id)


if __name__ == "__main__":
    main()
