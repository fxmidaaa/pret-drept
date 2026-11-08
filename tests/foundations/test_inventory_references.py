"""Synthetic contract, exact artifact binding and local failure checks for v2."""

import copy
import json
import os
import sys

import pytest

from rent_contracts import ContractError, validate_document
from rent_contracts.inventory import MANIFEST_FILE, PARQUET_FILE
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data import release_io
from rent_data.candidates import (
    build_observation_candidate,
    observation_candidate_digest,
    observation_quality_report_digest,
    project_candidate_observations,
    validate_observation_candidate,
)
from rent_data.inventory_io import InventoryLimits, write_observation_inventory
from rent_data.release_io import (
    COMPLETION_FILE,
    finalize_restoration,
    payload_inventory,
    read_verified_restore,
    verify_payload,
    write_payload,
)
from rent_data.releases import (
    DVC_VERSION,
    ReleaseError,
    build_dataset_release,
    build_restoration_report,
    content_digest,
    dataset_release_digest,
    validate_dataset_release,
)
from rent_data.split_io import materialize_development_split, read_verified_development_split
from rent_data.splits import build_development_split

VERSION = "2.0.0"


def canonical_bytes(document):
    return canonical_json(document).encode("utf-8")


@pytest.fixture
def reference_case(tmp_path, release_input_factory):
    base = release_input_factory()
    rows = base["candidate"]["observations"]
    inventory = tmp_path / "inventory"
    description = write_observation_inventory(inventory, rows)
    candidate = build_observation_candidate(
        base["sources"], **base["recipe"], inventory_directory=inventory
    )
    return {
        "base": base,
        "rows": rows,
        "inventory": inventory,
        "description": description,
        "candidate": candidate,
        "arguments": {
            "source_documents": base["sources"],
            "expected_candidate_ref": candidate["candidate_digest"],
            "inventory_directory": inventory,
        },
    }


@pytest.fixture
def sealed_case(reference_case, tmp_path):
    root = tmp_path / "payload"
    artifacts = write_payload(root, reference_case["candidate"], **reference_case["arguments"])
    binding = {
        "metadata": {
            "commit": "a" * 40,
            "path": "payload.dvc",
            "digest": content_digest(b"synthetic metadata fixture"),
        },
        "dvc": {
            "version": DVC_VERSION,
            "hash_algorithm": "md5",
            "object_id": "b" * 32 + ".dir",
            "size_bytes": sum(row["size_bytes"] for row in artifacts),
            "file_count": len(artifacts),
            "tool_profile_ref": content_digest(b"synthetic tool profile"),
        },
    }
    release = build_dataset_release(
        reference_case["candidate"],
        source_documents=reference_case["base"]["sources"],
        inventory_directory=root / "inventory",
        binding=binding,
        artifacts=artifacts,
    )
    return {**reference_case, "root": root, "release": release, "binding": binding}


def test_v2_candidate_preserves_v1_facts_and_is_deterministic(reference_case, tmp_path):
    case = reference_case
    candidate, base = case["candidate"], case["base"]
    validate_document("observation-candidate-v2", candidate)
    assert candidate["contract_version"] == VERSION
    assert candidate["inventory"] == case["description"]
    assert "observations" not in candidate
    for key in ("observations_digest", "sources", "lineage", "quality_report"):
        assert candidate[key] == base["candidate"][key]
    assert candidate["candidate_digest"] != base["candidate"]["candidate_digest"]

    copied = tmp_path / "same-inventory"
    copied.mkdir()
    for name in (MANIFEST_FILE, PARQUET_FILE):
        (copied / name).write_bytes((case["inventory"] / name).read_bytes())
    rebuilt = build_observation_candidate(
        base["sources"][::-1], **base["recipe"], inventory_directory=copied
    )
    assert canonical_bytes(candidate) == canonical_bytes(rebuilt)
    projection = project_candidate_observations(candidate, **case["arguments"])
    assert canonical_bytes(projection) == canonical_bytes(case["rows"])
    projection[0]["property_identity"]["policy_ref"] = "synthetic mutation"
    assert project_candidate_observations(candidate, **case["arguments"]) == case["rows"]


