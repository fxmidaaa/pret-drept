"""Public observation inventory manifest and expected logical identity."""

from .validation import ContractError, validate_document

MANIFEST_FILE = "observation-inventory.json"
PARQUET_FILE = "observations.parquet"
OBSERVATION_SCHEMA_PROFILE = "observation-reference-parquet-v1"
PYARROW_VERSION = "26.0.1"
WRITER_PROFILE = f"pyarrow-{PYARROW_VERSION}-parquet-2.6-uncompressed-v1"
MAX_INVENTORY_RECORDS = 100_000
MAX_MANIFEST_BYTES = 8 * 1024
MAX_PARQUET_BYTES = 128 * 1024 * 1024


def validate_inventory_manifest(manifest: dict, *, expected_inventory_ref: str) -> None:
    """Validate a manifest against a logical identity supplied by the caller."""
    validate_document("observation-inventory", manifest)
    if (
        type(manifest["observation_count"]) is not int
        or type(manifest["artifact"]["size_bytes"]) is not int
    ):
        raise ContractError("inventory manifest requires integer totals")
    if (
        type(expected_inventory_ref) is not str
        or manifest["observations_digest"] != expected_inventory_ref
    ):
        raise ContractError("expected observation inventory identity mismatch")
