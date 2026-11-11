import argparse
import json
from hashlib import sha256
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from xgboost import XGBRegressor

from features import MODEL_FEATURES, categorical, numerical
from predict import build_features

# Fixed defaults only apply when a whole optional column is missing from training.
EMPTY_COLUMN_DEFAULTS = {
    "floor": 1.0,
    "total_floors": 5.0,
    "kitchen_area": 10.0,
    "ceiling_height": 2.7,
}


def train(directory: Path, config: dict) -> None:
    source = directory / "train.csv"
    frame = pd.read_csv(source, dtype={name: str for name in categorical})
    numeric_columns = [name for name in numerical if name in MODEL_FEATURES]
    medians = frame[numeric_columns].median().fillna(EMPTY_COLUMN_DEFAULTS).to_dict()

    bundle = {
        "features": MODEL_FEATURES,
        "numeric_defaults": medians,
        "meta": {
            "format": "pret-drept-simple-v1",
            "n_listings": len(frame),
            "training_sha256": sha256(source.read_bytes()).hexdigest(),
            "config": config,
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
