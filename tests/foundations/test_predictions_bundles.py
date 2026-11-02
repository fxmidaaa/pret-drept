import copy

import pytest

from rent_contracts import ContractError
from rent_contracts.bundles import bundle_manifest_digest, validate_bundle_manifest
from rent_contracts.predictions import validate_prediction_correspondence

DIGEST = "sha256:" + "a" * 64


def result(records):
    return {
        "contract_version": "1.0.0",
        "bundle_digest": DIGEST,
        "target_unit": "EUR/month",
        "predictions": [
            {"record_id": row["record_id"], "predicted_rent_eur": 750.25} for row in records
        ],
    }


def test_predictions_correspond_by_identity_even_when_reordered(apartment):
    records = [apartment, {**apartment, "record_id": "observation-2"}]
    output = result(list(reversed(records)))
    validate_prediction_correspondence(records, output, expected_bundle_digest=DIGEST)


@pytest.mark.parametrize(
    "change", ["omitted", "duplicate", "substituted", "wrong-unit", "wrong-bundle", "nan"]
)
def test_prediction_population_and_identity_cannot_silently_change(apartment, change):
    records = [apartment, {**apartment, "record_id": "observation-2"}]
    output = result(records)
    if change == "omitted":
        output["predictions"].pop()
    if change == "duplicate":
        output["predictions"][1] = output["predictions"][0]
    if change == "substituted":
        output["predictions"][1]["record_id"] = "other"
    if change == "wrong-unit":
        output["target_unit"] = "MDL/month"
    if change == "wrong-bundle":
        output["bundle_digest"] = "sha256:" + "b" * 64
    if change == "nan":
        output["predictions"][0]["predicted_rent_eur"] = float("nan")
    with pytest.raises(ContractError):
        validate_prediction_correspondence(records, output, expected_bundle_digest=DIGEST)


@pytest.mark.parametrize(
    "field,value", [("price", 700), ("target", 700), ("area", -1), ("rooms", float("inf"))]
)
def test_invalid_record_fails_the_batch(apartment, field, value):
    invalid = {**apartment, field: value}
    with pytest.raises(ContractError):
        validate_prediction_correspondence(
            [invalid], result([invalid]), expected_bundle_digest=DIGEST
        )


def test_empty_and_duplicate_inputs_fail(apartment):
    with pytest.raises(ContractError):
        validate_prediction_correspondence([], result([]), expected_bundle_digest=DIGEST)
    with pytest.raises(ContractError):
        validate_prediction_correspondence(
            [apartment, apartment], result([apartment, apartment]), expected_bundle_digest=DIGEST
        )


def test_bundle_digest_has_no_circular_self_reference_and_binds_provenance(manifest):
    validate_bundle_manifest(manifest)
    digest = bundle_manifest_digest(manifest)
    manifest["bundle_digest"] = "sha256:" + "c" * 64
    assert bundle_manifest_digest(manifest) == digest
    manifest["bundle_digest"] = digest
    manifest["provenance"]["random_seed"] = 99
    with pytest.raises(ContractError, match="digest"):
        validate_bundle_manifest(manifest)


@pytest.mark.parametrize(
    "path",
    [
        "../escape",
        "/absolute",
        "a/../b",
        "a//b",
        "./file",
        "C:/file",
        "a\\b",
        "file\x00",
        "model.ubj",
    ],
)
def test_bundle_unsafe_and_duplicate_paths_fail(manifest, path):
    manifest["artifacts"][1]["path"] = path
    manifest["bundle_digest"] = bundle_manifest_digest(manifest)
    with pytest.raises(ContractError):
        validate_bundle_manifest(manifest)


def test_bundle_preprocessing_cannot_reference_an_undeclared_payload(manifest):
    manifest["preprocessing"]["artifact_path"] = "missing.json"
    manifest["bundle_digest"] = bundle_manifest_digest(manifest)
    with pytest.raises(ContractError, match="preprocessing"):
        validate_bundle_manifest(manifest)


def test_bundle_preprocessing_digest_must_match_its_declared_payload(manifest):
    manifest["preprocessing"]["state_digest"] = "sha256:" + "b" * 64
    manifest["bundle_digest"] = bundle_manifest_digest(manifest)
    with pytest.raises(ContractError, match="state identity"):
        validate_bundle_manifest(manifest)


def test_unknown_bundle_governance_cannot_embed_approval(manifest):
    changed = copy.deepcopy(manifest)
    changed["approval"] = "self-approved"
    with pytest.raises(ContractError):
        validate_bundle_manifest(changed)
