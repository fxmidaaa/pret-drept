import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def require_legacy_artifact(request):
    if request.node.get_closest_marker("legacy_artifact"):
        artifact = Path(__file__).resolve().parents[1] / "model.joblib"
        if not artifact.is_file():
            pytest.skip("private legacy model.joblib absent; no artifact result is claimed")


@pytest.fixture(scope="session")
def release_input_factory():
    """Fresh hand-written synthetic metadata, shared by core and real DVC tests."""
    from rent_data.candidates import build_observation_candidate

    def make(revision="A"):
        def ref(label):
            return "sha256:" + hashlib.sha256(f"synthetic release {label}".encode()).hexdigest()

        recipe = {
            "dataset_family": "synthetic-release-fixture",
            "transformation_ref": ref("transformation"),
            "projection_policy_ref": ref("projection"),
            "domain_policy_ref": ref("domain"),
            "property_matching_policy_ref": ref("matching"),
        }
        rows = []
        for index in range(4):
            # These dates are invented fixtures, never assertions about historical data.
            instant = f"2026-01-{10 + index}T12:00:00Z" if index != 2 else None
            rows.append(
                {
                    "contract_version": "1.0.0",
                    "observation_id": f"synthetic-{revision}-{index}",
                    "listing_id": f"synthetic-{revision}-listing-{index // 2}",
                    "property_identity": {
                        "status": "unresolved" if index == 2 else "confirmed",
                        "property_id": None if index == 2 else f"synthetic-property-{index // 2}",
                        "confidence": None,
                        "policy_ref": recipe["property_matching_policy_ref"],
                    },
                    "domain_policy_ref": recipe["domain_policy_ref"],
                    "domain_status": "invalid" if index == 3 else "valid",
                    "published_at": instant,
                    "collected_at": instant,
                    "features_available_at": instant,
                    "prediction_cutoff_at": instant,
                    "temporal_evidence_ref": ref("time evidence") if instant else None,
                }
            )
        rows[3]["features_available_at"] = "2026-01-12T12:00:00Z"
        sources = [
            json.dumps(
                {
                    "contract_version": "1.0.0",
                    "raw_source_ref": ref(f"raw {revision} {index}"),
                    "acquisition_provenance_ref": None,
                    "acquisition_period": {"start": None, "end": None},
                    "records": [
                        {"source_record_id": f"capture-{offset}", "observation": row}
                        for offset, row in enumerate(group)
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            for index, group in enumerate((rows[:2], rows[2:]))
        ]
        return {
            "candidate": build_observation_candidate(sources, **recipe),
            "sources": sources,
            "recipe": recipe,
        }

    return make
