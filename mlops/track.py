import argparse
import json
import os
import subprocess
from pathlib import Path

from mlops.files import sha256

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


def track(directory: Path, store: Path) -> str:
    os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
    import mlflow

    report_path = directory / "evaluation.json"
    dataset_path = directory / "dataset.json"
    model_path = directory / "model.joblib"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    lineage = report["lineage"]
    if lineage["dataset_sha256"] != sha256(dataset_path) or lineage[
        "model_sha256"
    ] != sha256(model_path):
        raise ValueError(
            "The dataset or model changed after evaluation. Evaluate it again."
        )

    dataset_kind = report["dataset"]
    if dataset_kind not in {"synthetic", "private"}:
        raise ValueError("Expected an evaluation of synthetic or private data.")

    store = store.resolve()
    store.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{store / 'mlflow.db'}")
    client = mlflow.MlflowClient()
    experiment_name = f"pret-drept-{dataset_kind}"
    experiment = client.get_experiment_by_name(experiment_name)
    artifact_dir = store / "artifacts" / dataset_kind
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

    status = git_value("status", "--porcelain")
    tags = {
        "dataset": dataset_kind,
        "git_commit_at_logging": git_value("rev-parse", "HEAD"),
        "git_worktree_at_logging": (
            status if status == "unavailable" else ("dirty" if status else "clean")
        ),
        **lineage,
    }
    if (
        directory.resolve() == ROOT / "artifacts" / "demo"
        and (ROOT / "dvc.lock").is_file()
    ):
        tags["dvc_lock_sha256_at_logging"] = sha256(ROOT / "dvc.lock")

    with mlflow.start_run(experiment_id=experiment_id, tags=tags) as run:
        params = report["parameters"]
        mlflow.log_params(
            {
                "seed": params["seed"],
                "evaluation_fraction": params["evaluation_fraction"],
                **{f"xgboost.{key}": value for key, value in params["model"].items()},
            }
        )
        mlflow.log_metrics(report["metrics"])
        mlflow.log_artifact(str(report_path))
        mlflow.log_artifact(str(dataset_path))
    return run.info.run_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record an evaluated model in local MLflow."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--store", type=Path, default=Path(".mlflow"))
    args = parser.parse_args()
    print(track(args.directory, args.store))


if __name__ == "__main__":
    main()
