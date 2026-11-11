import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mlops.evaluate import evaluate
from predict import load_bundle, model_matrix, predict_eur
from train import train

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("changed", ["model", "dataset", "metric"])
def test_tracking_rejects_invalid_inputs(tmp_path, changed):
    demo = ROOT / "artifacts/demo"
    if not (demo / "evaluation.json").is_file():
        pytest.skip("Run the fixture stage commands first.")
    for name in ("dataset.json", "evaluation.json", "model.joblib"):
        shutil.copy2(demo / name, tmp_path / name)
    report = json.loads((tmp_path / "evaluation.json").read_text())
    if changed == "model":
        with (tmp_path / "model.joblib").open("ab") as stream:
            stream.write(b"changed")
    elif changed == "dataset":
        report["dataset"] = "private"
        (tmp_path / "evaluation.json").write_text(json.dumps(report), encoding="utf-8")
    else:
        report["metrics"]["mae_eur"] = "invalid"
        (tmp_path / "evaluation.json").write_text(json.dumps(report), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mlops.track",
            str(tmp_path),
            "--store",
            str(tmp_path / "tracking"),
        ],
        check=False,
        cwd=ROOT,
        env={**os.environ, "MLFLOW_DISABLE_TELEMETRY": "true"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    expected = {
        "model": "changed after evaluation",
        "dataset": "matching synthetic or private",
        "metric": "invalid",
    }
    assert expected[changed] in result.stderr, result.stdout + result.stderr


def test_model_registry_round_trip_and_generic_tracking(tmp_path):
    demo = ROOT / "artifacts/demo"
    if not (demo / "evaluation.json").is_file():
        pytest.skip("Run the fixture stage commands first.")
    first = tmp_path / "first"
    second = tmp_path / "second"
    for destination in (first, second):
        destination.mkdir()
        for name in (
            "dataset.json",
            "train.csv",
            "evaluation.csv",
            "model.joblib",
            "evaluation.json",
        ):
            shutil.copy2(demo / name, destination / name)
    legacy = json.loads((first / "evaluation.json").read_text())
    legacy["model_artifact"]["code_paths"].append("mlops/files.py")
    (first / "evaluation.json").write_text(json.dumps(legacy), encoding="utf-8")
    config = json.loads((ROOT / "params.json").read_text())
    config["model"]["n_estimators"] = 4
    train(second, config)
    evaluate(second)
    expected_hash = sha256((second / "model.joblib").read_bytes()).hexdigest()
    inputs = pd.read_csv(second / "evaluation.csv").drop(columns="price")
    bundle = load_bundle(second / "model.joblib")
    expected = predict_eur(
        model_matrix(inputs.to_dict("records"), bundle),
        bundle,
    )

    # The subprocess uses the same Python environment and a temporary MLflow store.
    script = """
import json
import sys
from hashlib import sha256
from pathlib import Path

from mlops.registry import export_model, local_client, register, set_alias
from mlops.track import track

root = Path(sys.argv[1])
store = root / "tracking"
first = root / "first"
second = root / "second"
run1 = track(first, store)
assert track(first, store) != run1
version1 = register(run1, store)
assert register(run1, store).version != version1.version
run2 = track(second, store)
version2 = register(run2, store)
assert version1.version != version2.version
name = version1.name
client = local_client(store)
assert len(client.search_model_versions(f"name = '{name}'")) == 3
run = client.get_run(run2)
report = json.loads((second / "evaluation.json").read_text())
assert run.info.status == "FINISHED"
assert run.data.tags["dataset"] == "synthetic"
assert run.data.tags["model_type"] == "xgboost"
assert run.data.tags["model_ready"] == "true"
assert run.data.tags["model_uri"]
assert run.data.metrics == report["metrics"]
assert run.data.params["seed"] == str(report["parameters"]["seed"])
assert run.data.params["model.n_estimators"] == "4"
assert {file.path for file in client.list_artifacts(run2)} == {
    "dataset.json", "evaluation.json"
}
assert not any(key.startswith("xgboost.") for key in run.data.params)
assert run.data.tags["evaluation_sha256"]
assert "xgboost" not in sys.modules and "catboost" not in sys.modules

# Registry artifacts remain usable after the original experiment's model is gone.
(second / "model.joblib").unlink()
set_alias(name, version2.version, "champion", store)
chosen = export_model(name, root / "selected", store, alias="champion")
assert chosen["version"] == version2.version
try:
    export_model(name, root / "selected", store, alias="champion")
except FileExistsError:
    pass
else:
    raise AssertionError("An export must not overwrite an existing directory.")
set_alias(name, version1.version, "champion", store)
rollback = export_model(name, root / "rollback", store, alias="champion")
assert rollback["version"] == version1.version

# An arbitrary algorithm can log nested hyperparameters and scores without a model.
benchmark = root / "benchmark"
benchmark.mkdir()
report = json.loads((first / "evaluation.json").read_text())
report.update(model_type="other-regressor", model_artifact=None,
              parameters={"depth": 3, "options": {"layers": [4, 2]}})
(benchmark / "evaluation.json").write_text(json.dumps(report))
benchmark_run = track(benchmark, store, first)
logged = client.get_run(benchmark_run)
assert logged.data.params["model.depth"] == "3"
assert logged.data.params["model.options.layers"] == "[4, 2]"
assert logged.data.tags["model_type"] == "other-regressor"
assert logged.data.tags["model_ready"] == "false"
try:
    register(benchmark_run, store)
except ValueError:
    pass
else:
    raise AssertionError("A score-only benchmark must not become a model version.")
client.create_registered_model("private-only", tags={"dataset": "private"})
try:
    register(run1, store, "private-only")
except ValueError:
    pass
else:
    raise AssertionError("Synthetic and private versions must stay separate.")
assert len(client.search_runs([run.info.experiment_id])) == 4

# A custom loader and file format can register without edits to the tracker.
import mlops.track as tracking
code = root / "custom-code"
code.mkdir()
(code / "constant_loader.py").write_text(
    "import json\\nfrom pathlib import Path\\n"
    "class Predictor:\\n"
    "    def __init__(self, path): self.value = json.loads((Path(path) / 'weights.json').read_text())['rent']\\n"
    "    def predict(self, data): return [self.value] * len(data)\\n"
    "def _load_pyfunc(path): return Predictor(path)\\n"
)
custom = root / "custom"
custom.mkdir()
(custom / "weights.json").write_text(json.dumps({"rent": 500}))
report.update(model_type="constant", model_artifact={
    "loader_module": "constant_loader",
    "files": {"weights.json": {"path": "weights.json", "sha256": sha256((custom / "weights.json").read_bytes()).hexdigest()}},
    "requirements": [], "code_paths": ["constant_loader.py"]
})
(custom / "evaluation.json").write_text(json.dumps(report))
tracking.ROOT = code
custom_run = track(custom, store, first)
custom_version = register(custom_run, store)
export_model(name, root / "custom-export", store, version=custom_version.version)
import mlflow
assert list(mlflow.pyfunc.load_model(str(root / "custom-export")).predict([{}, {}])) == [500, 500]
print(json.dumps({"run_id": run2, "version": version2.version}))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(tmp_path)],
        cwd=ROOT,
        check=False,
        env={**os.environ, "MLFLOW_DISABLE_TELEMETRY": "true"},
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    identity = json.loads(result.stdout.splitlines()[-1])
    assert (
        json.loads((tmp_path / "selected/registry.json").read_text())["version"]
        == identity["version"]
    )
    saved = tmp_path / "selected/data/bundle/model.joblib"
    assert sha256(saved.read_bytes()).hexdigest() == expected_hash

    # Load the packaged source outside the repository in the inference environment.
    prediction_script = """
import json
import sys
from pathlib import Path
import pandas as pd
from mlops.models import _load_pyfunc
model = _load_pyfunc(str(Path(sys.argv[1]) / "data/bundle"))
data = pd.read_csv(sys.argv[2]).drop(columns="price")
print(json.dumps(model.predict(data).tolist()))
"""
    restored = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            prediction_script,
            str(tmp_path / "selected"),
            str(second / "evaluation.csv"),
        ],
        cwd=tmp_path,
        check=False,
        env={**os.environ, "PYTHONPATH": str(tmp_path / "selected/code")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert restored.returncode == 0, restored.stdout + restored.stderr
    np.testing.assert_array_equal(json.loads(restored.stdout), expected)
