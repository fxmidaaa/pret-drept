"""Verified-restoration input and exclusive local split artifacts; no DVC mutation."""

from pathlib import Path

from rent_contracts import load_document

from .release_io import create_json_artifact, read_artifact, read_verified_restore_observations
from .releases import ReleaseError
from .splits import build_development_split, validate_release_split

SPLIT_FILE = "development-split.json"


def _separate_output(restored_directory: Path, destination: Path) -> Path:
    restored_directory, destination = Path(restored_directory), Path(destination)
    try:
        if (
            not restored_directory.is_absolute()
            or ".." in restored_directory.parts
            or restored_directory.is_symlink()
            or not restored_directory.is_dir()
            or not destination.is_absolute()
            or ".." in destination.parts
            or destination.is_symlink()
            or destination.parent.is_symlink()
            or not destination.parent.is_dir()
        ):
            raise ReleaseError("INVALID_SPLIT_DIRECTORY")
        source, output = restored_directory.resolve(), destination.resolve()
    except (OSError, RuntimeError):
        raise ReleaseError("INVALID_SPLIT_DIRECTORY") from None
    if source == output or source in output.parents or output in source.parents:
        raise ReleaseError("OVERLAPPING_SPLIT_DIRECTORY")
    return destination


def materialize_development_split(
    restored_directory: Path,
    destination: Path,
    *,
    release: dict,
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
    training_cutoff: str,
    validation_window: dict,
    creation_provenance: dict,
) -> dict:
    """Reverify an existing restored release and create one new local split artifact.

    Both inline v1 and reference-backed v2 releases are accepted; unsupported versions
    fail verification. Validate all metadata, including the complete split's one-document
    output bound, before creating the output directory. A failed write may leave that
    new directory, but no final split file. Never reuse an output path.
    """
    destination = _separate_output(restored_directory, destination)
    if destination.exists():
        raise ReleaseError("OUTPUT_EXISTS")
    observations = read_verified_restore_observations(
        restored_directory, manifest=release, expected_release_ref=expected_release_ref
    )
    manifest = build_development_split(
        release=release,
        observations=observations,
        policy=policy,
        expected_release_ref=expected_release_ref,
        expected_policy_ref=expected_policy_ref,
        training_cutoff=training_cutoff,
        validation_window=validation_window,
        creation_provenance=creation_provenance,
    )
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError:
        raise ReleaseError("OUTPUT_EXISTS") from None
    except OSError:
        raise ReleaseError("SPLIT_WRITE_FAILED") from None
    create_json_artifact(destination / SPLIT_FILE, manifest)
    return manifest


def read_verified_development_split(
    destination: Path,
    *,
    restored_directory: Path,
    release: dict,
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
    expected_split_ref: str,
) -> dict:
    """Recheck the restored release and the exact requested split before consumption."""
    destination = _separate_output(restored_directory, destination)
    if not destination.is_dir():
        raise ReleaseError("INVALID_SPLIT_DIRECTORY")
    observations = read_verified_restore_observations(
        restored_directory, manifest=release, expected_release_ref=expected_release_ref
    )
    manifest = load_document(read_artifact(destination / SPLIT_FILE))
    validate_release_split(
        manifest,
        release=release,
        observations=observations,
        policy=policy,
        expected_release_ref=expected_release_ref,
        expected_policy_ref=expected_policy_ref,
        expected_split_ref=expected_split_ref,
    )
    return manifest
