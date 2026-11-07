"""Synthetic wire, population, and local transport checks."""

import copy
import hashlib
import json
import os
import subprocess
import sys

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from rent_contracts import ContractError
from rent_contracts.evaluation import ObservationInventoryHasher, observation_inventory_digest
from rent_contracts.inventory import MANIFEST_FILE, PARQUET_FILE, validate_inventory_manifest
from rent_contracts.validation import MAX_DOCUMENT_BYTES
from rent_data import _inventory_parquet as parquet_profile
from rent_data import inventory_io
from rent_data.inventory_io import (
    InventoryLimits,
    iter_verified_observations,
    verify_observation_inventory,
    write_observation_inventory,
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@pytest.fixture
def rows(release_input_factory):
    return release_input_factory()["candidate"]["observations"]


@pytest.fixture
def artifact(tmp_path, rows):
    root = tmp_path / "inventory"
    manifest = write_observation_inventory(root, iter(rows), limits=InventoryLimits(batch_rows=2))
    return root, manifest, _digest(_canonical(rows))


def _bind_physical_file(root, manifest):
    raw = (root / PARQUET_FILE).read_bytes()
    manifest["artifact"].update(digest=_digest(raw), size_bytes=len(raw))
    (root / MANIFEST_FILE).write_bytes(_canonical(manifest))


def _fixture_parquet(root, table, *, metadata=None, **overrides):
    profile = {
        "version": "2.6",
        "compression": "NONE",
        "use_dictionary": False,
        "write_statistics": False,
        "store_schema": False,
        "write_page_checksum": True,
    }
    with pq.ParquetWriter(root / PARQUET_FILE, table.schema, **(profile | overrides)) as writer:
        writer.write_table(table, row_group_size=2)
        if metadata is not None:
            writer.add_key_value_metadata(metadata)


def test_lossless_round_trip_matches_v1_and_independent_digest(tmp_path, rows):
    original = rows[0]
    for index, confidence in enumerate((0, 1, 0.0, 1.0, -0.0, 0.125, 5e-324), start=4):
        row = copy.deepcopy(original)
        row.update(
            observation_id=f"synthetic-numeric-{index:02d}",
            listing_id=f"synthetic-listing-{index}",
            collected_at="2026-01-10T14:00:00.120+02:00",
            features_available_at="2026-01-10T12:00:00.120000Z",
        )
        row["property_identity"].update(status="probable", confidence=confidence)
        rows.append(row)
    expected = _digest(_canonical(rows))
    assert observation_inventory_digest(list(reversed(rows))) == expected
    physical_digests = set()
    for batch_rows in (1, 4):
        root = tmp_path / f"batch-{batch_rows}"
        manifest = write_observation_inventory(
            root, iter(rows), limits=InventoryLimits(batch_rows=batch_rows)
        )
        assert manifest == {
            "contract_version": "1.0.0",
            "observation_contract_version": "1.0.0",
            "schema_profile": "observation-reference-parquet-v1",
            "writer_profile": "pyarrow-26.0.1-parquet-2.6-uncompressed-v1",
            "observation_count": len(rows),
            "observations_digest": expected,
            "artifact": {
                "path": "observations.parquet",
                "size_bytes": (root / PARQUET_FILE).stat().st_size,
                "digest": _digest((root / PARQUET_FILE).read_bytes()),
            },
        }
        assert (root / MANIFEST_FILE).read_bytes() == _canonical(manifest)
        assert verify_observation_inventory(root, expected_inventory_ref=expected) == manifest
        restored = list(
            iter_verified_observations(
                root, expected_inventory_ref=expected, limits=InventoryLimits(batch_rows=3)
            )
        )
        # Ordinary dict equality conflates integers, floats and signed zeros.
        assert _canonical(restored) == _canonical(rows)
        physical_digests.add(manifest["artifact"]["digest"])
    assert len(physical_digests) == 2


def test_writer_consumes_mutable_reused_rows_at_yield_time(tmp_path, rows):
    def reused_row():
        buffer = {}
        identity = {}
        for row in rows:
            buffer.update(row)
            identity.update(row["property_identity"])
            buffer["property_identity"] = identity
            yield buffer

    root = tmp_path / "inventory"
    expected = _digest(_canonical(rows))
    write_observation_inventory(root, reused_row())
    assert _canonical(list(iter_verified_observations(root, expected_inventory_ref=expected))) == (
        _canonical(rows)
    )


def test_large_inventory_exceeds_v1_json_and_round_trips(tmp_path, large_observation_inventory):
    rows = large_observation_inventory
    raw = _canonical(rows)
    assert len(raw) > MAX_DOCUMENT_BYTES
    with pytest.raises(ContractError, match="document size limit exceeded"):
        observation_inventory_digest(rows)
    root = tmp_path / "large"
    expected = _digest(raw)
    manifest = write_observation_inventory(root, iter(rows), limits=InventoryLimits(batch_rows=257))
    assert manifest["observation_count"] == 1_800
    assert manifest["artifact"]["size_bytes"] > MAX_DOCUMENT_BYTES
    assert manifest["observations_digest"] == expected
    restored = iter_verified_observations(
        root, expected_inventory_ref=expected, limits=InventoryLimits(batch_rows=31)
    )
    for wanted, actual in zip(rows, restored, strict=True):
        assert _canonical(wanted) == _canonical(actual)


def test_fresh_processes_use_same_pinned_profile_and_optional_backend(tmp_path, artifact, rows):
    root, _, expected = artifact
    code = """
import json, sys
sys.path[:] = json.loads(sys.argv[1])
from pathlib import Path
from rent_contracts.evaluation import observation_inventory_digest
from rent_data.inventory_io import InventoryLimits, iter_verified_observations, write_observation_inventory
assert 'pyarrow' not in sys.modules
rows = json.load(sys.stdin)
expected = sys.argv[3]
assert observation_inventory_digest(rows) == expected
destination = Path(sys.argv[2])
write_observation_inventory(destination, iter(rows), limits=InventoryLimits(batch_rows=2))
assert list(iter_verified_observations(destination, expected_inventory_ref=expected)) == rows
"""
    for seed in ("1", "97"):
        destination = tmp_path / f"process-{seed}"
        subprocess.run(
            [
                sys.executable,
                "-S",
                "-P",
                "-c",
                code,
                json.dumps(sys.path),
                str(destination),
                expected,
            ],
            input=_canonical(rows),
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            check=True,
            timeout=20,
        )
        for path in (MANIFEST_FILE, PARQUET_FILE):
            assert (root / path).read_bytes() == (destination / path).read_bytes()


def test_missing_optional_backend_has_setup_diagnostic(tmp_path, rows, monkeypatch):
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    destination = tmp_path / "missing-backend"
    with pytest.raises(ContractError, match="install the parquet extra"):
        write_observation_inventory(destination, rows)
    assert not (destination / MANIFEST_FILE).exists()


def test_writer_sanitizes_a_source_interruption(tmp_path, rows):
    def broken_source():
        yield rows[0]
        raise RuntimeError("synthetic-marker")

    root = tmp_path / "interrupted-source"
    with pytest.raises(ContractError, match="inventory observation source failed") as error:
        write_observation_inventory(root, broken_source(), limits=InventoryLimits(batch_rows=1))
    assert "synthetic-marker" not in str(error.value)
    assert not (root / MANIFEST_FILE).exists()


def test_incremental_digest_has_a_nonempty_bounded_population(rows):
    hasher = ObservationInventoryHasher(max_records=2)
    with pytest.raises(ContractError, match="nonempty"):
        hasher.digest()
    hasher.add(rows[0])
    with pytest.raises(ContractError, match="duplicate observation"):
        hasher.add(rows[0])
    assert hasher.digest() == _digest(_canonical(rows[:1]))
    hasher.add(rows[1])
    with pytest.raises(ContractError, match="record limit"):
        hasher.add(rows[2])
    assert hasher.count == 2
    assert hasher.digest() == _digest(_canonical(rows[:2]))


@pytest.mark.parametrize(
    ("violation", "diagnostic"),
    [
        ("empty", "nonempty"),
        ("unordered", "strictly increasing"),
        ("duplicate", "duplicate observation"),
        ("capture", "duplicate listing collection instant"),
        ("property", "conflicting confirmed listing property"),
        ("target", "observation-reference contract violation"),
        ("calendar", "observation-reference contract violation|unsupported contract timestamp"),
        ("nonfinite", "nonfinite JSON number"),
        ("record-limit", "record limit"),
    ],
)
def test_invalid_writer_population_never_finalizes(tmp_path, rows, violation, diagnostic):
    destination = tmp_path / "failed"
    if violation == "empty":
        rows.clear()
    elif violation == "unordered":
        rows.reverse()
    elif violation == "duplicate":
        rows[-1]["observation_id"] = rows[-2]["observation_id"]
    elif violation == "capture":
        rows[-1].update(listing_id=rows[0]["listing_id"], collected_at="2026-01-10T14:00:00+02:00")
    elif violation == "property":
        rows[-1]["listing_id"] = rows[0]["listing_id"]
    elif violation == "target":
        rows[-1]["target"] = "synthetic-marker"
    elif violation == "calendar":
        rows[-1]["collected_at"] = "2026-02-30T12:00:00Z"
    elif violation == "nonfinite":
        rows[-1]["property_identity"]["confidence"] = float("nan")
    limits = InventoryLimits(max_records=3 if violation == "record-limit" else 4, batch_rows=1)
    with pytest.raises(ContractError, match=diagnostic) as failure:
        write_observation_inventory(destination, iter(rows), limits=limits)
    assert "synthetic-marker" not in str(failure.value)
    assert not (destination / MANIFEST_FILE).exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_records", 100_001),
        ("max_records", 0),
        ("max_file_bytes", True),
        ("max_file_bytes", 128 * 1024 * 1024 + 1),
        ("batch_rows", 1.0),
        ("batch_rows", 2_049),
    ],
)
def test_local_limits_are_strict_and_can_only_be_lowered(field, value):
    with pytest.raises(ContractError, match="invalid observation inventory limits"):
        InventoryLimits(**{field: value})


