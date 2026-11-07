"""Development release/report contracts and candidate correspondence."""

import copy
import hashlib
import platform
import re
import sys
from pathlib import Path

from rent_contracts import ContractError, validate_document
from rent_contracts.inventory import (
    MANIFEST_FILE,
    MAX_MANIFEST_BYTES,
    MAX_PARQUET_BYTES,
    PARQUET_FILE,
    validate_inventory_manifest,
)
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json

from ._artifact_io import ReleaseError as ReleaseError
from .candidates import (
    INLINE_VERSION,
    MAX_REFERENCE_SOURCE_BYTES,
    PROVENANCE_FIELDS,
    REFERENCE_VERSION,
    validate_candidate_document,
    validate_observation_candidate,
)

DVC_VERSION = "3.67.1"
INVENTORY_DIRECTORY = "inventory"
INVENTORY_MANIFEST_PATH = f"{INVENTORY_DIRECTORY}/{MANIFEST_FILE}"
INVENTORY_PARQUET_PATH = f"{INVENTORY_DIRECTORY}/{PARQUET_FILE}"


def content_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def document_digest(document: dict | list) -> str:
    return content_digest(canonical_json(document).encode("utf-8"))


def data_tool_profile_digest(*, tool_lock: bytes, build_lock: bytes) -> str:
    """Bind both lock files; this identifies declared inputs, not the installed host."""
    if type(tool_lock) is not bytes or type(build_lock) is not bytes:
        raise ContractError("data tool profile requires exact lock bytes")
    return document_digest(
        {
            "requirements-data-tools.lock": content_digest(tool_lock),
            "requirements-data-build.lock": content_digest(build_lock),
        }
    )


def dataset_release_digest(manifest: dict) -> str:
    return document_digest(
        {key: value for key, value in manifest.items() if key != "release_digest"}
    )


def restoration_report_digest(report: dict) -> str:
    return document_digest({key: value for key, value in report.items() if key != "report_digest"})


def source_artifact_path(source_ref: str) -> str:
    if type(source_ref) is not str or re.fullmatch(r"sha256:[a-f0-9]{64}", source_ref) is None:
        raise ContractError("invalid metadata source reference")
    return f"sources/{source_ref[7:]}.json"


def valid_artifact_path(path: str, *, contract_version: str = INLINE_VERSION) -> bool:
    return type(path) is str and (
        path in ("candidate.json", "quality-report.json")
        or re.fullmatch(r"sources/[a-f0-9]{64}\.json", path) is not None
        or (
            contract_version == REFERENCE_VERSION
            and path in (INVENTORY_MANIFEST_PATH, INVENTORY_PARQUET_PATH)
        )
    )


def artifact_byte_limit(path: str) -> int:
    if path == INVENTORY_PARQUET_PATH:
        return MAX_PARQUET_BYTES
    if path == INVENTORY_MANIFEST_PATH:
        return MAX_MANIFEST_BYTES
    return MAX_DOCUMENT_BYTES


def inventory_artifacts(inventory: dict) -> list[dict]:
    """Derive the exact roster entries from an already validated inventory manifest."""
    raw = canonical_json(inventory).encode("utf-8")
    return [
        {"path": INVENTORY_MANIFEST_PATH, "digest": content_digest(raw), "size_bytes": len(raw)},
        {**inventory["artifact"], "path": INVENTORY_PARQUET_PATH},
    ]


def _validate_release_document(manifest: dict) -> None:
    name = (
        "dataset-release-v2"
        if type(manifest) is dict and manifest.get("contract_version") == REFERENCE_VERSION
        else "dataset-release"
    )
    validate_document(name, manifest)


