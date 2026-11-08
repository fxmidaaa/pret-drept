"""Synthetic unit I/O states; these fixtures do not claim an actual DVC operation."""

import copy
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from rent_contracts import ContractError
from rent_contracts.evaluation import development_split_digest
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data import release_io
from rent_data.release_io import (
    COMPLETION_FILE,
    finalize_restoration,
    write_payload,
)
from rent_data.releases import ReleaseError, build_restoration_report, content_digest
from rent_data.split_io import (
    SPLIT_FILE,
    materialize_development_split,
    read_verified_development_split,
)


@pytest.fixture
def local_case(split_case, tmp_path):
    # Valid synthetic metadata marker for unit tests, not a mocked successful CLI.
    restored = tmp_path / "restored"
    restored.mkdir()
    release = split_case["release"]
    write_payload(
        restored / "payload",
        split_case["candidate"],
        source_documents=split_case["sources"],
        expected_candidate_ref=split_case["candidate"]["candidate_digest"],
    )
    finalize_restoration(
        restored,
        build_restoration_report(release),
        manifest=release,
        expected_release_ref=release["release_digest"],
    )
    return {**split_case, "restored": restored, "output": tmp_path / "split"}


def materialize(case, **overrides):
    return materialize_development_split(
        **(
            {
                "restored_directory": case["restored"],
                "destination": case["output"],
                "release": case["release"],
                "policy": case["policy"],
                "expected_release_ref": case["release"]["release_digest"],
                "expected_policy_ref": case["policy"]["policy_digest"],
                **case["parameters"],
            }
            | overrides
        )
    )


def read(case, manifest, **overrides):
    return read_verified_development_split(
        **(
            {
                "destination": case["output"],
                "restored_directory": case["restored"],
                "release": case["release"],
                "policy": case["policy"],
                "expected_release_ref": case["release"]["release_digest"],
                "expected_policy_ref": case["policy"]["policy_digest"],
                "expected_split_ref": manifest["split_digest"],
            }
            | overrides
        )
    )


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): content_digest(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }


def test_verified_roundtrip_is_canonical_separate_and_preserves_all_source_bytes(local_case):
    case = local_case
    before = snapshot(case["restored"])
    manifest = materialize(case)
    assert read(case, manifest) == manifest
    assert (case["output"] / SPLIT_FILE).read_bytes() == canonical_json(manifest).encode("utf-8")
    assert [path.name for path in case["output"].iterdir()] == [SPLIT_FILE]
    assert len(manifest["memberships"]) == case["release"]["observation_count"] == 13
    assert snapshot(case["restored"]) == before
    manifest["memberships"].clear()
    assert (case["output"] / SPLIT_FILE).read_bytes() != canonical_json(manifest).encode("utf-8")


@pytest.mark.parametrize(
    "kind",
    [
        "payload",
        "marker",
        "missing-marker",
        "extra-payload",
        "policy",
        "release",
        "boundaries",
        "provenance",
    ],
)
def test_invalid_input_writes_no_output_directory(local_case, kind):
    case = local_case
    overrides = {}
    if kind == "payload":
        (case["restored"] / "payload/candidate.json").write_bytes(b"{}")
    elif kind == "marker":
        (case["restored"] / COMPLETION_FILE).write_bytes(b"{}")
    elif kind == "missing-marker":
        (case["restored"] / COMPLETION_FILE).unlink()
    elif kind == "extra-payload":
        (case["restored"] / "payload/extra.json").write_bytes(b"{}")
    elif kind == "policy":
        overrides["expected_policy_ref"] = content_digest(b"wrong")
    elif kind == "release":
        overrides["expected_release_ref"] = case["candidate"]["candidate_digest"]
    elif kind == "boundaries":
        overrides["validation_window"] = {}
    else:
        overrides["creation_provenance"] = {}
    with pytest.raises(ContractError):
        materialize(case, **overrides)
    assert not case["output"].exists()


@pytest.mark.parametrize(
    "kind",
    [
        "directory",
        "file",
        "link",
        "link-parent",
        "relative",
        "traversal",
        "inside-source",
        "ancestor",
        "source-link",
        "source-relative",
    ],
)
def test_output_and_input_paths_cannot_overwrite_or_overlap(local_case, tmp_path, kind):
    case = local_case
    destination, restored = case["output"], case["restored"]
    before = snapshot(restored)
    if kind == "directory":
        destination.mkdir()
        (destination / "preserve").write_bytes(b"existing")
    elif kind == "file":
        destination.write_bytes(b"existing")
    elif kind == "link":
        destination.symlink_to(restored, target_is_directory=True)
    elif kind == "link-parent":
        parent = tmp_path / "parent-link"
        parent.symlink_to(tmp_path, target_is_directory=True)
        destination = parent / "split"
    elif kind == "relative":
        destination = Path("relative-output")
    elif kind == "traversal":
        destination = restored / ".." / "split"
    elif kind == "inside-source":
        destination = restored / "payload/split"
    elif kind == "ancestor":
        destination = tmp_path
    elif kind == "source-link":
        restored = tmp_path / "source-link"
        restored.symlink_to(case["restored"], target_is_directory=True)
    else:
        restored = Path("relative-source")
    with pytest.raises(ReleaseError):
        materialize(case, destination=destination, restored_directory=restored)
    assert snapshot(case["restored"]) == before
    if kind == "directory":
        assert (destination / "preserve").read_bytes() == b"existing"
    elif kind == "file":
        assert destination.read_bytes() == b"existing"
    elif kind not in ("link", "ancestor"):
        assert not case["output"].exists()