@pytest.mark.parametrize("limit", [1, 400, 2_000])
def test_byte_cap_applies_to_all_writer_bytes(tmp_path, rows, limit):
    root = tmp_path / "limited"
    with pytest.raises(ContractError, match="Parquet file limit exceeded"):
        write_observation_inventory(root, rows, limits=InventoryLimits(max_file_bytes=limit))
    assert (root / PARQUET_FILE).stat().st_size <= limit
    assert not (root / MANIFEST_FILE).exists()


def test_writer_stops_at_row_group_limit(tmp_path, rows, monkeypatch):
    monkeypatch.setattr(parquet_profile, "MAX_ROW_GROUPS", 1)
    root = tmp_path / "group-limit"
    with pytest.raises(ContractError, match="Parquet row group limit exceeded"):
        write_observation_inventory(root, rows, limits=InventoryLimits(batch_rows=2))
    assert not (root / MANIFEST_FILE).exists()


@pytest.mark.parametrize("kind", ["records", "bytes"])
def test_manifest_is_checked_against_caller_limits(artifact, kind):
    root, manifest, expected = artifact
    limits = (
        InventoryLimits(max_records=manifest["observation_count"] - 1)
        if kind == "records"
        else InventoryLimits(max_file_bytes=manifest["artifact"]["size_bytes"] - 1)
    )
    with pytest.raises(ContractError, match="exceeds local limits"):
        verify_observation_inventory(root, expected_inventory_ref=expected, limits=limits)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_version", "2.0.0"),
        ("observation_contract_version", "2.0.0"),
        ("schema_profile", "guessed-schema"),
        ("writer_profile", "guessed-writer"),
        ("observation_count", True),
        ("observation_count", 4.0),
        ("observation_count", 100_001),
        ("observations_digest", "sha256:" + "f" * 63 + "\n"),
        ("source_path", "/private/synthetic-marker"),
        ("artifact.path", "../observations.parquet"),
        ("artifact.path", "/private/synthetic-marker"),
        ("artifact.size_bytes", 134_217_729),
        ("artifact.size_bytes", 5_000.0),
        ("artifact.digest", "sha256:" + "g" * 64),
        ("artifact.target", "synthetic-marker"),
    ],
)
def test_manifest_is_closed_versioned_and_bounded(artifact, field, value):
    _, manifest, expected = artifact
    if field.startswith("artifact."):
        manifest["artifact"][field.removeprefix("artifact.")] = value
    else:
        manifest[field] = value
    with pytest.raises(ContractError) as failure:
        validate_inventory_manifest(manifest, expected_inventory_ref=expected)
    assert "synthetic-marker" not in str(failure.value)


