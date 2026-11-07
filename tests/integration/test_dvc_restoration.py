"""Actual DVC 3.67.1, synthetic metadata, owned local stores and disposable Git only."""

import copy
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from rent_contracts import ContractError
from rent_contracts.evaluation import validate_development_population
from rent_contracts.inventory import MANIFEST_FILE, PARQUET_FILE
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data.dvc_local import LocalDvcStore
from rent_data.inventory_io import (
    InventoryLimits,
    verify_observation_inventory,
    write_observation_inventory,
)
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
from rent_data.split_io import (
    SPLIT_FILE,
    materialize_development_split,
    read_verified_development_split,
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


def test_old_release_materializes_identical_split_from_independent_actual_restores(
    local_dvc, revisions, split_input_factory, tmp_path
):
    case = revisions["releases"]["A"]
    release = case["manifest"]
    assert (
        payload_inventory(revisions["workspace"].root / "payload")
        == revisions["releases"]["B"]["manifest"]["artifacts"]
    )
    metadata = split_input_factory()
    policy = metadata["policy"]
    parameters = metadata["parameters"] | {
        "training_cutoff": "2026-01-11T00:00:00Z",
        "validation_window": {
            "start_inclusive": "2026-01-11T00:00:00Z",
            "end_exclusive": "2026-01-20T00:00:00Z",
        },
    }
    artifacts = []
    for index in range(2):
        restored = tmp_path / f"restored-{index}"
        output = tmp_path / f"split-{index}"
        local_dvc.restore(
            release,
            metadata_workspace=revisions["workspace"],
            destination=restored,
            expected_release_ref=release["release_digest"],
        )
        context = {
            "release": release,
            "policy": policy,
            "expected_release_ref": release["release_digest"],
            "expected_policy_ref": policy["policy_digest"],
        }
        split = materialize_development_split(restored, output, **context, **parameters)
        assert (
            read_verified_development_split(
                output,
                restored_directory=restored,
                expected_split_ref=split["split_digest"],
                **context,
            )
            == split
        )
        # Handwritten assignments for the original four-record DVC fixture.
        assert split["memberships"] == [
            {
                "observation_id": "synthetic-A-0",
                "partition": "training",
                "eligibility_exclusions": [],
                "cohorts": [],
                "unseen_property_exclusions": ["not_development_validation"],
            },
            {
                "observation_id": "synthetic-A-1",
                "partition": "development_validation",
                "eligibility_exclusions": [],
                "cohorts": ["future_market"],
                "unseen_property_exclusions": [
                    "listing_seen_in_training",
                    "property_overlap_training",
                ],
            },
            {
                "observation_id": "synthetic-A-2",
                "partition": "excluded",
                "eligibility_exclusions": ["temporal_evidence_missing"],
                "cohorts": [],
                "unseen_property_exclusions": ["not_development_validation"],
            },
            {
                "observation_id": "synthetic-A-3",
                "partition": "excluded",
                "eligibility_exclusions": ["invalid_non_target_domain", "temporal_order_invalid"],
                "cohorts": [],
                "unseen_property_exclusions": ["not_development_validation"],
            },
        ]
        assert len(split["memberships"]) == release["observation_count"] == 4
        assert split["dataset_ref"] == release["release_digest"]
        validate_development_population(
            split,
            ["synthetic-A-1"],
            cohort="future_market",
            expected_split_ref=split["split_digest"],
        )
        with pytest.raises(ContractError):
            validate_development_population(
                split,
                ["synthetic-A-1", "synthetic-A-3"],
                cohort="future_market",
                expected_split_ref=split["split_digest"],
            )
        assert payload_inventory(restored / "payload") == release["artifacts"]
        artifacts.append((output / SPLIT_FILE).read_bytes())
        assert artifacts[-1] == canonical_json(split).encode("utf-8")
    assert artifacts[0] == artifacts[1]
    assert (
        payload_inventory(revisions["workspace"].root / "payload")
        == revisions["releases"]["B"]["manifest"]["artifacts"]
    )


def test_actual_local_dvc_preserves_inventory_from_exact_revision_and_fresh_cache(
    local_dvc, tmp_path, large_observation_inventory
):
    """Transport fixture only. The production v1 release roster is still closed."""
    store = tmp_path / "local-store"
    store.mkdir()
    producer = local_dvc.create_workspace(tmp_path / "producer", store=store)
    source = producer.root / "payload"
    raw = json.dumps(
        large_observation_inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    expected = "sha256:" + hashlib.sha256(raw).hexdigest()
    manifest = write_observation_inventory(
        source, iter(large_observation_inventory), limits=InventoryLimits(batch_rows=257)
    )
    assert len(raw) > MAX_DOCUMENT_BYTES
    assert manifest["artifact"]["size_bytes"] > MAX_DOCUMENT_BYTES
    before = {name: (source / name).read_bytes() for name in (MANIFEST_FILE, PARQUET_FILE)}
    with pytest.raises(ReleaseError, match="UNEXPECTED_PAYLOAD_PATH"):
        payload_inventory(source)
    local_dvc._execute(local_dvc.executable, ["add", "payload"], producer.root)
    revision = commit_metadata(local_dvc, producer, "synthetic-observation-inventory")
    binding = local_dvc.metadata_binding(producer, revision)
    assert binding["metadata"]["commit"] == revision
    assert binding["dvc"]["file_count"] == 2
    assert binding["dvc"]["size_bytes"] == sum(map(len, before.values()))
    committed = local_dvc._execute(
        local_dvc.git, ["--no-pager", "show", f"{revision}:payload.dvc"], producer.root
    )
    assert binding["metadata"]["digest"] == content_digest(committed)
    local_dvc._execute(
        local_dvc.executable,
        ["push", "-j", "1", "-r", "local-store", "payload.dvc"],
        producer.root,
    )

    consumer = local_dvc.create_workspace(tmp_path / "consumer", store=store)
    cache = consumer.root / ".dvc/cache"
    assert not cache.exists() or not any(cache.iterdir())
    (consumer.root / "payload.dvc").write_bytes(committed)
    assert not (consumer.root / "payload").exists()
    local_dvc._execute(
        local_dvc.executable,
        ["pull", "-j", "1", "-r", "local-store", "payload.dvc"],
        consumer.root,
    )
    restored = consumer.root / "payload"
    assert any(cache.rglob("*.dir"))
    assert (
        verify_observation_inventory(
            restored, expected_inventory_ref=expected, limits=InventoryLimits(batch_rows=31)
        )
        == manifest
    )
    for name, raw_bytes in before.items():
        assert (source / name).read_bytes() == (restored / name).read_bytes() == raw_bytes
        assert (source / name).stat().st_ino != (restored / name).stat().st_ino
