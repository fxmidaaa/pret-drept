"""Package trusted local predictors without importing their training libraries."""

import json
import os
import shutil
import tempfile
import zipfile
from importlib.metadata import version
from pathlib import Path

from mlops.files import sha256

ROOT = Path(__file__).resolve().parents[1]
MODEL_CODE = [
    "features.py",
    "predict.py",
    "mlops/__init__.py",
    "mlops/files.py",
    "mlops/models.py",
]


def model_type(report: dict) -> str:
    # Older benchmark reports used model for the algorithm name.
    name = report.get("model_type", report.get("model", "xgboost"))
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Expected a non-empty model_type in the evaluation report.")
    return name.lower()


def model_artifact(directory: Path, report: dict) -> dict | None:
    """Read the common contract; retain compatibility with existing local results."""
    if "model_artifact" in report:
        return report["model_artifact"]
    kind = model_type(report)
    # Defaults for the two formats already saved by this project.
    # New algorithms supply model_artifact explicitly; tracking needs no changes.
    if kind == "xgboost":
        requirements = [
            line
            for line in (ROOT / "requirements-serve.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        filename = "model.joblib"
    elif kind == "catboost":
        requirements = [
            f"catboost=={report['model_version']}",
            *[f"{name}=={report['runtime'][name]}" for name in ("numpy", "pandas")],
        ]
        filename = "model.cbm"
    else:
        # A benchmark score is useful even when no fitted predictor was saved.
        return None
    return {
        "loader_module": "mlops.models",
        "kind": kind,
        "files": {
            filename: {
                "path": filename,
                "sha256": report["lineage"]["model_sha256"],
            }
        },
        "requirements": requirements,
        "code_paths": MODEL_CODE,
        "preprocessing": report.get("preprocessing"),
        "target_transform": report.get("target_transform", "log1p"),
    }


def verify_files(directory: Path, specification: dict) -> dict[str, Path]:
    """Verify every declared file before logging, exporting or deserializing it."""
    files = {}
    for name, entry in specification["files"].items():
        if Path(name).name != name or name in {"", ".", "..", "model.json"}:
            raise ValueError("Model artifact names must be plain filenames.")
        path = (directory / entry["path"]).resolve()
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Model artifact {name} changed after evaluation.")
        files[name] = path
    if not files:
        raise ValueError("A registered predictor needs at least one model artifact.")
    return files


class XGBoostPredictor:
    def __init__(self, directory: Path):
        from predict import load_bundle

        self.bundle = load_bundle(directory / "model.joblib")

    def predict(self, data):
        from predict import model_matrix, predict_eur

        return predict_eur(
            model_matrix(data.to_dict("records"), self.bundle), self.bundle
        )


class FramePredictor:
    def __init__(self, model, specification: dict):
        self.model = model
        self.preprocessing = specification["preprocessing"]
        if specification["target_transform"] != "log1p":
            raise ValueError("Expected the saved model to predict log1p rent.")

    def predict(self, data):
        import numpy as np
        import pandas as pd

        from predict import build_features

        frame = pd.DataFrame.from_records(
            [
                build_features(row, self.preprocessing)
                for row in data.to_dict("records")
            ],
            columns=self.preprocessing["features"],
        )
        predictions = np.expm1(self.model.predict(frame))
        if not (np.isfinite(predictions) & (predictions > 0)).all():
            raise ValueError("The model returned an invalid monthly rent.")
        return predictions


def save_tabpfn_artifact(
    model, directory: Path, checkpoint: Path, report: dict
) -> dict:
    """Call in the training environment, immediately after evaluating this estimator."""
    if sha256(checkpoint) != report["lineage"]["checkpoint_sha256"]:
        raise ValueError("The TabPFN checkpoint differs from the evaluated checkpoint.")
    destination = directory / "model.tabpfn_fit"
    directory.mkdir(parents=True, exist_ok=True)
    original_path = model.model_path
    if Path(original_path).resolve() != checkpoint.resolve():
        raise ValueError("Save the checkpoint used by the fitted TabPFN estimator.")
    try:
        # The pinned TabPFN serializer expects a JSON-compatible checkpoint path.
        model.model_path = str(checkpoint.resolve())
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            saved = Path(temporary) / destination.name
            model.save_fit_state(saved)
            shutil.move(saved, destination)
    finally:
        model.model_path = original_path
    return {
        "loader_module": "mlops.models",
        "kind": "tabpfn",
        "files": {
            destination.name: {"path": destination.name, "sha256": sha256(destination)},
            "checkpoint.ckpt": {
                "path": os.path.relpath(checkpoint, directory),
                "sha256": sha256(checkpoint),
            },
        },
        "requirements": [
            f"{name}=={version(name)}"
            for name in (
                "tabpfn",
                "torch",
                "numpy",
                "pandas",
                "scikit-learn",
                "scipy",
                "joblib",
            )
        ],
        "code_paths": MODEL_CODE,
        "preprocessing": report["preprocessing"],
        "target_transform": report["target_transform"],
    }


def load_tabpfn(directory: Path):
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
                    params["model_path"] = str(directory / "checkpoint.ckpt")
                    data = json.dumps(params).encode()
                target.writestr(entry, data)
        return TabPFNRegressor.load_from_fit_state(
            restored, device=os.environ.get("PRET_DREPT_TABPFN_DEVICE", "auto")
        )


def _load_pyfunc(data_path: str):
    """MLflow loader for the project's saved predictors; imports are lazy."""
    directory = Path(data_path)
    specification = json.loads((directory / "model.json").read_text())
    verify_files(directory, specification)
    if specification["kind"] == "xgboost":
        return XGBoostPredictor(directory)
    if specification["kind"] == "catboost":
        from catboost import CatBoostRegressor

        model = CatBoostRegressor()
        model.load_model(str(directory / "model.cbm"))
        return FramePredictor(model, specification)
    if specification["kind"] == "tabpfn":
        return FramePredictor(load_tabpfn(directory), specification)
    raise ValueError("Provide a loader_module for this model format.")