@pytest.mark.parametrize("corruption", ["duplicate-key", "noncanonical", "oversized", "other-ref"])
def test_reader_rejects_untrusted_manifest(artifact, corruption):
    root, manifest, expected = artifact
    path = root / MANIFEST_FILE
    raw = path.read_bytes()
    if corruption == "duplicate-key":
        raw = b'{"observation_count":4,' + raw[1:]
    elif corruption == "noncanonical":
        raw += b"\n"
    elif corruption == "oversized":
        raw += b" " * 8_192
    else:
        manifest["observations_digest"] = _digest(b"different synthetic population")
        raw = _canonical(manifest)
    path.write_bytes(raw)
    with pytest.raises(ContractError):
        verify_observation_inventory(root, expected_inventory_ref=expected)


@pytest.mark.parametrize(
    ("change", "diagnostic"),
    [
        ("digest", "file integrity mismatch"),
        ("footer", "oversized inventory Parquet footer"),
        ("count", "count or row group limit mismatch"),
        ("extra-column", "schema or profile mismatch"),
        ("timestamp-type", "schema or profile mismatch"),
        ("key-metadata", "schema or profile mismatch"),
        ("compression", "column layout mismatch"),
        ("dictionary", "column layout mismatch"),
        ("statistics", "column layout mismatch"),
        ("checksum", "inventory Parquet read failed"),
        ("duplicate", "duplicate observation"),
        ("capture", "duplicate listing collection instant"),
        ("property", "conflicting confirmed listing property"),
        ("numeric-marker", "confidence representation"),
        ("signed-integer", "integer confidence"),
        ("changed-row", "population or digest mismatch"),
    ],
)
def test_rehashed_files_are_verified_before_first_row(artifact, change, diagnostic):
    root, manifest, expected = artifact
    path = root / PARQUET_FILE
    if change == "count":
        manifest["observation_count"] += 1
    elif change in {"digest", "footer", "checksum"}:
        raw = bytearray(path.read_bytes())
        if change == "footer":
            raw[-8:-4] = (8 * 1024 * 1024 + 1).to_bytes(4, "little")
        else:
            with pq.ParquetFile(path) as parquet:
                chunk = parquet.metadata.row_group(1).column(0)
                raw[chunk.data_page_offset + chunk.total_compressed_size - 1] ^= 1
        path.write_bytes(raw)
    else:
        with pq.ParquetFile(path) as parquet:
            table = parquet.read()
        if change == "extra-column":
            table = table.append_column("synthetic-target", pa.array([9] * len(table)))
        elif change == "timestamp-type":
            index = table.schema.get_field_index("collected_at")
            table = table.set_column(
                index, "collected_at", pa.nulls(len(table), pa.timestamp("us"))
            )
        elif change not in {"compression", "dictionary", "statistics", "key-metadata"}:
            raw_rows = table.to_pylist()
            first, last = raw_rows[0], raw_rows[-1]
            if change == "duplicate":
                last["observation_id"] = raw_rows[-2]["observation_id"]
            elif change == "capture":
                last.update(
                    listing_id=first["listing_id"], collected_at="2026-01-10T14:00:00+02:00"
                )
            elif change == "property":
                last["listing_id"] = first["listing_id"]
            elif change == "numeric-marker":
                last["property_identity"]["confidence_is_integer"] = True
            elif change == "signed-integer":
                last["property_identity"].update(confidence=-0.0, confidence_is_integer=True)
            else:
                last["domain_status"] = "valid"
            table = pa.Table.from_pylist(raw_rows, schema=table.schema)
        options = {"compression": "snappy"} if change == "compression" else {}
        if change == "dictionary":
            options["use_dictionary"] = True
        if change == "statistics":
            options["write_statistics"] = True
        if change == "key-metadata":
            options["metadata"] = {b"synthetic-extra": b"synthetic-marker"}
        _fixture_parquet(root, table, **options)
    if change != "digest":
        _bind_physical_file(root, manifest)
    with pytest.raises(ContractError, match=diagnostic):
        next(iter_verified_observations(root, expected_inventory_ref=expected))


