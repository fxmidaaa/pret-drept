"""Shared training data and feature preparation for the three models."""

from pathlib import Path

import pandas as pd

from features import MODEL_FEATURES, categorical, numerical
from predict import build_features

EMPTY_COLUMN_DEFAULTS = {
    "floor": 1.0,
    "total_floors": 5.0,
    "kitchen_area": 10.0,
    "ceiling_height": 2.7,
}


def training_data(directory: Path) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(
        directory / "train.csv", dtype={name: str for name in categorical}
    )
    numeric_columns = [name for name in numerical if name in MODEL_FEATURES]
    medians = frame[numeric_columns].median().fillna(EMPTY_COLUMN_DEFAULTS).to_dict()
    return frame, {
        "features": MODEL_FEATURES,
        "numeric_defaults": medians,
        "categorical_features": [
            name for name in MODEL_FEATURES if name in categorical
        ],
    }


def feature_frame(frame: pd.DataFrame, preprocessing: dict) -> pd.DataFrame:
    rows = [build_features(row, preprocessing) for row in frame.to_dict("records")]
    return pd.DataFrame(rows, columns=preprocessing["features"])
