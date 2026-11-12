"""Package trusted local predictors without importing their training libraries."""

import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from predict import build_features, load_bundle, model_matrix, predict_eur

MODEL_CODE = [
    "features.py",
    "predict.py",
    "mlops/__init__.py",
    "mlops/models.py",
]
INFERENCE_PACKAGES = {
    "numpy",
    "pandas",
    "scikit-learn",
    "scipy",
    "joblib",
    "xgboost",
    "xgboost-cpu",
}


def model_type(report: dict) -> str:
    # Older benchmark reports used model for the algorithm name.
    return report.get("model_type", report.get("model", "xgboost")).lower()


def model_artifact(report: dict) -> dict | None:
    """Read the common contract; retain compatibility with existing local results."""
    if "model_artifact" in report:
        specification = report["model_artifact"]
        if specification is None:
            return None
        if specification.get("loader_module") == "mlops.models":
            # Re-log older reports using the current loader's source files.
            return {**specification, "code_paths": MODEL_CODE}
        return specification
    kind = model_type(report)
    # Build the artifact description for the three formats used by this project.
    # Other algorithms can provide model_artifact explicitly.
    if kind == "xgboost":
        requirements = [
            line
            for line in Path("requirements.txt").read_text().splitlines()
            if line.split("==")[0] in INFERENCE_PACKAGES
        ]
        filename = "model.joblib"
    elif kind == "catboost":
        requirements = [
            f"catboost=={report['model_version']}",
            *[f"{name}=={report['runtime'][name]}" for name in ("numpy", "pandas")],
        ]
        filename = "model.cbm"
    elif kind == "tabpfn" and "checkpoint_path" in report:
        requirements = [
            f"tabpfn=={report['model_version']}",
            *[
                f"{name}=={report['runtime'][name]}"
                for name in (
                    "torch",
                    "numpy",
                    "pandas",
                    "scikit-learn",
                    "scipy",
                    "joblib",
                )
            ],
        ]
        filename = "model.tabpfn_fit"
    else:
        # A benchmark score is useful even when no fitted predictor was saved.
        return None
    files = {
        filename: {
            "path": filename,
            "sha256": report["lineage"]["model_sha256"],
        }
    }
    if kind == "tabpfn":
        files["checkpoint.ckpt"] = {
            "path": report["checkpoint_path"],
            "sha256": report["lineage"]["checkpoint_sha256"],
        }
    return {
        "loader_module": "mlops.models",
        "kind": kind,
        "files": files,
        "requirements": requirements,
        "code_paths": MODEL_CODE,
        "preprocessing": report.get("preprocessing"),
        "target_transform": report.get("target_transform", "log1p"),
    }


class XGBoostPredictor:
    """Give MLflow the same bundle-based predictor used by the API and evaluation."""

    def __init__(self, directory: Path):
        self.bundle = load_bundle(directory / "model.joblib")

    def predict(self, data):
        return predict_eur(
            model_matrix(data.to_dict("records"), self.bundle), self.bundle
        )


class FramePredictor:
    """Share feature preparation and EUR conversion between CatBoost and TabPFN."""

    def __init__(self, model, specification: dict):
        self.model = model
        self.preprocessing = specification["preprocessing"]
        if specification["target_transform"] != "log1p":
            raise ValueError("Expected the saved model to predict log1p rent.")

    def predict(self, data):
        records = data.to_dict("records")
        feature_rows = [build_features(row, self.preprocessing) for row in records]
        frame = pd.DataFrame(feature_rows, columns=self.preprocessing["features"])
        predictions = np.expm1(self.model.predict(frame))
        if not (np.isfinite(predictions) & (predictions > 0)).all():
            raise ValueError("The model returned an invalid monthly rent.")
        return predictions


def load_tabpfn(directory: Path, checkpoint: Path | None = None):
    from tabpfn import TabPFNRegressor

    # TabPFN 9.2.0 stores an absolute checkpoint path in its fitted-state archive.
    # Rewrite only that reference in a temporary copy to use the packaged weights.
    with tempfile.TemporaryDirectory() as temporary:
        restored = Path(temporary) / "model.tabpfn_fit"
        with (
            zipfile.ZipFile(directory / "model.tabpfn_fit") as source,
            zipfile.ZipFile(restored, "w") as target,
        ):
            for entry in source.infolist():
                data = source.read(entry.filename)
                if entry.filename == "init_params.json":
                    params = json.loads(data)
                    params["model_path"] = str(
                        (checkpoint or directory / "checkpoint.ckpt").resolve()
                    )
                    data = json.dumps(params).encode()
                target.writestr(entry, data)
        return TabPFNRegressor.load_from_fit_state(
            restored, device=os.environ.get("PRET_DREPT_TABPFN_DEVICE", "auto")
        )


def _load_pyfunc(data_path: str):
    """Load a saved predictor; only its optional model library is imported."""
    directory = Path(data_path)
    specification = json.loads((directory / "model.json").read_text())
    kind = specification["kind"]
    if kind == "xgboost":
        return XGBoostPredictor(directory)
    if kind == "catboost":
        from catboost import CatBoostRegressor

        model = CatBoostRegressor()
        model.load_model(str(directory / "model.cbm"))
        return FramePredictor(model, specification)
    if kind == "tabpfn":
        return FramePredictor(load_tabpfn(directory), specification)
    raise ValueError("Provide a loader_module for this model format.")
