"""Exclusive local payload I/O and verification, not a storage authorization boundary."""

import hashlib
import os
import stat
import tempfile
from pathlib import Path

from rent_contracts import ContractError, load_document
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json

from .candidates import validate_observation_candidate
from .releases import (
    ReleaseError,
    content_digest,
    source_artifact_path,
    valid_artifact_path,
    validate_dataset_release,
    validate_release_candidate_binding,
    validate_restoration_report,
)

COMPLETION_FILE = "restoration-report.json"


def _regular_reader(path: Path):
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ReleaseError("NONREGULAR_ARTIFACT")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ReleaseError("NONREGULAR_ARTIFACT")
        return os.fdopen(descriptor, "rb")
    except OSError:
        raise ReleaseError("ARTIFACT_UNAVAILABLE") from None


def read_artifact(path: Path) -> bytes:
    try:
        with _regular_reader(path) as stream:
            data = stream.read(MAX_DOCUMENT_BYTES + 1)
    except OSError:
        raise ReleaseError("ARTIFACT_READ_FAILED") from None
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ReleaseError("PAYLOAD_LIMIT")
    return data


def _file_identity(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with _regular_reader(path) as stream:
        while chunk := stream.read(65_536):
            size += len(chunk)
            if size > MAX_DOCUMENT_BYTES:
                raise ReleaseError("PAYLOAD_LIMIT")
            digest.update(chunk)
    return "sha256:" + digest.hexdigest(), size


def _owned_directory(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReleaseError("INVALID_DIRECTORY")
    return path


def payload_inventory(root: Path) -> list[dict]:
    """The fixed v1 tree admits only regular artifacts and its sources directory."""
    root = _owned_directory(root)
    inventory = []
    try:
        for directory, dirs, files in os.walk(root, followlinks=False):
            parent = Path(directory)
            relative = parent.relative_to(root).as_posix()
            if relative not in (".", "sources"):
                raise ReleaseError("UNEXPECTED_PAYLOAD_PATH")
            for name in dirs:
                child = parent / name
                if child.is_symlink() or child.relative_to(root).as_posix() != "sources":
                    raise ReleaseError("UNEXPECTED_PAYLOAD_PATH")
            for name in files:
                path = parent / name
                relative_path = path.relative_to(root).as_posix()
                if not valid_artifact_path(relative_path):
                    raise ReleaseError("UNEXPECTED_PAYLOAD_PATH")
                digest, size = _file_identity(path)
                inventory.append({"path": relative_path, "digest": digest, "size_bytes": size})
    except OSError:
        raise ReleaseError("PAYLOAD_IO_FAILED") from None
    return sorted(inventory, key=lambda row: row["path"])


def _write_exclusive(path: Path, data: bytes) -> None:
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("PAYLOAD_WRITE_FAILED") from None


def write_payload(
    root: Path, candidate: dict, *, source_documents: list[bytes], expected_candidate_ref: str
) -> list[dict]:
    """Prepare a new payload only. A partial directory is not a verified restoration."""
    validate_observation_candidate(
        candidate, source_documents=source_documents, expected_candidate_ref=expected_candidate_ref
    )
    documents = {
        "candidate.json": canonical_json(candidate).encode("utf-8"),
        "quality-report.json": canonical_json(candidate["quality_report"]).encode("utf-8"),
    }
    for raw in source_documents:
        documents[source_artifact_path(content_digest(raw))] = raw
    root = Path(root)
    if not root.is_absolute() or root.parent.is_symlink() or not root.parent.is_dir():
        raise ReleaseError("INVALID_DIRECTORY")
    try:
        root.mkdir(mode=0o700)
        (root / "sources").mkdir(mode=0o700)
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("PAYLOAD_WRITE_FAILED") from None
    for relative, data in sorted(documents.items()):
        _write_exclusive(root / relative, data)
    return payload_inventory(root)


def verify_payload(manifest: dict, root: Path, *, expected_release_ref: str) -> dict:
    """Rehash all bytes and rebuild the candidate from every restored source envelope."""
    validate_dataset_release(manifest, expected_release_ref=expected_release_ref)
    if payload_inventory(root) != manifest["artifacts"]:
        raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
    documents = {}
    for artifact in manifest["artifacts"]:
        raw = read_artifact(Path(root) / artifact["path"])
        if len(raw) != artifact["size_bytes"] or content_digest(raw) != artifact["digest"]:
            raise ReleaseError("ARTIFACT_INTEGRITY_MISMATCH")
        documents[artifact["path"]] = raw
    candidate = load_document(documents["candidate.json"])
    sources = [
        documents[source_artifact_path(row["source_ref"])]
        for row in manifest["acquisition_sources"]
    ]
    validate_observation_candidate(
        candidate, source_documents=sources, expected_candidate_ref=manifest["candidate_ref"]
    )
    if load_document(documents["quality-report.json"]) != candidate["quality_report"]:
        raise ContractError("standalone quality report correspondence mismatch")
    validate_release_candidate_binding(manifest, candidate)
    return candidate


def finalize_restoration(
    destination: Path, report: dict, *, manifest: dict, expected_release_ref: str
) -> None:
    """Atomically create a completion report without replacing an existing file.

    Caller performs the actual DVC recovery. This single-writer completion protocol
    is development evidence, not authenticated verification or power-loss certification.
    """
    destination = _owned_directory(destination)
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=expected_release_ref
    )
    verify_payload(manifest, destination / "payload", expected_release_ref=expected_release_ref)
    create_json_artifact(destination / COMPLETION_FILE, report)


def create_json_artifact(path: Path, document: dict) -> None:
    """Atomically create one bounded JSON artifact, refusing any existing leaf.

    Callers validate document semantics first. This single-writer primitive supplies
    no authorization, power-loss certification or directory transaction semantics.
    """
    path = Path(path)
    destination = _owned_directory(path.parent)
    payload = canonical_json(document).encode("utf-8")
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".artifact-", dir=destination)
    except OSError:
        raise ReleaseError("FINALIZATION_FAILED") from None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Link is atomic and fails if the destination exists; replacing it is forbidden.
        os.link(temporary, path)
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("FINALIZATION_FAILED") from None
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            # Cleanup cannot turn an incomplete restore into a completed one, or
            # invalidate an already installed completion report.
            pass


def read_verified_restore(destination: Path, *, manifest: dict, expected_release_ref: str) -> dict:
    """Missing/partial/altered completion reports or payloads are never accepted."""
    destination = _owned_directory(destination)
    report = load_document(read_artifact(destination / COMPLETION_FILE))
    validate_restoration_report(
        report, manifest=manifest, expected_release_ref=expected_release_ref
    )
    return verify_payload(
        manifest, destination / "payload", expected_release_ref=expected_release_ref
    )
