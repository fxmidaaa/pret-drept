"""Actual DVC 3.67.1, synthetic metadata, owned local stores and disposable Git only."""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from rent_contracts import ContractError
from rent_data.dvc_local import LocalDvcStore
from rent_data.release_io import (
    COMPLETION_FILE,
    payload_inventory,
    read_verified_restore,
    write_payload,
)
from rent_data.releases import (
    ReleaseError,
    build_dataset_release,
    content_digest,
    data_tool_profile_digest,
    dataset_release_digest,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def local_dvc():
    executable = Path(os.environ.get("RENT_DATA_DVC", ROOT / ".venv-data-tools/bin/dvc"))
    if not executable.is_absolute() or not executable.is_file():
        pytest.fail(
            "Pinned DVC is required. Follow docs/development.md data-tool setup and set RENT_DATA_DVC to its absolute executable; no automatic install or skip."
        )
    profile = data_tool_profile_digest(
        tool_lock=(ROOT / "requirements-data-tools.lock").read_bytes(),
        build_lock=(ROOT / "requirements-data-build.lock").read_bytes(),
    )
    return LocalDvcStore(executable, tool_profile_ref=profile)


def commit_metadata(adapter, workspace, message):
    """Explicit authorization applies only to this owned synthetic Git repository."""
    assert workspace.root != ROOT and ROOT not in workspace.root.parents
    adapter._execute(adapter.git, ["add", "--", "payload.dvc"], workspace.root)
    arguments = [
        "-c",
        "user.name=Synthetic DVC Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        f"core.hooksPath={workspace.root / '.control/no-hooks'}",
        "commit",
        "--quiet",
        "--only",
        "-m",
        message,
        "--",
        "payload.dvc",
    ]
    adapter._execute(adapter.git, arguments, workspace.root)
    return adapter._execute(adapter.git, ["rev-parse", "HEAD"], workspace.root).decode().strip()


@pytest.fixture(scope="module")
def revisions(local_dvc, tmp_path_factory, release_input_factory):
    root = tmp_path_factory.mktemp("actual-local-dvc")
    store = root / "store"
    store.mkdir()
    workspace = local_dvc.create_workspace(root / "producer", store=store)
    releases = {}
    for revision in ("A", "B"):
        case = release_input_factory(revision)
        if (workspace.root / "payload").exists():
            shutil.rmtree(workspace.root / "payload")  # Only this fixture's disposable bytes.
        artifacts = write_payload(
            workspace.root / "payload",
            case["candidate"],
            source_documents=case["sources"],
            expected_candidate_ref=case["candidate"]["candidate_digest"],
        )
        local_dvc.track_payload(workspace)
        commit = commit_metadata(local_dvc, workspace, f"synthetic-revision-{revision}")
        manifest = build_dataset_release(
            case["candidate"],
            source_documents=case["sources"],
            binding=local_dvc.metadata_binding(workspace, commit),
            artifacts=artifacts,
        )
        local_dvc.push(workspace, manifest, expected_release_ref=manifest["release_digest"])
        releases[revision] = {**case, "manifest": manifest}
    return {"workspace": workspace, "root": root, "releases": releases}


def test_actual_two_revision_restore_uses_exact_old_commit_and_fresh_cache(local_dvc, revisions):
    workspace = revisions["workspace"]
    a, b = (revisions["releases"][key] for key in ("A", "B"))
    assert a["manifest"]["metadata"]["commit"] != b["manifest"]["metadata"]["commit"]
    assert a["manifest"]["dvc"]["object_id"] != b["manifest"]["dvc"]["object_id"]
    assert payload_inventory(workspace.root / "payload") == b["manifest"]["artifacts"]
    before = payload_inventory(workspace.root / "payload")
    for revision, case in (("B", b), ("A", a)):
        destination = revisions["root"] / f"consumer-{revision}"
        assert not destination.exists()
        manifest = case["manifest"]
        report = local_dvc.restore(
            manifest,
            metadata_workspace=workspace,
            destination=destination,
            expected_release_ref=manifest["release_digest"],
        )
        assert (
            read_verified_restore(
                destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
            )
            == case["candidate"]
        )
        assert report["fresh_cache"] is True
        assert report["observation_count"] == 4
        assert report["observations_digest"] == manifest["observations_digest"]
        assert report["tool_profile_ref"] == local_dvc.tool_profile_ref
        assert str(revisions["root"]) not in str(report)
        assert (destination / "payload.dvc").read_bytes() == local_dvc._execute(
            local_dvc.git,
            ["--no-pager", "show", f"{manifest['metadata']['commit']}:payload.dvc"],
            workspace.root,
        )
        cache = destination / ".dvc/cache"
        assert cache.is_dir() and any(cache.rglob("*.dir"))
        assert not cache.is_symlink()
        # Copy links ensure consumer payload bytes are not producer/cache hardlinks.
        assert (destination / "payload/candidate.json").stat().st_ino != (
            workspace.root / "payload/candidate.json"
        ).stat().st_ino
    assert payload_inventory(workspace.root / "payload") == before


@pytest.mark.parametrize("kind", ["missing", "corrupt-directory", "corrupt-artifact"])
def test_missing_or_corrupt_remote_fails_even_with_populated_producer_cache(
    local_dvc, revisions, tmp_path, kind
):
    case = revisions["releases"]["A"]
    manifest = case["manifest"]
    alternate = tmp_path / "alternate-store"
    if kind == "missing":
        alternate.mkdir()
    else:
        shutil.copytree(revisions["workspace"].store, alternate)
        if kind == "corrupt-directory":
            oid = manifest["dvc"]["object_id"]
            path = alternate / "files/md5" / oid[:2] / oid[2:]
        else:
            oid = manifest["dvc"]["object_id"]
            directory = alternate / "files/md5" / oid[:2] / oid[2:]
            entries = json.loads(directory.read_bytes())
            md5 = next(entry["md5"] for entry in entries if entry["relpath"] == "candidate.json")
            path = alternate / "files/md5" / md5[:2] / md5[2:]
        path.chmod(0o600)  # Only the copied synthetic store, never original DVC objects.
        path.write_bytes(b"synthetic corrupted object")
    # Own fresh metadata workspace contains Git objects but no producer DVC cache.
    metadata = local_dvc.create_workspace(tmp_path / "metadata", store=alternate)
    local_dvc._execute(
        local_dvc.git,
        [
            "fetch",
            "--quiet",
            "--no-tags",
            str(revisions["workspace"].root),
            manifest["metadata"]["commit"],
        ],
        metadata.root,
    )
    assert any((revisions["workspace"].root / ".dvc/cache").rglob("*.dir"))
    destination = tmp_path / "consumer"
    with pytest.raises(ContractError):
        local_dvc.restore(
            manifest,
            metadata_workspace=metadata,
            destination=destination,
            expected_release_ref=manifest["release_digest"],
        )
    assert not (destination / COMPLETION_FILE).exists()
    with pytest.raises(ContractError):
        read_verified_restore(
            destination, manifest=manifest, expected_release_ref=manifest["release_digest"]
        )


@pytest.mark.parametrize(
    "kind", ["external-ref", "wrong-commit", "wrong-digest", "wrong-object", "missing-commit"]
)
def test_wrong_identities_fail_before_output_is_created(local_dvc, revisions, tmp_path, kind):
    manifest = copy.deepcopy(revisions["releases"]["A"]["manifest"])
    expected = manifest["release_digest"]
    if kind == "external-ref":
        expected = content_digest(b"wrong")
    else:
        if kind == "wrong-commit":
            manifest["metadata"]["commit"] = revisions["releases"]["B"]["manifest"]["metadata"][
                "commit"
            ]
        elif kind == "wrong-digest":
            manifest["metadata"]["digest"] = content_digest(b"wrong")
        elif kind == "wrong-object":
            manifest["dvc"]["object_id"] = "0" * 32 + ".dir"
        else:
            manifest["metadata"]["commit"] = "0" * 40
        manifest["release_digest"] = dataset_release_digest(manifest)
        expected = manifest["release_digest"]
    destination = tmp_path / "consumer"
    with pytest.raises(ContractError):
        local_dvc.restore(
            manifest,
            metadata_workspace=revisions["workspace"],
            destination=destination,
            expected_release_ref=expected,
        )
    assert not destination.exists()


def test_existing_destinations_and_changed_config_are_preserved(local_dvc, revisions, tmp_path):
    manifest = revisions["releases"]["A"]["manifest"]
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "preserve"
    sentinel.write_bytes(b"existing bytes")
    with pytest.raises(ReleaseError, match="OUTPUT_EXISTS"):
        local_dvc.restore(
            manifest,
            metadata_workspace=revisions["workspace"],
            destination=destination,
            expected_release_ref=manifest["release_digest"],
        )
    assert sentinel.read_bytes() == b"existing bytes"
    store = tmp_path / "other-store"
    store.mkdir()
    workspace = local_dvc.create_workspace(tmp_path / "changed", store=store)
    (workspace.root / ".dvc/config.local").write_bytes(b"[core]\nremote = other\n")
    with pytest.raises(ReleaseError, match="WORKSPACE_CONFIGURATION_CHANGED"):
        local_dvc.track_payload(workspace)
    assert not (workspace.root / "payload.dvc").exists()
