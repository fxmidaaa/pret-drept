import copy

import pytest

from rent_contracts import ContractError, load_document, validate_document
from rent_contracts.errors import EXIT_CODES, ErrorCategory
from rent_contracts.requests import ExperimentRequest
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json


def test_request_is_independent_of_mutable_caller_state(request_document, model_schemas):
    request = ExperimentRequest.from_document(request_document, model_schemas=model_schemas)
    identity = request.request_digest
    request_document["configuration"]["n_estimators"] = 900
    exported = request.to_document()
    assert exported["configuration"]["n_estimators"] == 3
    exported["configuration"]["n_estimators"] = 800
    assert request.request_digest == identity
    assert request.to_document()["configuration"]["n_estimators"] == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", "2.0.0"),
        ("random_seed", -1),
        ("random_seed", True),
        ("operation", "promote"),
        ("code_snapshot_ref", "main"),
        ("dataset_ref", "/private/data"),
        ("principal", "admin"),
        ("docker_args", ["--privileged"]),
        ("command", "arbitrary code"),
        ("host_mount", "/"),
        ("security_options", {}),
    ],
)
def test_experiment_rejects_privilege_knobs_and_mutable_identities(
    request_document, model_schemas, field, value
):
    request_document[field] = value
    with pytest.raises(ContractError):
        ExperimentRequest.from_document(request_document, model_schemas=model_schemas)


@pytest.mark.parametrize(
    "field,value",
    [
        ("memory_mib", 0),
        ("duration_seconds", -1),
        ("cpu_count", 0.5),
        ("gpu_count", -1),
        ("privileged", True),
    ],
)
def test_resource_shape_rejection(request_document, model_schemas, field, value):
    request_document["resource_profile"][field] = value
    with pytest.raises(ContractError):
        ExperimentRequest.from_document(request_document, model_schemas=model_schemas)


def test_adapter_registration_and_configuration_are_required(request_document, model_schemas):
    with pytest.raises(ContractError, match="unregistered"):
        ExperimentRequest.from_document(request_document, model_schemas={})
    request_document["configuration"]["unreviewed_option"] = "secret-value"
    with pytest.raises(ContractError) as failure:
        ExperimentRequest.from_document(request_document, model_schemas=model_schemas)
    assert "secret-value" not in str(failure.value)


def test_fourth_family_does_not_change_public_protocol(request_document, model_schemas):
    request_document["model_family"] = "fourth_family"
    model_schemas["fourth_family"] = model_schemas["xgboost"]
    ExperimentRequest.from_document(request_document, model_schemas=model_schemas)


def test_configuration_validation_never_fetches_remote_schema(request_document):
    schemas = {"xgboost": {"$ref": "https://invalid.example/secret-schema"}}
    with pytest.raises(ContractError, match="unresolved"):
        ExperimentRequest.from_document(request_document, model_schemas=schemas)


@pytest.mark.parametrize(
    "raw",
    [
        '{"a":1,"a":2}',
        '{"a":NaN}',
        '{"a":Infinity}',
        '{"a":-Infinity}',
        '{"a":1e999}',
        "[]",
        "{bad",
        b"\xff",
    ],
)
def test_non_json_and_ambiguous_documents_are_rejected(raw):
    with pytest.raises(ContractError):
        load_document(raw)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), (1, 2), {1: "bad"}])
def test_python_values_cannot_bypass_json_validation(value):
    with pytest.raises(ContractError):
        canonical_json({"nested": value})


def test_size_and_depth_limits_are_enforced():
    with pytest.raises(ContractError):
        load_document('{"x":"' + "a" * MAX_DOCUMENT_BYTES + '"}')
    value = {}
    for _ in range(66):
        value = {"nested": value}
    with pytest.raises(ContractError, match="nesting"):
        canonical_json(value)


def test_unknown_schema_and_sensitive_values_are_not_echoed(apartment):
    with pytest.raises(ContractError, match="unsupported"):
        validate_document("injected", apartment)
    apartment["sensitive-credential"] = "do-not-print"
    with pytest.raises(ContractError) as failure:
        validate_document("apartment", apartment)
    assert "sensitive-credential" not in str(failure.value)
    assert "do-not-print" not in str(failure.value)


def test_resolved_cli_contracts_are_distinct(request_document):
    train = {
        "contract_version": "1.0.0",
        "model_family": "xgboost",
        "configuration": {},
        "training_partition": "/inputs/train.parquet",
        "validation_partition": None,
        "dataset_ref": request_document["dataset_ref"],
        "split_ref": request_document["split_ref"],
        "random_seed": 42,
        "checkpoint_ref": None,
        "output_directory": "/outputs/candidate",
    }
    validate_document("train-request", train)
    invalid = copy.deepcopy(train)
    del invalid["random_seed"]
    with pytest.raises(ContractError):
        validate_document("train-request", invalid)
    predict = {
        "contract_version": "1.0.0",
        "bundle_ref": {"path": "/inputs/bundle", "digest": request_document["dataset_ref"]},
        "input_path": "/inputs/predict.parquet",
        "input_schema_version": "1.0.0",
        "inference_configuration": {},
        "output_path": "/outputs/predictions.parquet",
    }
    validate_document("predict-batch-request", predict)
    predict["inference_configuration"]["tolerant"] = True
    with pytest.raises(ContractError):
        validate_document("predict-batch-request", predict)


def test_all_error_categories_have_unique_nonzero_documented_exit_codes():
    assert set(EXIT_CODES) == set(ErrorCategory)
    assert len(set(EXIT_CODES.values())) == len(ErrorCategory)
    assert 0 not in EXIT_CODES.values()
