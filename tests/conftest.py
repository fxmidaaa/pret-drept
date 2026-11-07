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


@pytest.fixture(scope="session")
def large_observation_inventory(release_input_factory):
    """Synthetic identifiers sized to exceed the v1 aggregate JSON byte bound."""
    template = release_input_factory()["candidate"]["observations"][0]
    return [
        {
            **template,
            "observation_id": "synthetic-obs-".ljust(122, "o") + f"{index:06d}",
            "listing_id": "synthetic-listing-".ljust(122, "l") + f"{index:06d}",
            "property_identity": {
                **template["property_identity"],
                "property_id": "synthetic-property-".ljust(122, "p") + f"{index:06d}",
                "confidence": 1.0,
            },
        }
        for index in range(1_800)
    ]


@pytest.fixture(scope="session")
def split_input_factory(release_input_factory):
    """Invented split metadata/provenance only; no clock, private rows or DVC claim."""
    import copy

    from rent_contracts.evaluation import evaluation_policy_digest
    from rent_data.candidates import build_observation_candidate
    from rent_data.releases import content_digest

    def make(*, observations=None):
        base = release_input_factory()
        template = base["candidate"]["observations"][0]

        def row(key, listing, property_id, instant, *, status="confirmed", domain="valid"):
            value = copy.deepcopy(template)
            value.update(observation_id=key, listing_id=listing, domain_status=domain)
            value["property_identity"].update(status=status, property_id=property_id)
            for field in (
                "published_at",
                "collected_at",
                "features_available_at",
                "prediction_cutoff_at",
            ):
                value[field] = instant
            value["temporal_evidence_ref"] = (
                content_digest(b"synthetic temporal evidence") if instant else None
            )
            return value

        if observations is None:
            observations = [
                row("obs-train-a", "listing-a", "property-a", "2026-01-10T12:00:00Z"),
                row("obs-train-b", "listing-b", "property-b", "2026-01-11T12:00:00Z"),
                row("obs-seen", "listing-seen", "property-a", "2026-02-10T12:00:00Z"),
                row("obs-refresh", "listing-a", "property-a", "2026-02-11T12:00:00Z"),
                row("obs-new", "listing-new", "property-new", "2026-02-12T12:00:00Z"),
                row(
                    "obs-probable",
                    "listing-probable",
                    "property-probable",
                    "2026-02-13T12:00:00Z",
                    status="probable",
                ),
                row(
                    "obs-unresolved",
                    "listing-unresolved",
                    None,
                    "2026-02-14T12:00:00Z",
                    status="unresolved",
                ),
                row("obs-notime", "listing-notime", "property-notime", None),
                row(
                    "obs-invalid",
                    "listing-invalid",
                    "property-invalid",
                    "2026-02-15T12:00:00Z",
                    domain="invalid",
                ),
                row(
                    "obs-pending",
                    "listing-pending",
                    "property-pending",
                    "2026-02-16T12:00:00Z",
                    domain="unresolved",
                ),
                row("obs-gap", "listing-gap", "property-gap", "2026-01-25T12:00:00Z"),
                row("obs-end", "listing-end", "property-end", "2026-03-01T00:00:00Z"),
                row(
                    "obs-multi",
                    "listing-multi",
                    "property-multi",
                    "2026-03-02T12:00:00Z",
                    domain="invalid",
                ),
            ]
            observations[-1]["features_available_at"] = "2026-03-03T12:00:00Z"
            observations[-1]["temporal_evidence_ref"] = None
        groups = [observations] if len(observations) <= 2 else [observations[:2], observations[2:]]
        sources = []
        for raw, group in zip(base["sources"], groups):
            source = json.loads(raw)
            source["records"] = [
                {"source_record_id": f"synthetic-capture-{index}", "observation": item}
                for index, item in enumerate(group)
            ]
            sources.append(json.dumps(source, ensure_ascii=False, indent=2).encode("utf-8"))
        candidate = build_observation_candidate(sources, **base["recipe"])
        policy = {
            "contract_version": "1.0.0",
            "policy_version": "synthetic-split-v1",
            "domain_policy_ref": base["recipe"]["domain_policy_ref"],
            "property_matching_policy_ref": base["recipe"]["property_matching_policy_ref"],
            "selection_basis": "non_target_metadata_only",
            "property_matching_basis": "non_target_signals_only",
            "eligibility_rule": "non_target_domain_and_observation_time_v1",
            "unseen_property_rule": "confirmed_absence_from_resolved_training_v1",
            "target_unit": "EUR/month",
        }
        policy["policy_digest"] = evaluation_policy_digest(policy)
        return {
            "candidate": candidate,
            "sources": sources,
            "recipe": base["recipe"],
            "policy": policy,
            "parameters": {
                "training_cutoff": "2026-01-20T00:00:00Z",
                "validation_window": {
                    "start_inclusive": "2026-02-01T00:00:00Z",
                    "end_exclusive": "2026-03-01T00:00:00Z",
                },
                "creation_provenance": {
                    "source_snapshot_ref": content_digest(b"synthetic split source snapshot"),
                    "created_at": "2026-03-03T12:00:00Z",
                },
            },
        }

    return make