def test_same_logical_inventory_with_different_bytes_is_a_new_candidate(reference_case, tmp_path):
    case = reference_case
    alternate = tmp_path / "alternate"
    manifest = write_observation_inventory(
        alternate, case["rows"], limits=InventoryLimits(batch_rows=1)
    )
    assert manifest["observations_digest"] == case["description"]["observations_digest"]
    assert manifest["artifact"]["digest"] != case["description"]["artifact"]["digest"]
    rebuilt = build_observation_candidate(
        case["base"]["sources"], **case["base"]["recipe"], inventory_directory=alternate
    )
    assert rebuilt["candidate_digest"] != case["candidate"]["candidate_digest"]
    assert rebuilt["quality_report"] == case["candidate"]["quality_report"]

    # A physical substitution must fail before attempting to open Parquet.
    (alternate / PARQUET_FILE).unlink()
    os.mkfifo(alternate / PARQUET_FILE)
    with pytest.raises(ContractError, match="manifest identity mismatch"):
        project_candidate_observations(
            case["candidate"], **{**case["arguments"], "inventory_directory": alternate}
        )


@pytest.mark.parametrize("change", ["population", "fact", "numeric-representation"])
def test_valid_inventory_with_different_source_population_is_rejected(
    reference_case, tmp_path, change
):
    case = reference_case
    rows = copy.deepcopy(case["rows"])
    if change == "population":
        rows.pop()
    elif change == "fact":
        rows[-1]["domain_status"] = "unresolved"
    else:
        # A JSON number that compares equal in Python must still change identity.
        rows[0]["property_identity"]["confidence"] = 1
        sources = [json.loads(raw) for raw in case["base"]["sources"]]
        sources[0]["records"][0]["observation"]["property_identity"]["confidence"] = 1.0
        case["base"]["sources"] = [canonical_bytes(source) for source in sources]
    alternate = tmp_path / "alternate"
    write_observation_inventory(alternate, rows)
    with pytest.raises(ContractError, match="expected observation inventory identity mismatch"):
        build_observation_candidate(
            case["base"]["sources"], **case["base"]["recipe"], inventory_directory=alternate
        )


def test_self_consistent_file_hash_does_not_hide_an_incorrect_logical_digest(
    reference_case, tmp_path
):
    case = reference_case
    rows = copy.deepcopy(case["rows"])
    rows[-1]["domain_status"] = "unresolved"
    alternate = tmp_path / "alternate"
    forged = write_observation_inventory(alternate, rows)
    forged["observations_digest"] = case["candidate"]["observations_digest"]
    (alternate / MANIFEST_FILE).write_bytes(canonical_bytes(forged))
    with pytest.raises(ContractError, match="inventory population or digest mismatch"):
        build_observation_candidate(
            case["base"]["sources"], **case["base"]["recipe"], inventory_directory=alternate
        )


@pytest.mark.parametrize("change", ["lineage", "report", "source-wire"])
def test_resealing_does_not_bypass_source_correspondence(reference_case, change):
    candidate = copy.deepcopy(reference_case["candidate"])
    arguments = reference_case["arguments"].copy()
    if change == "lineage":
        candidate["lineage"][0]["source_record_id"] = "synthetic-substitute"
    elif change == "report":
        report = candidate["quality_report"]
        report["listing_count"] += 1
        report["report_digest"] = observation_quality_report_digest(report)
    else:
        arguments["source_documents"] = [
            reference_case["base"]["sources"][0] + b" ",
            reference_case["base"]["sources"][1],
        ]
    candidate["candidate_digest"] = observation_candidate_digest(candidate)
    arguments["expected_candidate_ref"] = candidate["candidate_digest"]
    with pytest.raises(ContractError, match="source correspondence mismatch"):
        validate_observation_candidate(candidate, **arguments)


