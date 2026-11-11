import csv
import hashlib
import io
from pathlib import Path

import pytest

from mlops.dataset import stage_dataset
from mlops.files import write_json


def snapshot_fixture(directory: Path) -> tuple[Path, bytes, dict]:
    source = directory / "snapshot"
    source.mkdir()
    content = Path("data/sample/demo.csv").read_bytes()
    rows = sum(bool(row) for row in csv.reader(io.StringIO(content.decode()))) - 1
    manifest = {
        "status": "complete",
        "saved_rows": rows,
        "csv_sha256": hashlib.sha256(content).hexdigest(),
        "run_id": "test-snapshot",
    }
    (source / "listings.csv").write_bytes(content)
    write_json(source / "snapshot.json", manifest)
    return source, content, manifest


def test_selecting_snapshot_preserves_original_csv_and_manifest_bytes(tmp_path):
    source, content, _ = snapshot_fixture(tmp_path)
    output = tmp_path / "current"
    stage_dataset(source, output)
    assert (output / "listings.csv").read_bytes() == content
    assert (output / "snapshot.json").read_bytes() == (
        source / "snapshot.json"
    ).read_bytes()
    assert (source / "listings.csv").read_bytes() == content


@pytest.mark.parametrize("invalid", ["incomplete", "checksum", "row_count"])
def test_invalid_snapshot_does_not_replace_the_current_dataset(tmp_path, invalid):
    source, content, manifest = snapshot_fixture(tmp_path)
    output = tmp_path / "current"
    stage_dataset(source, output)
    original_manifest = (output / "snapshot.json").read_bytes()
    if invalid == "incomplete":
        manifest["status"] = "running"
    elif invalid == "checksum":
        manifest["csv_sha256"] = "different"
    else:
        manifest["saved_rows"] += 1
    write_json(source / "snapshot.json", manifest)
    with pytest.raises(ValueError, match="completed|differs"):
        stage_dataset(source, output)
    assert (output / "listings.csv").read_bytes() == content
    assert (output / "snapshot.json").read_bytes() == original_manifest


def test_preparation_checks_the_snapshot_before_writing_outputs(tmp_path):
    from mlops.config import load_config
    from mlops.prepare import prepare

    source, _, manifest = snapshot_fixture(tmp_path)
    manifest["csv_sha256"] = "different"
    write_json(source / "snapshot.json", manifest)
    with pytest.raises(ValueError, match="differs"):
        prepare(
            source / "listings.csv",
            tmp_path / "prepared",
            load_config(Path("params.json")),
            snapshot=source / "snapshot.json",
        )
    assert not (tmp_path / "prepared").exists()
