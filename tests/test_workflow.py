import json
import os
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from features import categorical
from mlops.evaluate import evaluate
from mlops.prepare import GROUP_COLUMNS, prepare
from predict import load_bundle, model_matrix, predict_eur
from train import EMPTY_COLUMN_DEFAULTS, train


def test_preparation_keeps_reposts_together_and_excludes_unknown_currency(tmp_path):
    fixture = pd.read_csv("data/sample/demo.csv")
    invalid = fixture.iloc[[0]].assign(price_unit="UNKNOWN")
    source = tmp_path / "listings.csv"
    pd.concat([fixture, invalid], ignore_index=True).to_csv(source, index=False)

    prepare(
        source,
        tmp_path / "prepared",
        json.loads(Path("params.json").read_text()),
        synthetic=True,
    )
    output = tmp_path / "prepared"
    train = pd.read_csv(output / "train.csv", dtype={name: str for name in categorical})
    evaluation = pd.read_csv(
        output / "evaluation.csv", dtype={name: str for name in categorical}
    )
    manifest = json.loads((output / "dataset.json").read_text())

    train_keys = set(train[GROUP_COLUMNS].itertuples(index=False, name=None))
    evaluation_keys = set(evaluation[GROUP_COLUMNS].itertuples(index=False, name=None))
    assert train_keys.isdisjoint(evaluation_keys)
    assert manifest["excluded_rows"] == 1
    assert len(train) + len(evaluation) == len(fixture)
    assert manifest["input_sha256"] == sha256(source.read_bytes()).hexdigest()


def test_dvc_evaluation_matches_reloaded_model():
    directory = Path(
        os.environ.get("PRET_DREPT_MODEL", "artifacts/demo/model.joblib")
    ).parent
    report_path = directory / "evaluation.json"
    if not report_path.is_file():
        pytest.skip("Build and evaluate the configured model first.")

    model_path = directory / "model.joblib"
    bundle = load_bundle(model_path)
    train = pd.read_csv(
        directory / "train.csv", dtype={name: str for name in categorical}
    )
    evaluation = pd.read_csv(
        directory / "evaluation.csv", dtype={name: str for name in categorical}
    )
    report = json.loads(report_path.read_text())
    predictions = predict_eur(
        model_matrix(evaluation.to_dict(orient="records"), bundle), bundle
    )
    errors = predictions - evaluation["price"].to_numpy()

    assert bundle["numeric_defaults"]["area"] == train["area"].median()
    assert (
        report["dataset"]
        == json.loads((directory / "dataset.json").read_text())["dataset"]
    )
    assert (
        report["lineage"]["model_sha256"] == sha256(model_path.read_bytes()).hexdigest()
    )
    assert report["metrics"]["mae_eur"] == pytest.approx(np.abs(errors).mean())
    assert report["metrics"]["rmse_eur"] == pytest.approx(np.sqrt((errors**2).mean()))


def test_training_with_only_required_listing_fields(tmp_path):
    from mlops.prepare import REQUIRED_COLUMNS

    source = tmp_path / "listings.csv"
    pd.read_csv("data/sample/demo.csv")[sorted(REQUIRED_COLUMNS)].to_csv(
        source, index=False
    )
    config = json.loads(Path("params.json").read_text())
    output = tmp_path / "run"
    prepare(source, output, config, synthetic=True)
    train(output, config)
    evaluate(output)

    bundle = load_bundle(output / "model.joblib")
    assert all(
        bundle["numeric_defaults"][key] == value
        for key, value in EMPTY_COLUMN_DEFAULTS.items()
    )
    assert np.isfinite(
        json.loads((output / "evaluation.json").read_text())["metrics"]["mae_eur"]
    )


def test_rebuilding_preserves_files_linked_to_a_dvc_cache(tmp_path):
    directory = tmp_path / "run"
    config = json.loads(Path("params.json").read_text())
    prepare(Path("data/sample/demo.csv"), directory, config, synthetic=True)
    train(directory, config)
    evaluate(directory)
    cached = {}
    for name in (
        "train.csv",
        "evaluation.csv",
        "dataset.json",
        "model.joblib",
        "evaluation.json",
    ):
        link = tmp_path / name
        os.link(directory / name, link)
        cached[link] = link.read_bytes()

    config["seed"] += 1
    prepare(Path("data/sample/demo.csv"), directory, config, synthetic=True)
    train(directory, config)
    evaluate(directory)

    for path, content in cached.items():
        assert path.read_bytes() == content
    assert (directory / "train.csv").read_bytes() != cached[tmp_path / "train.csv"]


@pytest.mark.parametrize("changed", ["evaluation.csv", "dataset.json"])
def test_evaluation_rejects_changed_data(tmp_path, changed):
    import shutil

    demo = Path("artifacts/demo")
    if not (demo / "model.joblib").exists():
        pytest.skip("Run the fixture stage commands first.")
    for name in ("model.joblib", "evaluation.csv", "dataset.json"):
        shutil.copy2(demo / name, tmp_path / name)
    if changed == "evaluation.csv":
        with (tmp_path / changed).open("a") as stream:
            stream.write("\n")
    else:
        dataset = json.loads((tmp_path / changed).read_text())
        dataset["training_sha256"] = "different-training-data"
        (tmp_path / changed).write_text(json.dumps(dataset))
    with pytest.raises(ValueError, match="differs|lineage"):
        evaluate(tmp_path)
    assert not (tmp_path / "evaluation.json").exists()


def test_batch_worker_preserves_rows_and_uses_the_saved_model():
    from functools import partial

    import cloudpickle

    from mlops.batch import PREDICTION_COLUMN, predict_batches

    demo = Path("artifacts/demo")
    if not (demo / "model.joblib").exists():
        pytest.skip("Run the fixture stage commands first.")
    bundle = load_bundle(demo / "model.joblib")
    inputs = pd.read_csv(
        demo / "evaluation.csv", dtype={name: str for name in categorical}
    ).drop(columns="price")
    inputs["listing_key"] = [f"row-{i}" for i in range(len(inputs))]
    expected = predict_eur(model_matrix(inputs.to_dict("records"), bundle), bundle)
    # Spark ships this function and its model to a Python worker.
    worker = cloudpickle.loads(
        cloudpickle.dumps(partial(predict_batches, bundle=bundle))
    )
    result = pd.concat(
        worker(iter([inputs.iloc[:0], inputs.iloc[:5], inputs.iloc[5:]]))
    )
    pd.testing.assert_frame_equal(result.drop(columns=PREDICTION_COLUMN), inputs)
    np.testing.assert_array_equal(result[PREDICTION_COLUMN], expected)

    with pytest.raises(ValueError, match="Each listing needs"):
        list(worker(iter([inputs.assign(area=-1)])))
