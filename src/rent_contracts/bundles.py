"""Manifest validation only. This does not load, trust or certify model payloads."""

import hashlib
from pathlib import PurePosixPath

from .validation import ContractError, canonical_json, validate_document


def bundle_manifest_digest(manifest: dict) -> str:
    """Hash the complete canonical manifest except its top-level self-reference (§11.2)."""
    body = {key: value for key, value in manifest.items() if key != "bundle_digest"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def validate_bundle_manifest(manifest: dict) -> None:
    validate_document("bundle-manifest", manifest)
    paths = set()
    for artifact in manifest["artifacts"]:
        path = artifact["path"]
        parts = path.split("/")
        if (
            not path
            or "\\" in path
            or ":" in path
            or "\x00" in path
            or PurePosixPath(path).is_absolute()
            or any(part in ("", ".", "..") for part in parts)
            or path in paths
        ):
            raise ContractError("unsafe or duplicate bundle artifact path")
        paths.add(path)
    if manifest["preprocessing"]["artifact_path"] not in paths:
        raise ContractError("preprocessing artifact is not declared")
    preprocessing_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["path"] == manifest["preprocessing"]["artifact_path"]
    )
    if preprocessing_artifact["digest"] != manifest["preprocessing"]["state_digest"]:
        raise ContractError("preprocessing state identity mismatch")
    if bundle_manifest_digest(manifest) != manifest["bundle_digest"]:
        raise ContractError("bundle manifest digest mismatch")
