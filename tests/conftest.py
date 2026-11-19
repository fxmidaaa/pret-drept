"""Build shared synthetic model outputs outside the project directory."""

import json
from pathlib import Path

import pytest

from mlops.evaluate import evaluate
from mlops.prepare import prepare
from train import train

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def synthetic_run(tmp_path_factory):
    directory = tmp_path_factory.mktemp("synthetic-run")
    config = json.loads((ROOT / "params.json").read_text())
    prepare(ROOT / "data/sample/demo.csv", directory, config, synthetic=True)
    train(directory, config)
    evaluate(directory)
    return directory
