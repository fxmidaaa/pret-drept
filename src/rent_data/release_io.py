"""Exclusive local payload I/O and verification, not a storage authorization boundary."""

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

from rent_contracts import ContractError, load_document
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json

from ._artifact_io import (
    create_json_artifact as create_json_artifact,
)
from ._artifact_io import (
    open_exclusive_artifact,
    open_regular_artifact,
    owned_directory,
    resolved_local_path,
)
from ._artifact_io import (
    read_artifact as read_artifact,
)
from .candidates import (
    INLINE_VERSION,
    MAX_REFERENCE_SOURCE_BYTES,
    REFERENCE_VERSION,
    project_candidate_observations,
    validate_observation_candidate,
)
from .releases import (
    INVENTORY_DIRECTORY,
    INVENTORY_MANIFEST_PATH,
    INVENTORY_PARQUET_PATH,
    ReleaseError,
    artifact_byte_limit,
    content_digest,
    inventory_artifacts,
    source_artifact_path,
    valid_artifact_path,
    validate_dataset_release,
    validate_release_candidate_binding,
    validate_restoration_report,
)

COMPLETION_FILE = "restoration-report.json"
_COPY_CHUNK_BYTES = 65_536


def _file_identity(path: Path, *, limit: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with open_regular_artifact(path) as stream:
            if os.fstat(stream.fileno()).st_size > limit:
                raise ReleaseError("PAYLOAD_LIMIT")
            while chunk := stream.read(_COPY_CHUNK_BYTES):
                size += len(chunk)
                if size > limit:
                    raise ReleaseError("PAYLOAD_LIMIT")
                digest.update(chunk)
    except OSError:
        raise ReleaseError("ARTIFACT_READ_FAILED") from None
    return "sha256:" + digest.hexdigest(), size


def _release_directory(path: Path, manifest: dict) -> Path:
    if type(manifest) is dict and manifest.get("contract_version") == REFERENCE_VERSION:
        path = resolved_local_path(path)
    return owned_directory(path)


def _payload_paths(root: Path, contract_version: str) -> Iterator[tuple[str, Path]]:
    allowed_directories = {"sources"}
    if contract_version == REFERENCE_VERSION:
        root = resolved_local_path(root)
        allowed_directories.add(INVENTORY_DIRECTORY)
    elif contract_version != INLINE_VERSION:
        raise ContractError("unsupported release payload version")
    root = owned_directory(root)
    directories = [root]
    try:
        while directories:
            with os.scandir(directories.pop()) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    if entry.is_dir(follow_symlinks=False) and relative in allowed_directories:
                        directories.append(path)
                    elif valid_artifact_path(relative, contract_version=contract_version):
                        yield relative, path
                    else:
                        raise ReleaseError("UNEXPECTED_PAYLOAD_PATH")
    except OSError:
        raise ReleaseError("PAYLOAD_IO_FAILED") from None


def payload_inventory(root: Path, *, contract_version: str = INLINE_VERSION) -> list[dict]:
    """Hash the allowed paths for the selected payload format; this is staging evidence."""
    inventory = []
    source_bytes = 0
    for relative, path in _payload_paths(root, contract_version):
        if contract_version == REFERENCE_VERSION and len(inventory) >= MAX_DOCUMENT_BYTES // 100:
            # Every valid roster entry takes over 100 bytes in the bounded release JSON.
            raise ReleaseError("PAYLOAD_LIMIT")
        digest, size = _file_identity(path, limit=artifact_byte_limit(relative))
        if contract_version == REFERENCE_VERSION and relative.startswith("sources/"):
            source_bytes += size
            if source_bytes > MAX_REFERENCE_SOURCE_BYTES:
                raise ReleaseError("PAYLOAD_LIMIT")
        inventory.append({"path": relative, "digest": digest, "size_bytes": size})
    return sorted(inventory, key=lambda row: row["path"])


def _write_exclusive(path: Path, data: bytes) -> None:
    with open_exclusive_artifact(path) as stream:
        stream.write(data)


def _copy_parquet(source: Path, destination: Path, size_bytes: int) -> None:
    with open_regular_artifact(source) as reader, open_exclusive_artifact(destination) as writer:
        remaining = size_bytes
        while remaining:
            chunk = reader.read(min(remaining, _COPY_CHUNK_BYTES))
            if not chunk:
                raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
            writer.write(chunk)
            remaining -= len(chunk)
        if reader.read(1):
            raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")


def _bytes_entry(path: str, data: bytes) -> dict:
    return {"path": path, "digest": content_digest(data), "size_bytes": len(data)}


def write_payload(
    root: Path,
    candidate: dict,
    *,
    source_documents: list[bytes],
    expected_candidate_ref: str,
    inventory_directory: Path | None = None,
) -> list[dict]:
    """Stage a new payload and copy the exact inventory bytes for v2."""
    validate_observation_candidate(
        candidate,
        source_documents=source_documents,
        expected_candidate_ref=expected_candidate_ref,
        inventory_directory=inventory_directory,
    )
    candidate_bytes = canonical_json(candidate).encode("utf-8")
    documents = {
        "quality-report.json": canonical_json(candidate["quality_report"]).encode("utf-8"),
    }
    for raw in source_documents:
        documents[source_artifact_path(content_digest(raw))] = raw
    version = candidate["contract_version"]
    if version == REFERENCE_VERSION:
        root = resolved_local_path(root)
        inventory_directory = resolved_local_path(inventory_directory)
        if (
            root == inventory_directory
            or root in inventory_directory.parents
            or inventory_directory in root.parents
        ):
            raise ReleaseError("OVERLAPPING_INVENTORY_PAYLOAD")
    else:
        root = Path(root)
        documents["candidate.json"] = candidate_bytes
    if not root.is_absolute() or root.parent.is_symlink() or not root.parent.is_dir():
        raise ReleaseError("INVALID_DIRECTORY")
    try:
        root.mkdir(mode=0o700)
        (root / "sources").mkdir(mode=0o700)
        if version == REFERENCE_VERSION:
            (root / INVENTORY_DIRECTORY).mkdir(mode=0o700)
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("PAYLOAD_WRITE_FAILED") from None
    for relative, data in sorted(documents.items()):
        _write_exclusive(root / relative, data)
    if version == INLINE_VERSION:
        return payload_inventory(root)

    inventory = candidate["inventory"]
    _write_exclusive(root / INVENTORY_MANIFEST_PATH, canonical_json(inventory).encode("utf-8"))
    _copy_parquet(
        inventory_directory / inventory["artifact"]["path"],
        root / INVENTORY_PARQUET_PATH,
        inventory["artifact"]["size_bytes"],
    )
    expected = [_bytes_entry(path, data) for path, data in documents.items()]
    expected.extend(inventory_artifacts(inventory))
    if payload_inventory(root, contract_version=version) != sorted(
        expected, key=lambda item: item["path"]
    ):
        raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
    # Stage outside the closed roster so a cleanup failure cannot contaminate it.
    create_json_artifact(root / "candidate.json", candidate, staging_directory=root.parent)
    return sorted(
        [*expected, _bytes_entry("candidate.json", candidate_bytes)], key=lambda item: item["path"]
    )


def _verified_payload(
    manifest: dict, root: Path, *, expected_release_ref: str
) -> tuple[dict, list[dict]]:
    validate_dataset_release(manifest, expected_release_ref=expected_release_ref)
    version = manifest["contract_version"]
    remaining = {artifact["path"]: artifact for artifact in manifest["artifacts"]}
    documents = {}
    for relative, path in _payload_paths(root, version):
        artifact = remaining.pop(relative, None)
        if artifact is None:
            raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
        if relative in (INVENTORY_MANIFEST_PATH, INVENTORY_PARQUET_PATH):
            # Verified by the inventory reader against the exact bound manifest.
            continue
        raw = read_artifact(path)
        if _bytes_entry(relative, raw) != artifact:
            raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
        documents[relative] = raw
    if remaining:
        raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
    candidate = load_document(documents["candidate.json"])
    validate_release_candidate_binding(manifest, candidate)
    sources = [
        documents[source_artifact_path(row["source_ref"])]
        for row in manifest["acquisition_sources"]
    ]
    # The same full rebuild that validates the candidate also yields its complete projection.
    observations = project_candidate_observations(
        candidate,
        source_documents=sources,
        expected_candidate_ref=manifest["candidate_ref"],
        inventory_directory=Path(root) / INVENTORY_DIRECTORY
        if version == REFERENCE_VERSION
        else None,
    )
    if load_document(documents["quality-report.json"]) != candidate["quality_report"]:
        raise ContractError("standalone quality report correspondence mismatch")
    return candidate, observations


def verify_payload(manifest: dict, root: Path, *, expected_release_ref: str) -> dict:
    """Rehash all bytes and rebuild the candidate from every restored source envelope."""
    return _verified_payload(manifest, root, expected_release_ref=expected_release_ref)[0]


def finalize_restoration(
    destination: Path, report: dict, *, manifest: dict, expected_release_ref: str
) -> None:
    """Atomically create a completion report without replacing an existing file.

    Caller performs the actual DVC recovery. This single-writer completion protocol
    is development evidence, not authenticated verification or power-loss certification.
    """
    destination = _release_directory(destination, manifest)
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=expected_release_ref
    )
    verify_payload(manifest, destination / "payload", expected_release_ref=expected_release_ref)
    create_json_artifact(destination / COMPLETION_FILE, report)


def _read_restore(
    destination: Path, manifest: dict, expected_release_ref: str
) -> tuple[dict, list[dict]]:
    destination = _release_directory(destination, manifest)
    report = load_document(read_artifact(destination / COMPLETION_FILE))
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=expected_release_ref
    )
    return _verified_payload(
        manifest, destination / "payload", expected_release_ref=expected_release_ref
    )


def read_verified_restore(destination: Path, *, manifest: dict, expected_release_ref: str) -> dict:
    """Missing/partial/altered completion reports or payloads are never accepted."""
    return _read_restore(destination, manifest, expected_release_ref)[0]


def read_verified_restore_observations(
    destination: Path, *, manifest: dict, expected_release_ref: str
) -> list[dict]:
    """Return a fresh copy of the complete verified observation population.

    This is the same all-or-nothing verification as ``read_verified_restore`` for either
    release version. The rows are the source-backed rebuild from every restored envelope.
    For v2 that same pass has already matched the exact inventory bytes, schema and full
    population to the rebuild. Nothing is returned from a payload that failed any check.
    """
    return _read_restore(destination, manifest, expected_release_ref)[1]
