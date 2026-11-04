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


@pytest.fixture
def cli_request_documents(request_document):
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
    predict = {
        "contract_version": "1.0.0",
        "bundle_ref": {"path": "/inputs/bundle", "digest": request_document["dataset_ref"]},
        "input_path": "/inputs/predict.parquet",
        "input_schema_version": "1.0.0",
        "inference_configuration": {},
        "output_path": "/outputs/predictions.parquet",
    }
    return {"train-request": train, "predict-batch-request": predict}


def test_resolved_cli_contracts_are_distinct(cli_request_documents):
    train = cli_request_documents["train-request"]
    predict = cli_request_documents["predict-batch-request"]
    validate_document("train-request", train)
    invalid = copy.deepcopy(train)
    del invalid["random_seed"]
    with pytest.raises(ContractError):
        validate_document("train-request", invalid)
    validate_document("predict-batch-request", predict)
    predict["inference_configuration"]["tolerant"] = True
    with pytest.raises(ContractError):
        validate_document("predict-batch-request", predict)


def test_all_error_categories_have_unique_nonzero_documented_exit_codes():
    assert set(EXIT_CODES) == set(ErrorCategory)
    assert len(set(EXIT_CODES.values())) == len(ErrorCategory)
    assert 0 not in EXIT_CODES.values()


@pytest.fixture
def identifier_documents(
    apartment, request_document, manifest, task_document, cli_request_documents
):
    digest = request_document["dataset_ref"]
    manifest["checkpoints"] = [
        {"checkpoint_id": "checkpoint-1", "digest": digest, "license_ref": "test-license"}
    ]
    task_document["verification_evidence"] = [
        {"check": "unit", "status": "passed", "required": True, "reference": "test-report"}
    ]
    return {
        **cli_request_documents,
        "apartment": apartment,
        "bundle-manifest": manifest,
        "experiment-request": request_document,
        "prediction-batch": {
            "contract_version": "1.0.0",
            "bundle_digest": digest,
            "target_unit": "EUR/month",
            "predictions": [{"record_id": apartment["record_id"], "predicted_rent_eur": 750}],
        },
        "task-record": task_document,
    }


IDENTIFIER_CASES = (
    ("A", "z" + "0" * 123 + "._-X"),
    ("", ".id", "id/name", "é", "a" * 129),
)
DIGEST_CASES = (
    ("sha256:" + "0a" * 32,),
    ("sha256:" + "a" * 63, "sha256:" + "a" * 65, "sha256:" + "A" * 64, "sha512:" + "a" * 64),
)
GIT_COMMIT_CASES = (
    ("a" * 40, "0f" * 32),
    ("a" * 39, "a" * 41, "a" * 63, "a" * 65, "A" * 40),
)


@pytest.mark.parametrize(
    "schema_name, path, cases",
    [
        ("apartment", ("record_id",), IDENTIFIER_CASES),
        ("bundle-manifest", ("bundle_digest",), DIGEST_CASES),
        ("bundle-manifest", ("model_family",), IDENTIFIER_CASES),
        ("bundle-manifest", ("provenance", "source_snapshot"), DIGEST_CASES),
        ("bundle-manifest", ("provenance", "reviewed_commit"), GIT_COMMIT_CASES),
        ("bundle-manifest", ("provenance", "dataset_ref"), DIGEST_CASES),
        ("bundle-manifest", ("provenance", "split_ref"), DIGEST_CASES),
        ("bundle-manifest", ("provenance", "training_run"), IDENTIFIER_CASES),
        ("bundle-manifest", ("provenance", "configuration_digest"), DIGEST_CASES),
        ("bundle-manifest", ("artifacts", 0, "digest"), DIGEST_CASES),
        ("bundle-manifest", ("preprocessing", "state_digest"), DIGEST_CASES),
        ("bundle-manifest", ("adapter", "name"), IDENTIFIER_CASES),
        ("bundle-manifest", ("checkpoints", 0, "digest"), DIGEST_CASES),
        ("experiment-request", ("task_ref",), IDENTIFIER_CASES),
        ("experiment-request", ("code_snapshot_ref",), DIGEST_CASES),
        ("experiment-request", ("dataset_ref",), DIGEST_CASES),
        ("experiment-request", ("split_ref",), DIGEST_CASES),
        ("experiment-request", ("model_family",), IDENTIFIER_CASES),
        ("experiment-request", ("idempotency_key",), IDENTIFIER_CASES),
        ("predict-batch-request", ("bundle_ref", "digest"), DIGEST_CASES),
        ("prediction-batch", ("bundle_digest",), DIGEST_CASES),
        ("prediction-batch", ("predictions", 0, "record_id"), IDENTIFIER_CASES),
        ("task-record", ("task_id",), IDENTIFIER_CASES),
        ("task-record", ("verification_evidence", 0, "check"), IDENTIFIER_CASES),
        ("train-request", ("model_family",), IDENTIFIER_CASES),
        ("train-request", ("dataset_ref",), DIGEST_CASES),
        ("train-request", ("split_ref",), DIGEST_CASES),
        ("train-request", ("checkpoint_ref",), DIGEST_CASES),
    ],
)
def test_identifier_formats(schema_name, path, cases, identifier_documents):
    document = identifier_documents[schema_name]
    container = document
    for segment in path[:-1]:
        container = container[segment]
    field = path[-1]
    valid_values, invalid_values = cases
    for value in valid_values:
        container[field] = value
        validate_document(schema_name, document)
        for suffix in ("\n", "\r\n", "\r", "\t", "\x00", "\u2028", "\u2029", " "):
            container[field] = value + suffix
            with pytest.raises(ContractError, match="contract violation"):
                validate_document(schema_name, document)

    for value in invalid_values:
        container[field] = value
        with pytest.raises(ContractError, match="contract violation"):
            validate_document(schema_name, document)
