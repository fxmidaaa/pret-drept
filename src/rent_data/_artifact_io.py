"""Shared local regular-file and atomic JSON primitives for owned directories."""

import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from rent_contracts import ContractError
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json


class ReleaseError(ContractError):
    """Safe operational reason with no source rows, commands or tool output."""

    def __init__(self, code: str, *, exit_code: int | None = None):
        self.code = code
        self.exit_code = exit_code
        message = f"local release operation failed ({code})"
        if code in {"TOOL_UNAVAILABLE", "TOOL_VERSION_MISMATCH", "DATA_EXTRA_UNAVAILABLE"}:
            message += "; follow the separate data-tool setup in docs/development.md"
        super().__init__(message)


def resolved_local_path(path: Path) -> Path:
    """Require an absolute path without traversal or symlink components."""
    try:
        path = Path(path)
        if path.is_absolute() and ".." not in path.parts and path.resolve() == path:
            return path
    except (OSError, TypeError, ValueError):
        pass
    raise ReleaseError("INVALID_DIRECTORY")


def owned_directory(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ReleaseError("INVALID_DIRECTORY")
    return path


def open_regular_artifact(path: Path):
    descriptor = None
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ReleaseError("NONREGULAR_ARTIFACT")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ReleaseError("NONREGULAR_ARTIFACT")
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        return stream
    except OSError:
        raise ReleaseError("ARTIFACT_UNAVAILABLE") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_artifact(path: Path) -> bytes:
    try:
        with open_regular_artifact(path) as stream:
            data = stream.read(MAX_DOCUMENT_BYTES + 1)
    except OSError:
        raise ReleaseError("ARTIFACT_READ_FAILED") from None
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ReleaseError("PAYLOAD_LIMIT")
    return data


@contextmanager
def open_exclusive_artifact(path: Path):
    def private_opener(name, flags):
        return os.open(name, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)

    try:
        with open(path, "xb", opener=private_opener) as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("PAYLOAD_WRITE_FAILED") from None


def create_json_artifact(
    path: Path, document: dict, *, staging_directory: Path | None = None
) -> None:
    """Install bounded canonical JSON atomically without replacing an existing leaf.

    Callers validate semantics first. Staging and destination must be owned
    directories on the same filesystem.
    """
    path = Path(path)
    destination = owned_directory(path.parent)
    staging = destination if staging_directory is None else owned_directory(staging_directory)
    payload = canonical_json(document).encode("utf-8")
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".artifact-", dir=staging)
    except OSError:
        raise ReleaseError("FINALIZATION_FAILED") from None
    try:
        opened = os.fdopen(descriptor, "wb")
        descriptor = None
        with opened as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("FINALIZATION_FAILED") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except OSError:
            # Cleanup does not invalidate an installed final file.
            pass