def test_source_envelope_and_aggregate_limits_are_distinct(reference_case):
    case = reference_case
    for sources, error in (
        ([b" " * (MAX_DOCUMENT_BYTES + 1)], "document size limit"),
        ([b" " * MAX_DOCUMENT_BYTES] * 4 + [b" "], "source inventory size limit"),
    ):
        with pytest.raises(ContractError, match=error):
            build_observation_candidate(
                sources, **case["base"]["recipe"], inventory_directory=case["inventory"]
            )


@pytest.mark.parametrize(
    "change", ["missing", "altered", "manifest-metadata", "manifest-wire", "unsafe-leaf", "extra"]
)
def test_inventory_changes_fail_before_any_projection(reference_case, tmp_path, change):
    case = reference_case
    parquet = case["inventory"] / PARQUET_FILE
    manifest_path = case["inventory"] / MANIFEST_FILE
    if change == "missing":
        manifest_path.unlink()
    elif change == "altered":
        raw = parquet.read_bytes()
        parquet.write_bytes(raw[:4] + bytes([raw[4] ^ 1]) + raw[5:])
    elif change == "manifest-metadata":
        manifest = copy.deepcopy(case["description"])
        manifest["observation_count"] += 1
        manifest_path.write_bytes(canonical_bytes(manifest))
    elif change == "manifest-wire":
        manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
    elif change == "unsafe-leaf":
        target = tmp_path / "synthetic-outside"
        parquet.rename(target)
        parquet.symlink_to(target)
    else:
        (case["inventory"] / "synthetic-unlisted").touch()
    with pytest.raises(ContractError) as error:
        project_candidate_observations(case["candidate"], **case["arguments"])
    assert str(tmp_path) not in str(error.value)


def test_version_pairing_and_resolved_inventory_paths(reference_case, tmp_path, monkeypatch):
    case = reference_case
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    for path in (alias / "inventory", case["inventory"] / ".." / "inventory"):
        with pytest.raises(ReleaseError, match="INVALID_DIRECTORY"):
            validate_observation_candidate(
                case["candidate"], **{**case["arguments"], "inventory_directory": path}
            )
    with pytest.raises(ContractError, match="version and inventory directory mismatch"):
        project_candidate_observations(
            case["candidate"],
            source_documents=case["base"]["sources"],
            expected_candidate_ref=case["candidate"]["candidate_digest"],
        )
    inline = case["base"]["candidate"]
    with pytest.raises(ContractError, match="version and inventory directory mismatch"):
        validate_observation_candidate(
            inline, **{**case["arguments"], "expected_candidate_ref": inline["candidate_digest"]}
        )
    for invalid in (
        {**case["candidate"], "observations": case["rows"]},
        {**case["candidate"], "contract_version": "3.0.0"},
        {key: value for key, value in case["candidate"].items() if key != "inventory"},
    ):
        with pytest.raises(ContractError, match="contract violation"):
            validate_observation_candidate(invalid, **case["arguments"])
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    assert build_observation_candidate(case["base"]["sources"], **case["base"]["recipe"]) == inline


def test_v2_release_binds_the_exact_inventory_files_and_preserves_v1_roster(sealed_case):
    case = sealed_case
    release, root = case["release"], case["root"]
    validate_document("dataset-release-v2", release)
    assert release["contract_version"] == VERSION
    assert release["inventory"] == case["candidate"]["inventory"]
    by_path = {artifact["path"]: artifact for artifact in release["artifacts"]}
    for name in (MANIFEST_FILE, PARQUET_FILE):
        path = f"inventory/{name}"
        raw = (case["inventory"] / name).read_bytes()
        assert (root / path).read_bytes() == raw
        assert by_path[path] == {
            "path": path,
            "size_bytes": len(raw),
            "digest": content_digest(raw),
        }
    assert len(by_path) == 4 + len(case["base"]["sources"])
    assert (
        verify_payload(release, root, expected_release_ref=release["release_digest"])
        == case["candidate"]
    )
    with pytest.raises(ContractError, match="expected dataset release identity mismatch"):
        verify_payload(release, root, expected_release_ref=content_digest(b"other release"))
    with pytest.raises(ReleaseError, match="UNEXPECTED_PAYLOAD_PATH"):
        payload_inventory(root)
    with pytest.raises(ContractError, match="contract violation"):
        validate_document("dataset-release", release)


