"""Population checks for future batch inference and trusted verification (§12.6)."""

from .validation import ContractError, validate_document


def validate_prediction_correspondence(
    input_records: list[dict], result: dict, *, expected_bundle_digest: str
) -> None:
    """Fail the whole batch for invalid inputs, substitutions, omissions or duplicates."""
    if not input_records:
        raise ContractError("prediction batch is empty")
    for record in input_records:
        validate_document("apartment", record)
    expected = [record["record_id"] for record in input_records]
    if len(set(expected)) != len(expected):
        raise ContractError("duplicate input record identity")
    validate_document("prediction-batch", result)
    if result["bundle_digest"] != expected_bundle_digest:
        raise ContractError("prediction bundle identity mismatch")
    actual = [row["record_id"] for row in result["predictions"]]
    if len(set(actual)) != len(actual) or set(actual) != set(expected):
        raise ContractError("prediction population mismatch")
