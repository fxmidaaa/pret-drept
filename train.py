import argparse
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from xgboost import XGBRegressor

from features import MODEL_FEATURES, numerical
from mlops.config import Config, load_config
from mlops.files import atomic_output, sha256
from mlops.prepare import read_partition
from predict import build_features

# Fixed defaults only apply when a whole optional column is missing from training.
EMPTY_COLUMN_DEFAULTS = {
    "floor": 1.0,
    "total_floors": 5.0,
    "kitchen_area": 10.0,
    "ceiling_height": 2.7,
}


def train(directory: Path, config: Config) -> None:
    source = directory / "train.csv"
    frame = read_partition(source)
    medians = {}
    for name in numerical:
        if name in MODEL_FEATURES:
            values = frame[name].dropna()
            medians[name] = (
                float(values.median()) if len(values) else EMPTY_COLUMN_DEFAULTS[name]
            )

    bundle = {
        "features": MODEL_FEATURES,
        "numeric_defaults": medians,
        "meta": {
            "format": "pret-drept-simple-v1",
            "n_listings": len(frame),
            "training_sha256": sha256(source),
            "config": config.model_dump(),
        },
    }
    vectorizer = DictVectorizer(sparse=False)
    matrix = vectorizer.fit_transform(
        [build_features(record, bundle) for record in frame.to_dict(orient="records")]
    )
    model = XGBRegressor(
        **config.model.model_dump(),
        objective="reg:squarederror",
        tree_method="hist",
        random_state=config.seed,
        n_jobs=1,
    )
    model.fit(matrix, np.log1p(frame["price"].to_numpy()))
    bundle.update(dv=vectorizer, model=model)

    destination = directory / "model.joblib"
    with atomic_output(destination) as temporary:
        joblib.dump(bundle, temporary, compress=3)
    print(f"Trained XGBoost on {len(frame)} rows and saved {destination}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit XGBoost using a prepared training partition."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--config", type=Path, default=Path("params.json"))
    args = parser.parse_args()
    try:
        train(args.directory, load_config(args.config))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Training failed. {exc}\n")


if __name__ == "__main__":
    main()