@pytest.mark.parametrize("change", ["missing", "wrong-path", "wrong-digest", "count", "float-size"])
def test_invalid_inventory_release_declarations_fail_even_when_resealed(sealed_case, change):
    release = copy.deepcopy(sealed_case["release"])
    parquet = next(
        row for row in release["artifacts"] if row["path"] == f"inventory/{PARQUET_FILE}"
    )
    if change == "missing":
        release["artifacts"].remove(parquet)
    elif change == "wrong-path":
        parquet["path"] = "inventory/../synthetic-secret.parquet"
    elif change == "wrong-digest":
        parquet["digest"] = content_digest(b"synthetic substitute")
    elif change == "count":
        release["observation_count"] += 1
    else:
        parquet["size_bytes"] = float(parquet["size_bytes"])
    release["release_digest"] = dataset_release_digest(release)
    with pytest.raises(ContractError) as error:
        validate_dataset_release(release, expected_release_ref=release["release_digest"])
    assert "synthetic-secret" not in str(error.value)


def test_release_rejects_a_resealed_same_population_physical_substitution(sealed_case, tmp_path):
    case = sealed_case
    other = tmp_path / "alternate"
    alternate = write_observation_inventory(
        other, case["rows"], limits=InventoryLimits(batch_rows=1)
    )
    for name in (MANIFEST_FILE, PARQUET_FILE):
        (case["root"] / "inventory" / name).write_bytes((other / name).read_bytes())
    release = copy.deepcopy(case["release"])
    release["inventory"] = alternate
    release["artifacts"] = payload_inventory(case["root"], contract_version=VERSION)
    release["dvc"]["size_bytes"] = sum(row["size_bytes"] for row in release["artifacts"])
    release["release_digest"] = dataset_release_digest(release)
    assert release["release_digest"] != case["release"]["release_digest"]
    validate_dataset_release(release, expected_release_ref=release["release_digest"])
    with pytest.raises(ContractError, match="release candidate inventory identity mismatch"):
        finalize_restoration(
            tmp_path,
            build_restoration_report(release),
            manifest=release,
            expected_release_ref=release["release_digest"],
        )
    assert not (tmp_path / COMPLETION_FILE).exists()


def test_release_builder_requires_verified_inventory_bytes(sealed_case):
    case = sealed_case
    staged = case["root"] / "inventory"
    (staged / PARQUET_FILE).unlink()
    with pytest.raises(ContractError, match="incomplete local inventory"):
        build_dataset_release(
            case["candidate"],
            source_documents=case["base"]["sources"],
            inventory_directory=staged,
            binding=case["binding"],
            artifacts=case["release"]["artifacts"],
        )


def test_existing_output_and_overlap_are_rejected_before_writes(sealed_case):
    case = sealed_case
    before = payload_inventory(case["root"], contract_version=VERSION)
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        write_payload(case["root"], case["candidate"], **case["arguments"])
    child = case["inventory"] / "nested"
    with pytest.raises(ReleaseError, match="OVERLAPPING_INVENTORY_PAYLOAD"):
        write_payload(child, case["candidate"], **case["arguments"])
    assert not child.exists()
    assert payload_inventory(case["root"], contract_version=VERSION) == before


