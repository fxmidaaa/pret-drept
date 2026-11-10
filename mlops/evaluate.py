import argparse
import json
from pathlib import Path

from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from mlops.files import sha256, write_json
from mlops.prepare import read_partition
from predict import load_bundle, model_matrix, predict_eur


def evaluate(directory: Path) -> None:
    model_path = directory / "model.joblib"
    manifest_path = directory / "dataset.json"
    evaluation_path = directory / "evaluation.csv"
    dataset = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(evaluation_path) != dataset["evaluation_sha256"]:
        raise ValueError(
            "The evaluation CSV differs from dataset.json. Run preparation again."
        )

    bundle = load_bundle(model_path)
    metadata = bundle.get("meta", {})
    if metadata.get("format") != "pret-drept-simple-v1":
        raise ValueError("Evaluate a model produced by this branch's train.py.")
    config = metadata["config"]
    if metadata["training_sha256"] != dataset["training_sha256"] or any(
        config[key] != dataset["split"][key] for key in ("seed", "evaluation_fraction")
    ):
        raise ValueError(
            "The model and dataset have different training lineage. Retrain the model."
        )

    frame = read_partition(evaluation_path)
    predictions = predict_eur(
        model_matrix(frame.to_dict(orient="records"), bundle), bundle
    )
    report = {
        "dataset": dataset["dataset"],
        "parameters": config,
        "metrics": {
            "mae_eur": mean_absolute_error(frame["price"], predictions),
            "rmse_eur": root_mean_squared_error(frame["price"], predictions),
            "training_rows": metadata["n_listings"],
            "evaluation_rows": len(frame),
        },
        "lineage": {
            "input_sha256": dataset["input_sha256"],
            "dataset_sha256": sha256(manifest_path),
            "model_sha256": sha256(model_path),
        },
    }
    write_json(directory / "evaluation.json", report)
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
