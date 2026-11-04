from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd

import predict
import train
from features import FEATURES


class _StubEstimator:
    def __init__(self, **kwargs):
        pass

    def fit(self, inputs, targets):
        return self

    def predict(self, inputs):
        self.last_inputs = inputs
        return np.full(len(inputs), np.log1p(500))


def test_legacy_export_reloads_the_fitted_preprocessing(tmp_path, monkeypatch):
    training = pd.DataFrame(
        {
            **{field: [1.0] * 3 for field in FEATURES},
            "sector": ["centru"] * 3,
            "area": [50.0] * 3,
            "price": [2000.0, 500.0, 500.0],
            "lat": [47.02] * 3,
            "lon": [28.85] * 3,
            "total_floors": [10.0, 20.0, 30.0],
            "photo_count": [1, 5, 9],
        }
    )
    requests = [
        {**training.iloc[1].to_dict(), "total_floors": None},
        training.iloc[2].to_dict(),
    ]
    validation = pd.DataFrame(requests, columns=training.columns)

    monkeypatch.setattr(train, "BASE", str(tmp_path))
    monkeypatch.setattr(train.pd, "read_csv", lambda path: training)
    monkeypatch.setattr(train, "clean_data", lambda rows: rows)
    monkeypatch.setattr(train, "train_test_split", lambda *args, **kwargs: (training, validation))
    monkeypatch.setattr(train, "trim_ppm_outliers", lambda rows, bounds=None: (rows, bounds))
    monkeypatch.setattr(train, "LinearRegression", _StubEstimator)
    monkeypatch.setattr(train, "XGBRegressor", _StubEstimator)

    train.main()
    bundle = joblib.load(tmp_path / "model.joblib")

    assert bundle["imputation_medians"]["total_floors"] == 20.0
    assert bundle["numeric_defaults"]["total_floors"] == 20.0
    assert bundle["numeric_defaults"]["photo_count"] == 7.0
    assert predict.build_features(requests[0], bundle)["total_floors"] == 20.0
    expected = bundle["model"].last_inputs.copy()
    bundle["explainer"] = SimpleNamespace(shap_values=np.zeros_like)
    monkeypatch.setattr(predict, "get_bundle", lambda: bundle)
    for row, encoded in zip(requests, expected, strict=True):
        assert predict.run(row)["fair_price"] == 500
        np.testing.assert_array_equal(bundle["model"].last_inputs[0], encoded)

    # An older bundle has only the serving defaults available to it.
    del bundle["imputation_medians"]
    bundle["numeric_defaults"]["total_floors"] = 25.0
    predict.run(requests[0])
    index = list(bundle["dv"].get_feature_names_out()).index("total_floors")
    assert bundle["model"].last_inputs[0, index] == 25.0
