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
from rent_data.candidates import build_observation_candidate, project_candidate_observations
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


def stage_reference_payload(workspace, inventory, case, rows):
    write_observation_inventory(inventory, rows)
    candidate = build_observation_candidate(
        case["sources"], **case["recipe"], inventory_directory=inventory
    )
    root = workspace.root / "payload"
    artifacts = write_payload(
        root,
        candidate,
        source_documents=case["sources"],
        expected_candidate_ref=candidate["candidate_digest"],
        inventory_directory=inventory,
    )
    return candidate, artifacts


def test_actual_v2_release_restores_large_older_inventory_and_rejects_bad_objects(
    local_dvc, tmp_path, release_input_factory, large_observation_inventory
):
    store = tmp_path / "store"
    store.mkdir()
    producer = local_dvc.create_workspace(tmp_path / "producer", store=store)
    root = producer.root / "payload"
    older = release_input_factory("A")
    rows = large_observation_inventory
    original_source = json.loads(older["sources"][0])
    older["sources"] = []
    for start in range(0, len(rows), 600):
        source = {
            **original_source,
            "raw_source_ref": content_digest(f"synthetic archive {start}".encode()),
            "records": [
                {"source_record_id": f"capture-{offset}", "observation": row}
                for offset, row in enumerate(rows[start : start + 600])
            ],
        }
        older["sources"].append(canonical_json(source).encode("utf-8"))
    assert sum(map(len, older["sources"])) > MAX_DOCUMENT_BYTES

    candidate, artifacts = stage_reference_payload(producer, tmp_path / "inventory-A", older, rows)
    logical_bytes = json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert len(logical_bytes) > MAX_DOCUMENT_BYTES
    assert candidate["observations_digest"] == content_digest(logical_bytes)
    assert candidate["inventory"]["artifact"]["size_bytes"] > MAX_DOCUMENT_BYTES
    assert len(canonical_json(candidate).encode("utf-8")) < MAX_DOCUMENT_BYTES
    local_dvc.track_payload(producer, contract_version="2.0.0")
    commit = commit_metadata(local_dvc, producer, "synthetic-v2-revision-A")
    release = build_dataset_release(
        candidate,
        source_documents=older["sources"],
        inventory_directory=root / "inventory",
        binding=local_dvc.metadata_binding(producer, commit),
        artifacts=artifacts,
    )
    reference = release["release_digest"]
    local_dvc.push(producer, release, expected_release_ref=reference)

    shutil.rmtree(root)  # Only the disposable producer fixture's synthetic payload.
    newer = release_input_factory("B")
    _, newer_artifacts = stage_reference_payload(
        producer, tmp_path / "inventory-B", newer, newer["candidate"]["observations"]
    )
    local_dvc.track_payload(producer, contract_version="2.0.0")
    latest = commit_metadata(local_dvc, producer, "synthetic-v2-revision-B")
    assert latest != commit

    destination = tmp_path / "consumer-A"
    report = local_dvc.restore(
        release,
        metadata_workspace=producer,
        destination=destination,
        expected_release_ref=reference,
    )
    assert report["metadata_commit"] == commit
    assert report["fresh_cache"] is True
    assert report["observation_count"] == len(rows)
    assert any((destination / ".dvc/cache").rglob("*.dir"))
    restored = destination / "payload"
    assert payload_inventory(restored, contract_version="2.0.0") == artifacts
    verified = read_verified_restore(destination, manifest=release, expected_release_ref=reference)
    assert verified == candidate
    projected = project_candidate_observations(
        verified,
        source_documents=older["sources"],
        expected_candidate_ref=candidate["candidate_digest"],
        inventory_directory=restored / "inventory",
    )
    assert projected == rows
    for name in (MANIFEST_FILE, PARQUET_FILE):
        original = tmp_path / "inventory-A" / name
        assert (restored / "inventory" / name).read_bytes() == original.read_bytes()
        assert (restored / "inventory" / name).stat().st_ino != original.stat().st_ino
    assert payload_inventory(root, contract_version="2.0.0") == newer_artifacts

    # Mutate only the disposable remote's Parquet object. Each consumer starts
    # with an empty cache even though a completed consumer has the original.
    oid = release["dvc"]["object_id"]
    objects = store / "files/md5"
    entries = json.loads((objects / oid[:2] / oid[2:]).read_bytes())
    md5 = next(entry["md5"] for entry in entries if entry["relpath"] == f"inventory/{PARQUET_FILE}")
    remote_parquet = objects / md5[:2] / md5[2:]
    remote_parquet.chmod(0o600)
    with remote_parquet.open("r+b") as stream:
        stream.write(b"FAIL")
    corrupted = tmp_path / "consumer-corrupt"
    with pytest.raises(ContractError):
        local_dvc.restore(
            release,
            metadata_workspace=producer,
            destination=corrupted,
            expected_release_ref=reference,
        )
    assert not (corrupted / COMPLETION_FILE).exists()

    remote_parquet.unlink()
    incomplete = tmp_path / "consumer-missing"
    with pytest.raises(ContractError):
        local_dvc.restore(
            release,
            metadata_workspace=producer,
            destination=incomplete,
            expected_release_ref=reference,
        )
    assert not (incomplete / COMPLETION_FILE).exists()
    assert (destination / COMPLETION_FILE).is_file()


