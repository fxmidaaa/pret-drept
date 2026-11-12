"""Train a native CatBoost model on the shared training partition."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

import catboost
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from mlops.training import feature_frame, training_data


def train(directory: Path, config: dict) -> None:
    frame, preprocessing = training_data(directory)
    settings = {
        **config["catboost"],
        "loss_function": "RMSE",
        "random_seed": config["seed"],
        "thread_count": 1,
        "allow_writing_files": False,
        "verbose": False,
    }
    model = CatBoostRegressor(**settings)
    model.fit(
        feature_frame(frame, preprocessing),
        np.log1p(frame["price"].to_numpy()),
        cat_features=preprocessing["categorical_features"],
    )

    output = directory / "catboost"
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "model.cbm"
    model_path.unlink(missing_ok=True)  # Do not write through a DVC cache link.
    model.save_model(str(model_path))
    metadata = {
        "model_type": "catboost",
        "model_version": catboost.__version__,
        "parameters": settings,
        "runtime": {"numpy": np.__version__, "pandas": pd.__version__},
        "preprocessing": preprocessing,
        "training_rows": len(frame),
        "training_sha256": sha256((directory / "train.csv").read_bytes()).hexdigest(),
        "model_sha256": sha256(model_path.read_bytes()).hexdigest(),
    }
    metadata_path = output / "training.json"
    metadata_path.unlink(missing_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Trained CatBoost on {len(frame)} rows and saved {model_path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CatBoost on a prepared split.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--config", type=Path, default=Path("params.json"))
    args = parser.parse_args()
    train(args.directory, json.loads(args.config.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
