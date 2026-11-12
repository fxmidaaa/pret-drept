"""Fit TabPFN using the local checkpoint and the shared training partition."""

import argparse
import json
import os
from hashlib import sha256
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
import tabpfn
import torch
from tabpfn import TabPFNRegressor

from mlops.training import feature_frame, training_data

CHECKPOINT = Path("artifacts/private/checkpoints/tabpfn-v2-regressor.ckpt")


def train(directory: Path, config: dict) -> None:
    if not CHECKPOINT.is_file():
        raise FileNotFoundError(f"TabPFN needs the local checkpoint: {CHECKPOINT}")
    frame, preprocessing = training_data(directory)
    settings = {**config["tabpfn"], "random_state": config["seed"]}
    model = TabPFNRegressor(
        model_path=str(CHECKPOINT.resolve()),
        categorical_features_indices=[
            preprocessing["features"].index(name)
            for name in preprocessing["categorical_features"]
        ],
        **settings,
    )
    print(f"Fitting TabPFN on {len(frame)} rows.", flush=True)
    model.fit(feature_frame(frame, preprocessing), np.log1p(frame["price"].to_numpy()))

    output = directory / "tabpfn"
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "model.tabpfn_fit"
    model_path.unlink(missing_ok=True)  # Do not write through a DVC cache link.
    model.save_fit_state(model_path)

    metadata = {
        "model_type": "tabpfn",
        "model_version": tabpfn.__version__,
        "parameters": settings,
        "runtime": {
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "preprocessing": preprocessing,
        "training_rows": len(frame),
        "training_sha256": sha256((directory / "train.csv").read_bytes()).hexdigest(),
        "model_sha256": sha256(model_path.read_bytes()).hexdigest(),
        "checkpoint_path": os.path.relpath(CHECKPOINT.resolve(), output.resolve()),
        "checkpoint_sha256": sha256(CHECKPOINT.read_bytes()).hexdigest(),
    }
    metadata_path = output / "training.json"
    metadata_path.unlink(missing_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved the fitted TabPFN model in {output}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit TabPFN on a prepared split.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--config", type=Path, default=Path("params.json"))
    args = parser.parse_args()
    train(args.directory, json.loads(args.config.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
