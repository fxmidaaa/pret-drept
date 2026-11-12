"""Evaluate one saved model on the shared held-out partition."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from features import categorical
from mlops.models import FramePredictor, load_tabpfn, model_artifact
from predict import load_bundle, model_matrix, predict_eur


def evaluate(directory: Path, model_type: str = "xgboost") -> None:
    manifest_path = directory / "dataset.json"
    evaluation_path = directory / "evaluation.csv"
    dataset = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(evaluation_path.read_bytes()).hexdigest() != dataset["evaluation_sha256"]:
        raise ValueError(
            "The evaluation CSV differs from dataset.json. Run preparation again."
        )
    frame = pd.read_csv(evaluation_path, dtype={name: str for name in categorical})

    if model_type == "xgboost":
        import xgboost

        output = directory
        model_path = output / "model.joblib"
        bundle = load_bundle(model_path)
        metadata = {
            "model_version": xgboost.__version__,
            "parameters": bundle["meta"]["config"],
            "training_rows": bundle["meta"]["n_listings"],
            "training_sha256": bundle["meta"]["training_sha256"],
        }
    else:
        output = directory / model_type
        metadata = json.loads((output / "training.json").read_text(encoding="utf-8"))
        if metadata["model_type"] != model_type:
            raise ValueError("The saved model type does not match the requested model.")
        if model_type == "tabpfn" and "model_artifact" in metadata:
            # Training files from the earlier workflow stored these inside the artifact.
            files = metadata["model_artifact"]["files"]
            metadata["model_sha256"] = files["model.tabpfn_fit"]["sha256"]
            metadata["checkpoint_path"] = files["checkpoint.ckpt"]["path"]
            metadata["checkpoint_sha256"] = files["checkpoint.ckpt"]["sha256"]

    if metadata["training_sha256"] != dataset["training_sha256"]:
        raise ValueError(
            "The model and dataset have different training lineage. Retrain the model."
        )

    if model_type == "xgboost":
        predictions = predict_eur(
            model_matrix(frame.to_dict("records"), bundle), bundle
        )
    else:
        if model_type == "catboost":
            from catboost import CatBoostRegressor

            model_path = output / "model.cbm"
        elif model_type == "tabpfn":
            model_path = output / "model.tabpfn_fit"
        else:
            raise ValueError(f"Unknown model: {model_type}")

        if sha256(model_path.read_bytes()).hexdigest() != metadata["model_sha256"]:
            raise ValueError(f"The saved {model_type} model changed after training.")
        if model_type == "catboost":
            model = CatBoostRegressor()
            model.load_model(str(model_path))
        else:
            checkpoint = output / metadata["checkpoint_path"]
            if (
                sha256(checkpoint.read_bytes()).hexdigest()
                != metadata["checkpoint_sha256"]
            ):
                raise ValueError("The TabPFN checkpoint changed after training.")
            model = load_tabpfn(output, checkpoint)
        predictions = FramePredictor(
            model,
            {"preprocessing": metadata["preprocessing"], "target_transform": "log1p"},
        ).predict(frame)

    errors = predictions - frame["price"].to_numpy()
    report = {
        "dataset": dataset["dataset"],
        "model_type": model_type,
        "model_version": metadata["model_version"],
        "target_transform": "log1p",
        "target_unit": "EUR/month",
        "parameters": metadata["parameters"],
        "metrics": {
            "mae_eur": float(np.abs(errors).mean()),
            "rmse_eur": float(np.sqrt(np.square(errors).mean())),
            "training_rows": metadata["training_rows"],
            "evaluation_rows": len(frame),
        },
        "lineage": {
            "dataset_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
            "model_sha256": sha256(model_path.read_bytes()).hexdigest(),
        },
    }
    if model_type != "xgboost":
        report["preprocessing"] = metadata["preprocessing"]
        report["runtime"] = metadata["runtime"]
    if model_type == "tabpfn":
        report["checkpoint_path"] = metadata["checkpoint_path"]
        report["lineage"]["checkpoint_sha256"] = metadata["checkpoint_sha256"]
    if model_type == "tabpfn" and "model_artifact" in metadata:
        report["model_artifact"] = metadata["model_artifact"]
    else:
        report["model_artifact"] = model_artifact(report)
    report_path = output / "evaluation.json"
    report_path.unlink(missing_ok=True)  # Leave any DVC cache link untouched.
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a model on the held-out partition."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--model", choices=("xgboost", "catboost", "tabpfn"), default="xgboost"
    )
    args = parser.parse_args()
    evaluate(args.directory, args.model)


if __name__ == "__main__":
    main()
