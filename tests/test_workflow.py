import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mlops.config import load_config
from mlops.files import sha256
from mlops.prepare import GROUP_COLUMNS, prepare, read_partition
from predict import load_bundle, model_matrix, predict_eur


def test_preparation_keeps_reposts_together_and_excludes_unknown_currency(tmp_path):
    fixture = pd.read_csv("data/sample/demo.csv")
    invalid = fixture.iloc[[0]].assign(price_unit="UNKNOWN")
    source = tmp_path / "listings.csv"
    pd.concat([fixture, invalid], ignore_index=True).to_csv(source, index=False)

    prepare(
        source, tmp_path / "prepared", load_config(Path("params.json")), synthetic=True
    )
    output = tmp_path / "prepared"
    train = read_partition(output / "train.csv")
    evaluation = read_partition(output / "evaluation.csv")
    manifest = json.loads((output / "dataset.json").read_text())

    train_keys = set(train[GROUP_COLUMNS].itertuples(index=False, name=None))
    evaluation_keys = set(evaluation[GROUP_COLUMNS].itertuples(index=False, name=None))
    assert train_keys.isdisjoint(evaluation_keys)
    assert manifest["excluded_rows"] == 1
    assert len(train) + len(evaluation) == len(fixture)
    assert manifest["input_sha256"] == sha256(source)


def test_dvc_evaluation_matches_reloaded_model():
    demo = Path("artifacts/demo")
    report_path = demo / "evaluation.json"
    if not report_path.is_file():
        pytest.skip("Run dvc repro to build and evaluate the demo model.")

    model_path = demo / "model.joblib"
    bundle = load_bundle(model_path)
    train = read_partition(demo / "train.csv")
    evaluation = read_partition(demo / "evaluation.csv")
    report = json.loads(report_path.read_text())
    predictions = predict_eur(
        model_matrix(evaluation.to_dict(orient="records"), bundle), bundle
    )
    errors = predictions - evaluation["price"].to_numpy()

    assert bundle["numeric_defaults"]["area"] == train["area"].median()
    assert report["dataset"] == "synthetic"
    assert report["lineage"]["model_sha256"] == sha256(model_path)
    assert report["metrics"]["mae_eur"] == pytest.approx(np.abs(errors).mean())
    assert report["metrics"]["rmse_eur"] == pytest.approx(np.sqrt((errors**2).mean()))
