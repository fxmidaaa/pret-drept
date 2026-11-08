"""Synthetic byte/lineage integrity and incomplete-write checks, with no DVC claims."""

import copy
import os
import shutil
import tempfile

import pytest

from rent_contracts import ContractError
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data import release_io
from rent_data.release_io import (
    COMPLETION_FILE,
    finalize_restoration,
    payload_inventory,
    read_artifact,
    read_verified_restore,
    verify_payload,
    write_payload,
)
from rent_data.releases import (
    ReleaseError,
    build_restoration_report,
    content_digest,
    dataset_release_digest,
)


def check(case):
    return verify_payload(
        case["manifest"], case["root"], expected_release_ref=case["manifest"]["release_digest"]
    )


def reseal_payload(case):
    """Simulate a new declared release; semantic checks must still catch contradictions."""
    manifest = case["manifest"]
    manifest["artifacts"] = payload_inventory(case["root"])
    manifest["dvc"]["size_bytes"] = sum(row["size_bytes"] for row in manifest["artifacts"])
    manifest["dvc"]["file_count"] = len(manifest["artifacts"])
    manifest["release_digest"] = dataset_release_digest(manifest)


def test_payload_preserves_every_exact_source_byte_and_unknown_fact(release_case):
    case = release_case
    before = copy.deepcopy(case["candidate"])
    candidate = check(case)
    assert candidate == before
    source_files = list((case["root"] / "sources").iterdir())
    assert sorted(path.read_bytes() for path in source_files) == sorted(case["sources"])
    assert candidate["quality_report"]["observation_count"] == 4
    assert candidate["quality_report"]["observations_with_eligibility_issues"] == 2
    unknown = next(
        row
        for row in candidate["observations"]
        if row["property_identity"]["status"] == "unresolved"
    )
    assert unknown["property_identity"]["property_id"] is None
    assert all(
        unknown[key] is None
        for key in (
            "published_at",
            "collected_at",
            "features_available_at",
            "prediction_cutoff_at",
            "temporal_evidence_ref",
        )
    )
    assert all(
        source["acquisition_period"] == {"start": None, "end": None}
        for source in candidate["sources"]
    )


@pytest.mark.parametrize(
    "kind", ["changed", "missing", "extra", "extra-directory", "source-missing"]
)
def test_tampered_or_incomplete_payload_is_rejected(release_case, kind):
    root = release_case["root"]
    if kind == "changed":
        with (root / "candidate.json").open("ab") as stream:
            stream.write(b" ")
    elif kind == "missing":
        (root / "quality-report.json").unlink()
    elif kind == "extra":
        (root / ".dvcignore").write_bytes(b"secret.json")
    elif kind == "extra-directory":
        (root / "other").mkdir()
    else:
        next((root / "sources").iterdir()).unlink()
    with pytest.raises(ContractError):
        check(release_case)


@pytest.mark.parametrize("kind", ["file-link", "directory-link", "root-link", "fifo"])
def test_nonregular_or_symlink_payloads_never_follow_or_block(release_case, tmp_path, kind):
    root = release_case["root"]
    if kind == "file-link":
        target = tmp_path / "outside.json"
        (root / "candidate.json").rename(target)
        (root / "candidate.json").symlink_to(target)
    elif kind == "directory-link":
        target = tmp_path / "outside-sources"
        (root / "sources").rename(target)
        (root / "sources").symlink_to(target, target_is_directory=True)
    elif kind == "root-link":
        target = tmp_path / "original-payload"
        root.rename(target)
        root.symlink_to(target, target_is_directory=True)
    else:
        (root / "candidate.json").unlink()
        os.mkfifo(root / "candidate.json")
    with pytest.raises(ReleaseError):
        check(release_case)