def test_interrupted_payload_finalization_leaves_no_candidate(
    reference_case, tmp_path, monkeypatch
):
    case = reference_case
    root = tmp_path / "payload"

    def fail(*args):
        raise OSError("synthetic sensitive destination")

    monkeypatch.setattr(os, "link", fail)
    with pytest.raises(ReleaseError, match="FINALIZATION_FAILED") as error:
        write_payload(root, case["candidate"], **case["arguments"])
    assert "synthetic sensitive destination" not in str(error.value)
    assert not (root / "candidate.json").exists()
    assert not (tmp_path / COMPLETION_FILE).exists()
    assert not list(tmp_path.glob(".artifact-*"))


def test_parquet_copy_is_rechecked_before_the_candidate_is_installed(
    reference_case, tmp_path, monkeypatch
):
    case = reference_case
    root = tmp_path / "payload"
    copy_parquet = release_io._copy_parquet

    def corrupt_copy(source, destination, size_bytes):
        copy_parquet(source, destination, size_bytes)
        with destination.open("r+b") as stream:
            stream.write(b"FAIL")

    monkeypatch.setattr(release_io, "_copy_parquet", corrupt_copy)
    with pytest.raises(ReleaseError, match="ARTIFACT_INTEGRITY_MISMATCH"):
        write_payload(root, case["candidate"], **case["arguments"])
    assert not (root / "candidate.json").exists()


def test_failed_staging_cleanup_stays_outside_the_closed_payload(
    reference_case, tmp_path, monkeypatch
):
    case = reference_case
    root = tmp_path / "payload"

    def fail(*args):
        raise OSError("synthetic cleanup failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "unlink", fail)
        artifacts = write_payload(root, case["candidate"], **case["arguments"])
    assert len(list(tmp_path.glob(".artifact-*"))) == 1
    assert payload_inventory(root, contract_version=VERSION) == artifacts


def test_reader_reverifies_the_inventory_after_completion(sealed_case, tmp_path):
    case = sealed_case
    release = case["release"]
    arguments = {"manifest": release, "expected_release_ref": release["release_digest"]}
    with pytest.raises(ReleaseError, match="ARTIFACT_UNAVAILABLE"):
        read_verified_restore(tmp_path, **arguments)
    finalize_restoration(tmp_path, build_restoration_report(release), **arguments)
    assert read_verified_restore(tmp_path, **arguments) == case["candidate"]
    marker = (tmp_path / COMPLETION_FILE).read_bytes()
    (case["root"] / "inventory" / PARQUET_FILE).write_bytes(b"synthetic altered Parquet")
    with pytest.raises(ContractError):
        read_verified_restore(tmp_path, **arguments)
    assert (tmp_path / COMPLETION_FILE).read_bytes() == marker


def test_development_split_entry_points_reject_unsupported_release_versions(
    sealed_case, split_input_factory, tmp_path
):
    """V2 acceptance and parity are covered in test_reference_splits.py."""
    case = sealed_case
    release = case["release"]
    finalize_restoration(
        tmp_path,
        build_restoration_report(release),
        manifest=release,
        expected_release_ref=release["release_digest"],
    )
    unsupported = copy.deepcopy(release)
    unsupported["contract_version"] = "3.0.0"
    unsupported["release_digest"] = dataset_release_digest(unsupported)
    split = split_input_factory()
    arguments = {
        "release": unsupported,
        "policy": split["policy"],
        "expected_policy_ref": split["policy"]["policy_digest"],
        "expected_release_ref": unsupported["release_digest"],
    }
    message = "dataset-release contract violation"
    with pytest.raises(ContractError, match=message):
        build_development_split(observations=case["rows"], **arguments, **split["parameters"])
    destination = tmp_path.parent / f"{tmp_path.name}-split"
    with pytest.raises(ContractError, match=message):
        materialize_development_split(tmp_path, destination, **arguments, **split["parameters"])
    assert not destination.exists()
    destination.mkdir()
    with pytest.raises(ContractError, match=message):
        read_verified_development_split(
            destination,
            restored_directory=tmp_path,
            expected_split_ref=content_digest(b"unused synthetic split identity"),
            **arguments,
        )
    assert not list(destination.iterdir())
