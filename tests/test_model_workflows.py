"""Exercise optional models from training through a reloaded registry export."""

import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mlops.prepare import prepare

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "artifacts/private/checkpoints/tabpfn-v2-regressor.ckpt"


@pytest.mark.parametrize("model_type", ["catboost", "tabpfn"])
def test_model_workflow_and_registry_export(tmp_path, model_type):
    python = ROOT / f".venv-{model_type}/bin/python"
    if not python.is_file() or (model_type == "tabpfn" and not CHECKPOINT.is_file()):
        pytest.skip(
            f"The optional {model_type} environment or checkpoint is unavailable."
        )

    config = json.loads((ROOT / "params.json").read_text())
    config["catboost"]["iterations"] = 4
    config["tabpfn"]["n_estimators"] = 1
    config["tabpfn"]["device"] = "cpu"
    config_path = tmp_path / "params.json"
    config_path.write_text(json.dumps(config))
    run = tmp_path / "run"
    prepare(ROOT / "data/sample/demo.csv", run, config, synthetic=True)

    environment = {
        **os.environ,
        "MPLCONFIGDIR": str(tmp_path / "matplotlib"),
        "HF_HUB_OFFLINE": "1",
        "TABPFN_NO_BROWSER": "1",
        "PRET_DREPT_TABPFN_DEVICE": "cpu",
        "OMP_NUM_THREADS": "2",
        "MLFLOW_DISABLE_TELEMETRY": "true",
    }

    def run_command(command, *, cwd=ROOT):
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    run_command(
        [
            str(python),
            "-m",
            f"mlops.train_{model_type}",
            str(run),
            "--config",
            str(config_path),
        ]
    )
    run_command([str(python), "-m", "mlops.evaluate", str(run), "--model", model_type])
    output = run / model_type
    report = json.loads((output / "evaluation.json").read_text())
    metadata = json.loads((output / "training.json").read_text())
    dataset = json.loads((run / "dataset.json").read_text())
    training = pd.read_csv(run / "train.csv")
    assert report["model_type"] == model_type
    assert metadata["training_sha256"] == dataset["training_sha256"]
    assert (
        metadata["preprocessing"]["numeric_defaults"]["area"]
        == training["area"].median()
    )
    assert report["metrics"]["evaluation_rows"] == dataset["evaluation_rows"]

    if model_type == "tabpfn":
        # Previous runs kept the model and checkpoint hashes in model_artifact.
        old_metadata = {**metadata, "model_artifact": report["model_artifact"]}
        old_metadata["runtime"] = {
            name: metadata["runtime"][name] for name in ("numpy", "pandas", "torch")
        }
        for name in ("model_sha256", "checkpoint_path", "checkpoint_sha256"):
            del old_metadata[name]
        metadata_path = output / "training.json"
        metadata_path.write_text(json.dumps(old_metadata))
        run_command(
            [str(python), "-m", "mlops.evaluate", str(run), "--model", model_type]
        )
        old_report = json.loads((output / "evaluation.json").read_text())
        assert old_report["metrics"] == report["metrics"]
        metadata_path.write_text(json.dumps(metadata))

    # Tracking runs in the main environment; the predictor loads in its own one.
    tracking = """
import sys
from pathlib import Path
from mlops.track import track
from mlops.registry import export_model, register
root = Path(sys.argv[1])
model = sys.argv[2]
store = root / 'tracking'
run_id = track(root / 'run' / model, store)
version = register(run_id, store)
export_model(version.name, root / 'export', store, version=version.version)
"""
    run_command([sys.executable, "-c", tracking, str(tmp_path), model_type])
    prediction = """
import json, sys
import pandas as pd
# CI installs mlflow-skinny in the model environment. Locally, use the main
# environment's MLflow when the optional environment does not have it yet.
try:
    import mlflow
except ModuleNotFoundError:
    sys.path.append(sys.argv[3])
    import mlflow
model = mlflow.pyfunc.load_model(sys.argv[1])
frame = pd.read_csv(sys.argv[2])
print(json.dumps(model.predict(frame).tolist()))
"""
    package = tmp_path / "export"
    environment["PYTHONPATH"] = str(package / "code")
    predictions = json.loads(
        run_command(
            [
                str(python),
                "-c",
                prediction,
                str(package),
                str(run / "evaluation.csv"),
                sysconfig.get_paths()["purelib"],
            ],
            cwd=tmp_path,
        ).splitlines()[-1]
    )
    errors = (
        np.asarray(predictions)
        - pd.read_csv(run / "evaluation.csv")["price"].to_numpy()
    )
    assert report["metrics"]["mae_eur"] == pytest.approx(np.abs(errors).mean())
    assert report["metrics"]["rmse_eur"] == pytest.approx(
        np.sqrt(np.square(errors).mean())
    )

    # Evaluation refuses a model changed since training.
    model_file = output / (
        "model.cbm" if model_type == "catboost" else "model.tabpfn_fit"
    )
    with model_file.open("ab") as stream:
        stream.write(b"changed")
    result = subprocess.run(
        [str(python), "-m", "mlops.evaluate", str(run), "--model", model_type],
        cwd=ROOT,
        env={**environment, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode != 0
    assert "changed after training" in result.stderr
