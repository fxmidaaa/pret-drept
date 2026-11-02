import pytest

from rent_contracts.bundles import bundle_manifest_digest

DIGEST = "sha256:" + "a" * 64


@pytest.fixture
def apartment():
    return {
        "record_id": "observation-1",
        "rooms": 2,
        "area": 55,
        "floor": 3,
        "total_floors": 9,
        "sector": "centru",
        "author": "agenție",
    }


@pytest.fixture
def request_document():
    return {
        "contract_version": "1.0.0",
        "task_ref": "RP-1",
        "operation": "train",
        "code_snapshot_ref": DIGEST,
        "dataset_ref": DIGEST,
        "split_ref": DIGEST,
        "model_family": "xgboost",
        "configuration": {"n_estimators": 3},
        "resource_profile": {
            "cpu_count": 1,
            "memory_mib": 512,
            "duration_seconds": 30,
            "gpu_count": 0,
        },
        "idempotency_key": "request-1",
        "random_seed": 42,
    }


@pytest.fixture
def model_schemas():
    # This is a contract fixture, not an implemented model adapter or training integration.
    return {
        "xgboost": {
            "type": "object",
            "properties": {"n_estimators": {"type": "integer", "minimum": 1}},
            "required": ["n_estimators"],
            "additionalProperties": False,
        }
    }


@pytest.fixture
def manifest():
    value = {
        "bundle_format_version": "1.0.0",
        "bundle_digest": DIGEST,
        "model_family": "xgboost",
        "provenance": {
            "source_snapshot": DIGEST,
            "reviewed_commit": None,
            "dataset_ref": DIGEST,
            "split_ref": DIGEST,
            "training_run": "run-1",
            "configuration_digest": DIGEST,
            "random_seed": 42,
        },
        "artifacts": [
            {"path": "model.ubj", "format": "xgboost-ubj", "size_bytes": 50, "digest": DIGEST},
            {"path": "preprocessing.json", "format": "json", "size_bytes": 20, "digest": DIGEST},
        ],
        "preprocessing": {
            "artifact_path": "preprocessing.json",
            "state_digest": DIGEST,
            "compatibility_version": "1.0.0",
        },
        "domain_contract": {
            "input_schema_version": "1.0.0",
            "output_protocol_version": "1.0.0",
            "target_unit": "EUR/month",
        },
        "adapter": {"name": "xgboost", "interface_version": "1.0.0"},
        "runtime": {
            "dependencies": [{"name": "xgboost", "version": "3.3.0"}],
            "platform_constraints": ["cpu"],
        },
        "checkpoints": [],
        "governance": {"license_ref": "review-required", "data_handling_restrictions": ["private"]},
    }
    value["bundle_digest"] = bundle_manifest_digest(value)
    return value


@pytest.fixture
def task_document():
    return {
        "contract_version": "1.0.0",
        "task_id": "RP-test",
        "objective": "Test lifecycle",
        "original_authorized_request": "Synthetic contract test only",
        "risk_level": "L1",
        "state": "PROPOSED",
        "scope_boundaries": ["test"],
        "protected_invariants": ["no deployment"],
        "acceptance_criteria": ["checks pass"],
        "implementation_plan": ["test"],
        "affected_modules": ["test"],
        "current_progress": [],
        "important_decisions": [],
        "verification_requirements": ["unit"],
        "verification_evidence": [],
        "execution_identifiers": {"runner": [], "mlflow": [], "ci": []},
        "pending_approvals": [],
        "known_blockers": [],
        "next_recovery_action": "Inspect Git state",
        "final_outcome": None,
        "history": [{"state": "PROPOSED", "timestamp": "2026-11-02T10:00:00Z"}],
    }