def validate_dataset_release(manifest: dict, *, expected_release_ref: str) -> None:
    """Check the envelope and its declared roster. Use verify_payload for actual bytes."""
    _validate_release_document(manifest)
    if dataset_release_digest(manifest) != manifest["release_digest"]:
        raise ContractError("dataset release digest mismatch")
    if type(expected_release_ref) is not str or manifest["release_digest"] != expected_release_ref:
        raise ContractError("expected dataset release identity mismatch")
    version = manifest["contract_version"]
    artifacts = manifest["artifacts"]
    paths = [row["path"] for row in artifacts]
    if paths != sorted(set(paths)) or any(
        not valid_artifact_path(path, contract_version=version) for path in paths
    ):
        raise ContractError("unsafe, duplicate or noncanonical release artifact paths")
    sources = manifest["acquisition_sources"]
    source_refs = [source["source_ref"] for source in sources]
    raw_refs = [source["raw_source_ref"] for source in sources]
    if source_refs != sorted(set(source_refs)) or len(raw_refs) != len(set(raw_refs)):
        raise ContractError("duplicate or noncanonical release source identities")
    expected_paths = {"candidate.json", "quality-report.json"} | {
        source_artifact_path(source_ref) for source_ref in source_refs
    }
    by_path = {row["path"]: row for row in artifacts}
    if version == REFERENCE_VERSION:
        inventory = manifest["inventory"]
        validate_inventory_manifest(
            inventory, expected_inventory_ref=manifest["observations_digest"]
        )
        if inventory["observation_count"] != manifest["observation_count"]:
            raise ContractError("release inventory population mismatch")
        for artifact in inventory_artifacts(inventory):
            expected_paths.add(artifact["path"])
            if by_path.get(artifact["path"]) != artifact:
                raise ContractError("release inventory artifact identity mismatch")
        if (
            type(manifest["observation_count"]) is not int
            or any(type(manifest["dvc"][key]) is not int for key in ("file_count", "size_bytes"))
            or any(type(source["record_count"]) is not int for source in sources)
            or any(
                type(artifact["size_bytes"]) is not int
                or artifact["size_bytes"] > artifact_byte_limit(artifact["path"])
                for artifact in artifacts
            )
            or any(type(source["size_bytes"]) is not int for source in sources)
            or sum(source["size_bytes"] for source in sources) > MAX_REFERENCE_SOURCE_BYTES
        ):
            raise ContractError("invalid or oversized reference release totals")
    if set(paths) != expected_paths:
        raise ContractError("release artifact population mismatch")
    if manifest["dvc"]["file_count"] != len(artifacts) or manifest["dvc"]["size_bytes"] != sum(
        row["size_bytes"] for row in artifacts
    ):
        raise ContractError("release DVC artifact totals mismatch")
    if manifest["observation_count"] != sum(source["record_count"] for source in sources):
        raise ContractError("release observation population mismatch")
    for source in sources:
        artifact = by_path[source_artifact_path(source["source_ref"])]
        if (
            artifact["digest"] != source["source_ref"]
            or artifact["size_bytes"] != source["size_bytes"]
        ):
            raise ContractError("release source artifact identity mismatch")


def validate_release_candidate_binding(manifest: dict, candidate: dict) -> None:
    """Check declared correspondence; caller also validates the source-backed candidate."""
    _validate_release_document(manifest)
    validate_candidate_document(candidate)
    expected = {
        "contract_version": candidate["contract_version"],
        "dataset_family": candidate["dataset_family"],
        "candidate_ref": candidate["candidate_digest"],
        "observations_digest": candidate["observations_digest"],
        "observation_count": candidate["quality_report"]["observation_count"],
        "quality_report_ref": candidate["quality_report"]["report_digest"],
        "provenance": {key: candidate[key] for key in PROVENANCE_FIELDS},
        "acquisition_sources": candidate["sources"],
    }
    if any(manifest[key] != value for key, value in expected.items()):
        raise ContractError("release candidate provenance mismatch")
    if manifest["contract_version"] == REFERENCE_VERSION and canonical_json(
        manifest["inventory"]
    ) != canonical_json(candidate["inventory"]):
        raise ContractError("release candidate inventory identity mismatch")
    by_path = {row["path"]: row for row in manifest["artifacts"]}
    for path, document in (
        ("candidate.json", candidate),
        ("quality-report.json", candidate["quality_report"]),
    ):
        raw = canonical_json(document).encode("utf-8")
        artifact = by_path.get(path)
        if artifact != {"path": path, "digest": content_digest(raw), "size_bytes": len(raw)}:
            raise ContractError("release canonical artifact correspondence mismatch")