@pytest.mark.parametrize(
    "kind",
    [
        "extra",
        "missing",
        "file-link",
        "manifest-link",
        pytest.param(
            "fifo", marks=pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
        ),
        "root-link",
    ],
)
def test_reader_rejects_incomplete_or_unsafe_artifact_rosters(tmp_path, artifact, kind):
    root, _, expected = artifact
    if kind == "extra":
        (root / "extra-directory").mkdir()
    elif kind == "missing":
        (root / MANIFEST_FILE).unlink()
    elif kind == "root-link":
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)
        root = link
    else:
        path = root / (MANIFEST_FILE if kind == "manifest-link" else PARQUET_FILE)
        outside = tmp_path / "outside"
        path.replace(outside)
        if kind == "fifo":
            os.mkfifo(path)
        else:
            path.symlink_to(outside)
    with pytest.raises(ContractError):
        verify_observation_inventory(root, expected_inventory_ref=expected)


def test_replacing_path_cannot_swap_second_pass_input(tmp_path, artifact, rows, monkeypatch):
    root, _, expected = artifact
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"synthetic replacement")
    decode = inventory_io.decoded_observations

    def replace_after_verification(reader, *, batch_rows):
        yield from decode(reader, batch_rows=batch_rows)
        if replacement.exists():
            replacement.replace(root / PARQUET_FILE)

    monkeypatch.setattr(inventory_io, "decoded_observations", replace_after_verification)
    assert list(iter_verified_observations(root, expected_inventory_ref=expected)) == rows
    with pytest.raises(ContractError, match="file integrity mismatch"):
        verify_observation_inventory(root, expected_inventory_ref=expected)