def test_actual_v2_push_rejects_stale_dvc_metadata_with_matching_totals(
    local_dvc, tmp_path, release_input_factory
):
    store = tmp_path / "store"
    store.mkdir()
    producer = local_dvc.create_workspace(tmp_path / "producer", store=store)
    root = producer.root / "payload"
    before = release_input_factory("A")
    _, tracked = stage_reference_payload(
        producer, tmp_path / "inventory-A", before, before["candidate"]["observations"]
    )
    local_dvc.track_payload(producer, contract_version="2.0.0")
    revision = commit_metadata(local_dvc, producer, "synthetic-stale-metadata")
    binding = local_dvc.metadata_binding(producer, revision)
    shutil.rmtree(root)
    after = release_input_factory("B")
    candidate, artifacts = stage_reference_payload(
        producer, tmp_path / "inventory-B", after, after["candidate"]["observations"]
    )
    assert len(tracked) == len(artifacts)
    assert sum(row["size_bytes"] for row in tracked) == sum(row["size_bytes"] for row in artifacts)
    release = build_dataset_release(
        candidate,
        source_documents=after["sources"],
        inventory_directory=root / "inventory",
        binding=binding,
        artifacts=artifacts,
    )
    with pytest.raises(ReleaseError, match="DVC_PAYLOAD_CHANGED"):
        local_dvc.push(producer, release, expected_release_ref=release["release_digest"])
    assert not list(store.iterdir())


# --- Development splits from reference-backed (v2) releases through actual DVC restores -----

