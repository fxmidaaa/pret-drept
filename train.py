import argparse
import json
from hashlib import sha256
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from xgboost import XGBRegressor

from mlops.training import training_data
from predict import build_features


def train(directory: Path, config: dict) -> None:
    source = directory / "train.csv"
    frame, preprocessing = training_data(directory)

    bundle = {
        "features": preprocessing["features"],
        "numeric_defaults": preprocessing["numeric_defaults"],
        "meta": {
            "format": "pret-drept-simple-v1",
            "n_listings": len(frame),
            "training_sha256": sha256(source.read_bytes()).hexdigest(),
            "config": {
                "seed": config["seed"],
                "evaluation_fraction": config["evaluation_fraction"],
                "model": config["model"],
            },
        },
    }
    vectorizer = DictVectorizer(sparse=False)
    matrix = vectorizer.fit_transform(
        [build_features(record, bundle) for record in frame.to_dict(orient="records")]
    )
    model = XGBRegressor(
        **config["model"],
        objective="reg:squarederror",
        tree_method="hist",
        random_state=config["seed"],
        n_jobs=1,
    )
    model.fit(matrix, np.log1p(frame["price"].to_numpy()))
    bundle.update(dv=vectorizer, model=model)

    destination = directory / "model.joblib"
    destination.unlink(missing_ok=True)  # Leave any DVC cache link untouched.
    joblib.dump(bundle, destination, compress=3)
    print(f"Trained XGBoost on {len(frame)} rows and saved {destination}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit XGBoost using a prepared training partition."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--config", type=Path, default=Path("params.json"))
    args = parser.parse_args()
    train(args.directory, json.loads(args.config.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