def build_dataset_release(
    candidate: dict,
    *,
    source_documents: list[bytes],
    binding: dict,
    artifacts: list[dict],
    inventory_directory: Path | None = None,
) -> dict:
    """Bind an already committed DVC metadata revision and verify the v2 inventory."""
    validate_candidate_document(candidate)
    validate_observation_candidate(
        candidate,
        source_documents=source_documents,
        expected_candidate_ref=candidate["candidate_digest"],
        inventory_directory=inventory_directory,
    )
    canonical_json(binding)
    canonical_json(artifacts)
    if type(binding) is not dict or set(binding) != {"metadata", "dvc"}:
        raise ContractError("invalid DVC metadata binding")
    manifest = {
        "contract_version": candidate["contract_version"],
        "dataset_family": candidate["dataset_family"],
        "access_domain": "development",
        "release_state": "SEALED_CANDIDATE",
        "retention": {"status": "PENDING_REVIEW", "policy_ref": None},
        "candidate_ref": candidate["candidate_digest"],
        "observation_schema_version": "1.0.0",
        "observations_digest": candidate["observations_digest"],
        "observation_count": candidate["quality_report"]["observation_count"],
        "quality_report_ref": candidate["quality_report"]["report_digest"],
        "provenance": {key: candidate[key] for key in PROVENANCE_FIELDS},
        "acquisition_sources": copy.deepcopy(candidate["sources"]),
        "metadata": copy.deepcopy(binding["metadata"]),
        "dvc": copy.deepcopy(binding["dvc"]),
        "artifacts": copy.deepcopy(artifacts),
    }
    if candidate["contract_version"] == REFERENCE_VERSION:
        manifest["inventory"] = copy.deepcopy(candidate["inventory"])
    manifest["release_digest"] = dataset_release_digest(manifest)
    validate_dataset_release(manifest, expected_release_ref=manifest["release_digest"])
    validate_release_candidate_binding(manifest, candidate)
    return manifest


def build_restoration_report(manifest: dict) -> dict:
    """Construct a report envelope. The adapter verifies recovery before installing it."""
    _validate_release_document(manifest)
    validate_dataset_release(manifest, expected_release_ref=manifest["release_digest"])
    report = {
        "contract_version": "1.0.0",
        "status": "PASSED",
        "verification_method": "fresh-local-dvc-pull-and-sha256-v1",
        "fresh_cache": True,
        "release_ref": manifest["release_digest"],
        "metadata_commit": manifest["metadata"]["commit"],
        "dvc_version": DVC_VERSION,
        "tool_profile_ref": manifest["dvc"]["tool_profile_ref"],
        "artifacts_digest": document_digest(manifest["artifacts"]),
        "artifact_count": len(manifest["artifacts"]),
        "observation_count": manifest["observation_count"],
        "observations_digest": manifest["observations_digest"],
        "runtime": {
            "python_version": platform.python_version(),
            "platform": sys.platform,
            "machine": platform.machine(),
        },
    }
    report["report_digest"] = restoration_report_digest(report)
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=manifest["release_digest"]
    )
    return report


def validate_restoration_report(report: dict, *, manifest: dict, expected_release_ref: str) -> None:
    validate_dataset_release(manifest, expected_release_ref=expected_release_ref)
    validate_document("restoration-report", report)
    if restoration_report_digest(report) != report["report_digest"]:
        raise ContractError("restoration report digest mismatch")
    expected = {
        "release_ref": expected_release_ref,
        "metadata_commit": manifest["metadata"]["commit"],
        "dvc_version": manifest["dvc"]["version"],
        "tool_profile_ref": manifest["dvc"]["tool_profile_ref"],
        "artifacts_digest": document_digest(manifest["artifacts"]),
        "artifact_count": len(manifest["artifacts"]),
        "observation_count": manifest["observation_count"],
        "observations_digest": manifest["observations_digest"],
    }
    if any(report[key] != value for key, value in expected.items()):
        raise ContractError("restoration report release correspondence mismatch")
