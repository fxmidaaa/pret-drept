"""Bounded local transport for an ordered v1 observation inventory."""

import hashlib
import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from rent_contracts import ContractError, load_document
from rent_contracts.evaluation import ObservationInventoryHasher
from rent_contracts.inventory import (
    MANIFEST_FILE,
    MAX_INVENTORY_RECORDS,
    MAX_MANIFEST_BYTES,
    MAX_PARQUET_BYTES,
    OBSERVATION_SCHEMA_PROFILE,
    PARQUET_FILE,
    WRITER_PROFILE,
    validate_inventory_manifest,
)
from rent_contracts.validation import canonical_json

from ._artifact_io import create_json_artifact, open_regular_artifact
from ._inventory_parquet import MAX_BATCH_ROWS, decoded_observations, open_parquet, write_parquet


@dataclass(frozen=True)
class InventoryLimits:
    """Local per-operation limits. Callers may choose smaller limits."""

    max_records: int = MAX_INVENTORY_RECORDS
    max_file_bytes: int = MAX_PARQUET_BYTES
    batch_rows: int = 1_024

    def __post_init__(self) -> None:
        for value, maximum in (
            (self.max_records, MAX_INVENTORY_RECORDS),
            (self.max_file_bytes, MAX_PARQUET_BYTES),
            (self.batch_rows, MAX_BATCH_ROWS),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ContractError("invalid observation inventory limits")


class _BoundedSink:
    def __init__(self, stream, max_bytes: int):
        self._stream = stream
        self._max_bytes = max_bytes

    @property
    def closed(self) -> bool:
        return self._stream.closed

    def tell(self) -> int:
        return self._stream.tell()

    def write(self, data: bytes) -> int:
        if self.tell() + len(data) > self._max_bytes:
            raise ContractError("inventory Parquet file limit exceeded")
        return self._stream.write(data)


def _inventory_path(path: Path) -> Path:
    try:
        path = Path(path)
        if (
            not path.is_absolute()
            or ".." in path.parts
            or path.parent.is_symlink()
            or not path.parent.is_dir()
        ):
            raise ContractError("invalid local inventory path")
    except (OSError, TypeError):
        raise ContractError("invalid local inventory path") from None
    return path


def _file_identity(stream, max_bytes: int) -> tuple[str, int]:
    try:
        digest = hashlib.sha256()
        size = os.fstat(stream.fileno()).st_size
        if not 12 <= size <= max_bytes:
            raise ContractError("invalid or oversized inventory Parquet file")
        remaining = size
        while remaining:
            chunk = stream.read(min(remaining, 65_536))
            if not chunk:
                raise ContractError("inventory Parquet file size mismatch")
            remaining -= len(chunk)
            digest.update(chunk)
        if stream.read(1):
            raise ContractError("inventory Parquet file size mismatch")
        return "sha256:" + digest.hexdigest(), size
    except OSError:
        raise ContractError("inventory Parquet file read failed") from None


def _check_roster(root: Path, expected: set[str]) -> None:
    try:
        if root.is_symlink() or not root.is_dir():
            raise ContractError("invalid local inventory directory")
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.name not in expected:
                    raise ContractError("unexpected local inventory artifact")
                expected.remove(entry.name)
        if expected:
            raise ContractError("incomplete local inventory")
    except OSError:
        raise ContractError("inventory directory read failed") from None


def _manifest(root: Path, *, expected_inventory_ref: str, expected_manifest: dict | None) -> dict:
    _check_roster(root, {MANIFEST_FILE, PARQUET_FILE})
    try:
        with open_regular_artifact(root / MANIFEST_FILE) as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    except OSError:
        raise ContractError("inventory manifest read failed") from None
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ContractError("inventory manifest size limit exceeded")
    manifest = load_document(raw)
    validate_inventory_manifest(manifest, expected_inventory_ref=expected_inventory_ref)
    if raw != canonical_json(manifest).encode("utf-8"):
        raise ContractError("inventory manifest must be canonical JSON")
    if expected_manifest is not None and raw != canonical_json(expected_manifest).encode("utf-8"):
        raise ContractError("observation inventory manifest identity mismatch")
    return manifest


def _verify_population(reader, manifest: dict, *, batch_rows: int) -> None:
    count = manifest["observation_count"]
    inventory = ObservationInventoryHasher(max_records=count)
    for row in decoded_observations(reader, batch_rows=batch_rows):
        inventory.add(row)
    if inventory.count != count or inventory.digest() != manifest["observations_digest"]:
        raise ContractError("observation inventory population or digest mismatch")


@contextmanager
def _verified_parquet(stream, manifest: dict, limits: InventoryLimits):
    with open_parquet(
        stream,
        size_bytes=manifest["artifact"]["size_bytes"],
        observation_count=manifest["observation_count"],
    ) as reader:
        _verify_population(reader, manifest, batch_rows=limits.batch_rows)
        yield reader


@contextmanager
def _open_verified_inventory(
    root: Path,
    *,
    expected_inventory_ref: str,
    limits: InventoryLimits,
    expected_manifest: dict | None = None,
):
    root = _inventory_path(root)
    manifest = _manifest(
        root, expected_inventory_ref=expected_inventory_ref, expected_manifest=expected_manifest
    )
    artifact = manifest["artifact"]
    if (
        manifest["observation_count"] > limits.max_records
        or artifact["size_bytes"] > limits.max_file_bytes
    ):
        raise ContractError("observation inventory exceeds local limits")
    with open_regular_artifact(root / PARQUET_FILE) as stream:
        if _file_identity(stream, limits.max_file_bytes) != (
            artifact["digest"],
            artifact["size_bytes"],
        ):
            raise ContractError("inventory Parquet file integrity mismatch")
        with _verified_parquet(stream, manifest, limits) as reader:
            yield manifest, reader


def _write_payload(
    root: Path, observations: Iterable[dict], limits: InventoryLimits
) -> tuple[int, str]:
    inventory = ObservationInventoryHasher(max_records=limits.max_records)
    try:
        root.mkdir(mode=0o700)
        descriptor = os.open(root / PARQUET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            write_parquet(
                _BoundedSink(stream, limits.max_file_bytes),
                observations,
                inventory=inventory,
                batch_rows=limits.batch_rows,
            )
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ContractError("observation inventory output already exists") from None
    except OSError:
        raise ContractError("inventory artifact write failed") from None
    return inventory.count, inventory.digest()


def write_observation_inventory(
    destination: Path,
    observations: Iterable[dict],
    *,
    limits: InventoryLimits = InventoryLimits(),
) -> dict:
    """Write ordered references into a new directory and finalize after readback.

    Use a caller-owned parent. Failed writes may leave an incomplete directory.
    """
    root = _inventory_path(destination)
    count, observations_digest = _write_payload(root, observations, limits)
    with open_regular_artifact(root / PARQUET_FILE) as stream:
        file_digest, size = _file_identity(stream, limits.max_file_bytes)
        manifest = {
            "contract_version": "1.0.0",
            "observation_contract_version": "1.0.0",
            "schema_profile": OBSERVATION_SCHEMA_PROFILE,
            "writer_profile": WRITER_PROFILE,
            "observation_count": count,
            "observations_digest": observations_digest,
            "artifact": {"path": PARQUET_FILE, "digest": file_digest, "size_bytes": size},
        }
        validate_inventory_manifest(manifest, expected_inventory_ref=observations_digest)
        with _verified_parquet(stream, manifest, limits):
            pass
    _check_roster(root, {PARQUET_FILE})
    create_json_artifact(root / MANIFEST_FILE, manifest)
    return manifest


def verify_observation_inventory(
    root: Path,
    *,
    expected_inventory_ref: str,
    limits: InventoryLimits = InventoryLimits(),
    expected_manifest: dict | None = None,
) -> dict:
    """Verify bytes, schema and population. If supplied, pin the exact manifest first."""
    with _open_verified_inventory(
        root,
        expected_inventory_ref=expected_inventory_ref,
        limits=limits,
        expected_manifest=expected_manifest,
    ) as (manifest, _):
        return manifest


def iter_verified_observations(
    root: Path, *, expected_inventory_ref: str, limits: InventoryLimits = InventoryLimits()
) -> Iterator[dict]:
    """Verify before yielding rows from the same open file. Keep it immutable during use."""
    with _open_verified_inventory(
        root, expected_inventory_ref=expected_inventory_ref, limits=limits
    ) as (_, reader):
        yield from decoded_observations(reader, batch_rows=limits.batch_rows)