def test_file_size_bound_is_enforced_before_json_parsing(release_case):
    path = release_case["root"] / "candidate.json"
    path.write_bytes(b" " * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(ReleaseError, match="PAYLOAD_LIMIT"):
        check(release_case)
    with pytest.raises(ReleaseError, match="PAYLOAD_LIMIT"):
        read_artifact(path)


@pytest.mark.parametrize("kind", ["quality", "candidate", "provenance"])
def test_rehashed_files_still_require_candidate_report_and_source_correspondence(
    release_case, kind
):
    case = release_case
    if kind == "quality":
        report = copy.deepcopy(case["candidate"]["quality_report"])
        report["listing_count"] += 1
        (case["root"] / "quality-report.json").write_text(canonical_json(report), encoding="utf-8")
        reseal_payload(case)
    elif kind == "candidate":
        candidate = copy.deepcopy(case["candidate"])
        candidate["observations"][0]["listing_id"] = "invented-listing"
        (case["root"] / "candidate.json").write_text(canonical_json(candidate), encoding="utf-8")
        reseal_payload(case)
    else:
        case["manifest"]["provenance"]["projection_policy_ref"] = content_digest(b"different")
        case["manifest"]["release_digest"] = dataset_release_digest(case["manifest"])
    with pytest.raises(ContractError):
        check(case)


def test_existing_payload_is_never_overwritten_and_invalid_input_writes_nothing(
    release_case, tmp_path
):
    case = release_case
    before = payload_inventory(case["root"])
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        write_payload(
            case["root"],
            case["candidate"],
            source_documents=case["sources"],
            expected_candidate_ref=case["candidate"]["candidate_digest"],
        )
    assert payload_inventory(case["root"]) == before
    destination = tmp_path / "invalid-input"
    with pytest.raises(ContractError):
        write_payload(
            destination,
            case["candidate"],
            source_documents=case["sources"][:1],
            expected_candidate_ref=case["candidate"]["candidate_digest"],
        )
    assert not destination.exists()


@pytest.mark.parametrize("operation", ["fsync", "link"])
def test_interrupted_finalization_has_no_success_marker(release_case, monkeypatch, operation):
    case = release_case
    destination = case["root"].parent
    report = build_restoration_report(case["manifest"])

    def fail(*args, **kwargs):
        raise OSError("synthetic private diagnostic must not leak")

    monkeypatch.setattr(release_io.os, operation, fail)
    with pytest.raises(ReleaseError, match="FINALIZATION_FAILED") as failure:
        finalize_restoration(
            destination,
            report,
            manifest=case["manifest"],
            expected_release_ref=case["manifest"]["release_digest"],
        )
    assert "private diagnostic" not in str(failure.value)
    assert not (destination / COMPLETION_FILE).exists()
    assert not list(destination.glob(".artifact-*"))
    with pytest.raises(ReleaseError):
        read_verified_restore(
            destination,
            manifest=case["manifest"],
            expected_release_ref=case["manifest"]["release_digest"],
        )


def test_reader_requires_marker_then_reverifies_all_bytes_and_refuses_overwrite(release_case):
    case = release_case
    destination = case["root"].parent
    manifest = case["manifest"]
    with pytest.raises(ReleaseError):
        read_verified_restore(
            destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )
    report = build_restoration_report(manifest)
    finalize_restoration(
        destination, report, manifest=manifest, expected_release_ref=manifest["release_digest"]
    )
    assert (
        read_verified_restore(
            destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )
        == case["candidate"]
    )
    marker = (destination / COMPLETION_FILE).read_bytes()
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        finalize_restoration(
            destination, report, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )
    assert (destination / COMPLETION_FILE).read_bytes() == marker
    (case["root"] / "quality-report.json").write_bytes(b"{}")
    with pytest.raises(ContractError):
        read_verified_restore(
            destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )


def test_partial_payload_write_is_never_a_completed_restore(
    release_input_factory, tmp_path, monkeypatch
):
    case = release_input_factory()

    def fail(*args):
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(release_io.os, "fsync", fail)
    with pytest.raises(ReleaseError, match="PAYLOAD_WRITE_FAILED"):
        write_payload(
            tmp_path / "payload",
            case["candidate"],
            source_documents=case["sources"],
            expected_candidate_ref=case["candidate"]["candidate_digest"],
        )
    assert not (tmp_path / COMPLETION_FILE).exists()


def test_bad_report_and_payload_cannot_be_finalized(release_case):
    case = release_case
    manifest = case["manifest"]
    report = build_restoration_report(manifest)
    report["observation_count"] += 1
    with pytest.raises(ContractError):
        finalize_restoration(
            case["root"].parent,
            report,
            manifest=manifest,
            expected_release_ref=manifest["release_digest"],
        )
    assert not (case["root"].parent / COMPLETION_FILE).exists()
    shutil.rmtree(case["root"])  # Only the owned synthetic fixture.
    with pytest.raises(ContractError):
        finalize_restoration(
            case["root"].parent,
            build_restoration_report(manifest),
            manifest=manifest,
            expected_release_ref=manifest["release_digest"],
        )


def test_completion_staging_failure_is_safe_and_cleanup_failure_preserves_success(
    release_case, monkeypatch
):
    case = release_case
    destination = case["root"].parent
    manifest = case["manifest"]
    report = build_restoration_report(manifest)

    def fail(*args, **kwargs):
        raise OSError("synthetic private path")

    with monkeypatch.context() as patch:
        patch.setattr(tempfile, "mkstemp", fail)
        with pytest.raises(ReleaseError, match="FINALIZATION_FAILED"):
            finalize_restoration(
                destination,
                report,
                manifest=manifest,
                expected_release_ref=manifest["release_digest"],
            )
    assert not (destination / COMPLETION_FILE).exists()
    with monkeypatch.context() as patch:
        patch.setattr(release_io.os, "unlink", fail)
        finalize_restoration(
            destination, report, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )
    assert (
        read_verified_restore(
            destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )
        == case["candidate"]
    )