FOUR_RECORD_ASSIGNMENTS = [
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
        "unseen_property_exclusions": ["listing_seen_in_training", "property_overlap_training"],
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
FOUR_RECORD_PARAMETERS = {
    "training_cutoff": "2026-01-11T00:00:00Z",
    "validation_window": {
        "start_inclusive": "2026-01-11T00:00:00Z",
        "end_exclusive": "2026-01-20T00:00:00Z",
    },
}


@pytest.fixture(scope="module")
def reference_revisions(local_dvc, tmp_path_factory, release_input_factory):
    """Two v2 revisions of the same synthetic fixtures as the v1 `revisions` fixture."""
    root = tmp_path_factory.mktemp("actual-local-dvc-v2")
    store = root / "store"
    store.mkdir()
    workspace = local_dvc.create_workspace(root / "producer", store=store)
    releases = {}
    for revision in ("A", "B"):
        case = release_input_factory(revision)
        if (workspace.root / "payload").exists():
            shutil.rmtree(workspace.root / "payload")  # Only this fixture's disposable bytes.
        candidate, artifacts = stage_reference_payload(
            workspace, root / f"inventory-{revision}", case, case["candidate"]["observations"]
        )
        local_dvc.track_payload(workspace, contract_version="2.0.0")
        commit = commit_metadata(local_dvc, workspace, f"synthetic-v2-revision-{revision}")
        manifest = build_dataset_release(
            candidate,
            source_documents=case["sources"],
            inventory_directory=workspace.root / "payload/inventory",
            binding=local_dvc.metadata_binding(workspace, commit),
            artifacts=artifacts,
        )
        local_dvc.push(workspace, manifest, expected_release_ref=manifest["release_digest"])
        releases[revision] = {**case, "candidate": candidate, "manifest": manifest}
    return {"workspace": workspace, "root": root, "releases": releases}


def test_actual_v1_and_v2_restores_materialize_identical_assignments_for_identical_observations(
    local_dvc, revisions, reference_revisions, split_input_factory, tmp_path
):
    metadata = split_input_factory()
    policy = metadata["policy"]
    parameters = metadata["parameters"] | FOUR_RECORD_PARAMETERS
    splits = {}
    for label, source in (("v1", revisions), ("v2", reference_revisions)):
        release = source["releases"]["A"]["manifest"]
        restored, output = tmp_path / f"restored-{label}", tmp_path / f"split-{label}"
        local_dvc.restore(
            release,
            metadata_workspace=source["workspace"],
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
        assert split["dataset_ref"] == release["release_digest"]
        assert (
            payload_inventory(restored / "payload", contract_version=release["contract_version"])
            == (release["artifacts"])
        )
        splits[label] = split
    one, two = splits["v1"], splits["v2"]
    assert one["memberships"] == two["memberships"] == FOUR_RECORD_ASSIGNMENTS
    assert one["observations_digest"] == two["observations_digest"]
    assert one["dataset_ref"] != two["dataset_ref"]
    assert one["split_digest"] != two["split_digest"]
    assert revisions["releases"]["A"]["manifest"]["contract_version"] == "1.0.0"
    assert reference_revisions["releases"]["A"]["manifest"]["contract_version"] == "2.0.0"


def test_actual_v2_older_large_release_materializes_identical_splits_from_independent_restores(
    local_dvc, tmp_path, release_input_factory, reference_population_factory
):
    population = reference_population_factory(1_800, long_ids=True)
    store = tmp_path / "store"
    store.mkdir()
    producer = local_dvc.create_workspace(tmp_path / "producer", store=store)
    root = producer.root / "payload"
    candidate, artifacts = stage_reference_payload(
        producer, tmp_path / "inventory-A", population, population["rows"]
    )
    logical = json.dumps(
        population["rows"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert len(logical) > MAX_DOCUMENT_BYTES  # the input is above the legacy inline bound
    assert candidate["observations_digest"] == content_digest(logical)
    local_dvc.track_payload(producer, contract_version="2.0.0")
    commit = commit_metadata(local_dvc, producer, "synthetic-v2-large-revision-A")
    release = build_dataset_release(
        candidate,
        source_documents=population["sources"],
        inventory_directory=root / "inventory",
        binding=local_dvc.metadata_binding(producer, commit),
        artifacts=artifacts,
    )
    reference = release["release_digest"]
    local_dvc.push(producer, release, expected_release_ref=reference)

    shutil.rmtree(root)  # Only the disposable producer fixture's synthetic payload.
    newer = release_input_factory("B")
    _, newer_artifacts = stage_reference_payload(
        producer, tmp_path / "inventory-B", newer, newer["candidate"]["observations"]
    )
    local_dvc.track_payload(producer, contract_version="2.0.0")
    assert commit_metadata(local_dvc, producer, "synthetic-v2-large-revision-B") != commit

    policy = population["policy"]
    context = {
        "release": release,
        "policy": policy,
        "expected_release_ref": reference,
        "expected_policy_ref": policy["policy_digest"],
    }
    stored, caches = [], []
    for index in range(2):
        restored, output = tmp_path / f"restored-{index}", tmp_path / f"split-{index}"
        report = local_dvc.restore(
            release,
            metadata_workspace=producer,
            destination=restored,
            expected_release_ref=reference,
        )
        assert report["fresh_cache"] is True
        assert report["metadata_commit"] == commit
        assert report["observation_count"] == len(population["rows"])
        caches.append(restored / ".dvc/cache")
        assert any(caches[-1].rglob("*.dir")) and not caches[-1].is_symlink()
        split = materialize_development_split(
            restored, output, **context, **population["parameters"]
        )
        assert (
            read_verified_development_split(
                output,
                restored_directory=restored,
                expected_split_ref=split["split_digest"],
                **context,
            )
            == split
        )
        assert split["dataset_ref"] == reference
        assert split["memberships"] == population["expected"]  # closed-form rules, row by row
        assert payload_inventory(restored / "payload", contract_version="2.0.0") == artifacts
        data = (output / SPLIT_FILE).read_bytes()
        assert data == canonical_json(split).encode("utf-8")
        assert len(data) < MAX_DOCUMENT_BYTES  # the output bound differs from the input bound
        stored.append(data)
    assert stored[0] == stored[1]
    assert caches[0] != caches[1]  # independent consumer workspaces and caches
    unseen = [
        row["observation_id"]
        for row in population["expected"]
        if "unseen_property" in row["cohorts"]
    ]
    for cohort, ids in (
        ("future_market", [r["observation_id"] for r in population["expected"] if r["cohorts"]]),
        ("unseen_property", unseen),
    ):
        validate_development_population(
            split, ids, cohort=cohort, expected_split_ref=split["split_digest"]
        )
    assert payload_inventory(root, contract_version="2.0.0") == newer_artifacts


@pytest.mark.parametrize("kind", ["parquet-byte", "marker-missing", "release-ref", "policy-ref"])
def test_actual_v2_restoration_damage_or_wrong_references_never_produce_a_split(
    local_dvc, reference_revisions, split_input_factory, tmp_path, kind
):
    release = reference_revisions["releases"]["A"]["manifest"]
    metadata = split_input_factory()
    restored, output = tmp_path / "restored", tmp_path / "split"
    local_dvc.restore(
        release,
        metadata_workspace=reference_revisions["workspace"],
        destination=restored,
        expected_release_ref=release["release_digest"],
    )
    arguments = (
        {
            "release": release,
            "policy": metadata["policy"],
            "expected_release_ref": release["release_digest"],
            "expected_policy_ref": metadata["policy"]["policy_digest"],
        }
        | metadata["parameters"]
        | FOUR_RECORD_PARAMETERS
    )
    if kind == "parquet-byte":
        path = restored / "payload/inventory" / PARQUET_FILE
        path.chmod(0o600)  # Only this disposable consumer workspace.
        raw = path.read_bytes()
        path.write_bytes(raw[:4] + bytes([raw[4] ^ 1]) + raw[5:])
    elif kind == "marker-missing":
        (restored / COMPLETION_FILE).unlink()
    elif kind == "release-ref":
        arguments["expected_release_ref"] = content_digest(b"wrong release")
    else:
        arguments["expected_policy_ref"] = content_digest(b"wrong policy")
    with pytest.raises(ContractError):
        materialize_development_split(restored, output, **arguments)
    assert not output.exists()