@pytest.mark.parametrize("failure", ["readback", "manifest-link"])
def test_write_interruption_does_not_finalize(tmp_path, rows, failure, monkeypatch):
    root = tmp_path / "interrupted"
    if failure == "readback":
        fsync = os.fsync

        def corrupt_before_sync(descriptor):
            with (root / PARQUET_FILE).open("r+b") as stream:
                stream.write(b"FAIL")
            fsync(descriptor)

        monkeypatch.setattr(os, "fsync", corrupt_before_sync)
    else:

        def fail_link(*args):
            raise OSError("synthetic-marker")

        monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(
        ContractError, match="invalid inventory Parquet framing|FINALIZATION_FAILED"
    ) as error:
        write_observation_inventory(root, rows)
    assert "synthetic-marker" not in str(error.value)
    assert {path.name for path in root.iterdir()} == {PARQUET_FILE}


def test_writer_refuses_existing_outputs_and_unsafe_paths(tmp_path, artifact, rows):
    root, _, _ = artifact
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    linked_parent = tmp_path / "link"
    linked_parent.symlink_to(root, target_is_directory=True)
    for destination in (root, linked_parent, linked_parent / "new", tmp_path / ".." / "new"):
        with pytest.raises(
            ContractError, match="output already exists|invalid local inventory path"
        ):
            write_observation_inventory(destination, rows)
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before


def test_writer_refuses_extra_artifacts_before_finalizing(tmp_path, rows):
    root = tmp_path / "unexpected-files"

    def source():
        yield from rows
        (root / "extra").write_bytes(b"synthetic extra")

    with pytest.raises(ContractError, match="unexpected local inventory artifact"):
        write_observation_inventory(root, source())
    assert not (root / MANIFEST_FILE).exists()