@pytest.mark.parametrize("operation", ["mkstemp", "write", "fsync", "link"])
def test_interrupted_atomic_creation_leaves_no_final_split(local_case, monkeypatch, operation):
    case = local_case
    before = snapshot(case["restored"])

    def fail(*args, **kwargs):
        raise OSError("synthetic-private-path-do-not-log")

    if operation == "write":
        original = release_io.os.fdopen

        @contextmanager
        def interrupted(*args, **kwargs):
            with original(*args, **kwargs) as stream:
                if "w" not in (args[1] if len(args) > 1 else kwargs.get("mode", "r")):
                    yield stream
                    return

                class Writer:
                    def write(self, raw):
                        stream.write(raw[:5])
                        fail()

                yield Writer()

        monkeypatch.setattr(release_io.os, "fdopen", interrupted)
    elif operation == "mkstemp":
        monkeypatch.setattr(tempfile, operation, fail)
    else:
        monkeypatch.setattr(release_io.os, operation, fail)
    with pytest.raises(ReleaseError, match="FINALIZATION_FAILED") as failure:
        materialize(case)
    assert "synthetic-private-path" not in str(failure.value)
    assert not (case["output"] / SPLIT_FILE).exists()
    assert not list(case["output"].glob(".artifact-*"))
    assert snapshot(case["restored"]) == before


def test_directory_creation_failure_is_safe_and_preserves_source(local_case, monkeypatch):
    original = Path.mkdir

    def fail(path, *args, **kwargs):
        if path == local_case["output"]:
            raise OSError("synthetic-private-path")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail)
    with pytest.raises(ReleaseError, match="SPLIT_WRITE_FAILED"):
        materialize(local_case)
    assert not local_case["output"].exists()


def test_existing_completed_output_is_preserved_even_if_input_later_changes(local_case):
    case = local_case
    manifest = materialize(case)
    before = snapshot(case["output"])
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        materialize(case)
    (case["restored"] / "payload/candidate.json").write_bytes(b"{}")
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        materialize(case)
    with pytest.raises(ContractError):
        read(case, manifest)
    assert snapshot(case["output"]) == before


@pytest.mark.parametrize(
    "kind", ["missing", "json", "bom", "oversized", "file-link", "root-link", "fifo"]
)
def test_invalid_split_file_states_are_not_consumed(local_case, tmp_path, kind):
    case = local_case
    manifest = materialize(case)
    path = case["output"] / SPLIT_FILE
    if kind == "missing":
        path.unlink()
    elif kind == "json":
        path.write_bytes(b"{")
    elif kind == "bom":
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    elif kind == "oversized":
        path.write_bytes(b" " * (MAX_DOCUMENT_BYTES + 1))
    elif kind == "file-link":
        outside = tmp_path / "outside.json"
        path.rename(outside)
        path.symlink_to(outside)
    elif kind == "root-link":
        outside = tmp_path / "outside-output"
        case["output"].rename(outside)
        case["output"].symlink_to(outside, target_is_directory=True)
    else:
        path.unlink()
        os.mkfifo(path)
    with pytest.raises(ContractError):
        read(case, manifest)


@pytest.mark.parametrize(
    "reference", ["expected_release_ref", "expected_policy_ref", "expected_split_ref"]
)
def test_reader_requires_all_external_identities(local_case, reference):
    manifest = materialize(local_case)
    with pytest.raises(ContractError):
        read(local_case, manifest, **{reference: content_digest(b"substituted identity")})


@pytest.mark.parametrize("kind", ["population", "cohort", "provenance"])
def test_resealed_split_tampering_does_not_bypass_reader(local_case, kind):
    case = local_case
    original = materialize(case)
    changed = copy.deepcopy(original)
    if kind == "population":
        changed["memberships"].pop()
    elif kind == "cohort":
        next(row for row in changed["memberships"] if row["observation_id"] == "obs-new")[
            "cohorts"
        ] = ["future_market"]
    else:
        changed["creation_provenance"]["created_at"] = "2026-03-04T12:00:00Z"
    changed["split_digest"] = development_split_digest(changed)
    (case["output"] / SPLIT_FILE).write_text(canonical_json(changed), encoding="utf-8")
    # A fixed expected ref rejects even a semantically valid provenance change.
    expected = original if kind == "provenance" else changed
    with pytest.raises(ContractError):
        read(case, expected)


def test_reader_preserves_existing_valid_v1_array_order_acceptance(local_case):
    case = local_case
    manifest = materialize(case)
    manifest["memberships"].reverse()
    for row in manifest["memberships"]:
        for name in ("cohorts", "eligibility_exclusions", "unseen_property_exclusions"):
            row[name].reverse()
    manifest["split_digest"] = development_split_digest(manifest)
    (case["output"] / SPLIT_FILE).write_text(canonical_json(manifest), encoding="utf-8")
    assert read(case, manifest) == manifest
