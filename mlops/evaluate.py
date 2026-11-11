"""Score the saved XGBoost bundle on its held-out rows and write EUR metrics."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import xgboost
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from features import categorical
from mlops.models import model_artifact
from predict import load_bundle, model_matrix, predict_eur


def evaluate(directory: Path) -> None:
    model_path = directory / "model.joblib"
    manifest_path = directory / "dataset.json"
    evaluation_path = directory / "evaluation.csv"
    dataset = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(evaluation_path.read_bytes()).hexdigest() != dataset["evaluation_sha256"]:
        raise ValueError(
            "The evaluation CSV differs from dataset.json. Run preparation again."
        )

    bundle = load_bundle(model_path)
    metadata = bundle["meta"]
    if metadata["training_sha256"] != dataset["training_sha256"]:
        raise ValueError(
            "The model and dataset have different training lineage. Retrain the model."
        )

    frame = pd.read_csv(evaluation_path, dtype={name: str for name in categorical})
    predictions = predict_eur(
        model_matrix(frame.to_dict(orient="records"), bundle), bundle
    )
    report = {
        "dataset": dataset["dataset"],
        "model_type": "xgboost",
        "model_version": xgboost.__version__,
        "target_transform": "log1p",
        "target_unit": "EUR/month",
        "parameters": metadata["config"],
        "metrics": {
            "mae_eur": mean_absolute_error(frame["price"], predictions),
            "rmse_eur": root_mean_squared_error(frame["price"], predictions),
            "training_rows": metadata["n_listings"],
            "evaluation_rows": len(frame),
        },
        "lineage": {
            "dataset_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
            "model_sha256": sha256(model_path.read_bytes()).hexdigest(),
        },
    }
    report["model_artifact"] = model_artifact(report)
    report_path = directory / "evaluation.json"
    report_path.unlink(missing_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a trusted model on the held-out partition."
    )
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    evaluate(args.directory)


if __name__ == "__main__":
    main()
