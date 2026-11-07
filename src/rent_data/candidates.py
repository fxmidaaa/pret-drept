"""Deterministic metadata candidates from supplied source envelopes (§§8–9).

Optional local inventory verification. Source envelopes arrive as explicit bytes.
No raw-data projection, network access, matching, split selection or publication.
Raw-source and policy references are declarations, not authorization or verified truth.
"""

import hashlib
from datetime import datetime
from pathlib import Path

from rent_contracts import ContractError, load_document, validate_document
from rent_contracts.evaluation import (
    ObservationInventoryHasher,
    observation_eligibility_exclusions,
    observation_inventory_digest,
)
from rent_contracts.inventory import MAX_INVENTORY_RECORDS
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json

from ._artifact_io import resolved_local_path
from .inventory_io import verify_observation_inventory

INLINE_VERSION = "1.0.0"
REFERENCE_VERSION = "2.0.0"
MAX_REFERENCE_SOURCE_BYTES = 4 * MAX_DOCUMENT_BYTES
PROVENANCE_FIELDS = (
    "transformation_ref",
    "projection_policy_ref",
    "domain_policy_ref",
    "property_matching_policy_ref",
)


def _digest(document: dict | list) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def observation_candidate_digest(candidate: dict) -> str:
    """Use local v1 canonical JSON, excluding only the top-level self-reference."""
    return _digest({key: value for key, value in candidate.items() if key != "candidate_digest"})


def observation_quality_report_digest(report: dict) -> str:
    return _digest({key: value for key, value in report.items() if key != "report_digest"})


def _instant(value: str | None) -> datetime | None:
    # Envelopes have already passed the shared instant syntax. Calendar validation
    # must also work without optional JSON Schema format dependencies.
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise ContractError("invalid source acquisition instant") from None


def _source_inventory(
    source_documents: list[bytes], *, reference_backed: bool
) -> tuple[list[dict], list[dict], list[dict]]:
    if (
        type(source_documents) is not list
        or not source_documents
        or (reference_backed and len(source_documents) > MAX_INVENTORY_RECORDS)
        or any(type(raw) is not bytes for raw in source_documents)
    ):
        raise ContractError("source documents must be a nonempty list of UTF-8 bytes")
    limit = MAX_REFERENCE_SOURCE_BYTES if reference_backed else MAX_DOCUMENT_BYTES
    if sum(len(raw) for raw in source_documents) > limit:
        raise ContractError("source inventory size limit exceeded")
    sources, observations, lineage = [], [], []
    source_refs, raw_refs = set(), set()
    for raw in source_documents:
        source = load_document(raw)
        validate_document("observation-source", source)
        source_ref = "sha256:" + hashlib.sha256(raw).hexdigest()
        if source_ref in source_refs or source["raw_source_ref"] in raw_refs:
            raise ContractError("duplicate source or raw-source reference")
        source_refs.add(source_ref)
        raw_refs.add(source["raw_source_ref"])
        start = _instant(source["acquisition_period"]["start"])
        end = _instant(source["acquisition_period"]["end"])
        if start is not None and end is not None and start > end:
            raise ContractError("source acquisition period is reversed")
        record_ids = set()
        for record in source["records"]:
            if record["source_record_id"] in record_ids:
                raise ContractError("duplicate source record identity")
            record_ids.add(record["source_record_id"])
            observation = record["observation"]
            collected = _instant(observation["collected_at"])
            if collected is not None and (
                (start is not None and collected < start) or (end is not None and collected > end)
            ):
                raise ContractError("collection instant contradicts source acquisition period")
            observations.append(observation)
            lineage.append(
                {
                    "observation_id": observation["observation_id"],
                    "source_ref": source_ref,
                    "source_record_id": record["source_record_id"],
                }
            )
        sources.append(
            {
                "source_ref": source_ref,
                "raw_source_ref": source["raw_source_ref"],
                "size_bytes": len(raw),
                "record_count": len(source["records"]),
                "acquisition_provenance_ref": source["acquisition_provenance_ref"],
                "acquisition_period": source["acquisition_period"],
            }
        )
    return (
        sorted(sources, key=lambda row: row["source_ref"]),
        sorted(observations, key=lambda row: row["observation_id"]),
        sorted(lineage, key=lambda row: row["observation_id"]),
    )


def _quality_report(sources: list[dict], observations: list[dict], inventory_digest: str) -> dict:
    issues = {
        "invalid_non_target_domain": 0,
        "unresolved_non_target_domain": 0,
        "temporal_evidence_missing": 0,
        "temporal_order_invalid": 0,
    }
    property_counts = {"confirmed": 0, "probable": 0, "unresolved": 0}
    affected = 0
    for observation in observations:
        reasons = observation_eligibility_exclusions(observation)
        affected += bool(reasons)
        for reason in reasons:
            issues[reason] += 1
        property_counts[observation["property_identity"]["status"]] += 1
    report = {
        "contract_version": "1.0.0",
        "assessment_version": "1.0.0",
        "observations_digest": inventory_digest,
        "sources_digest": _digest(sources),
        "observation_count": len(observations),
        "listing_count": len({row["listing_id"] for row in observations}),
        "observations_with_eligibility_issues": affected,
        "property_resolution_counts": property_counts,
        "eligibility_issue_counts": issues,
        "source_counts": {
            "total": len(sources),
            "missing_acquisition_provenance": sum(
                source["acquisition_provenance_ref"] is None for source in sources
            ),
            "missing_period_start": sum(
                source["acquisition_period"]["start"] is None for source in sources
            ),
            "missing_period_end": sum(
                source["acquisition_period"]["end"] is None for source in sources
            ),
        },
    }
    report["report_digest"] = observation_quality_report_digest(report)
    return report


def _build_candidate(
    source_documents: list[bytes],
    recipe: dict,
    *,
    inventory_directory: Path | None,
    expected_manifest: dict | None = None,
) -> tuple[dict, list[dict]]:
    reference_backed = inventory_directory is not None
    sources, observations, lineage = _source_inventory(
        source_documents, reference_backed=reference_backed
    )
    if reference_backed:
        hasher = ObservationInventoryHasher(max_records=MAX_INVENTORY_RECORDS)
        for observation in observations:
            hasher.add(observation)
        inventory_digest = hasher.digest()
    else:
        inventory_digest = observation_inventory_digest(observations)
    for observation in observations:
        if observation["domain_policy_ref"] != recipe["domain_policy_ref"]:
            raise ContractError("candidate domain policy identity mismatch")
        if observation["property_identity"]["policy_ref"] != recipe["property_matching_policy_ref"]:
            raise ContractError("candidate matching policy identity mismatch")
    candidate = {
        "contract_version": REFERENCE_VERSION if reference_backed else INLINE_VERSION,
        "dataset_family": recipe["dataset_family"],
        "access_domain": "development",
        "release_state": "UNPUBLISHED_CANDIDATE",
        **{key: recipe[key] for key in PROVENANCE_FIELDS},
        "observations_digest": inventory_digest,
        "sources": sources,
        "lineage": lineage,
    }
    if reference_backed:
        manifest = verify_observation_inventory(
            resolved_local_path(inventory_directory),
            expected_inventory_ref=inventory_digest,
            expected_manifest=expected_manifest,
        )
        if manifest["observation_count"] != len(observations):
            raise ContractError("candidate inventory population mismatch")
        candidate["inventory"] = manifest
    else:
        candidate["observations"] = observations
    candidate["quality_report"] = _quality_report(sources, observations, inventory_digest)
    candidate["candidate_digest"] = observation_candidate_digest(candidate)
    validate_candidate_document(candidate)
    return candidate, observations


def build_observation_candidate(
    source_documents: list[bytes],
    *,
    dataset_family: str,
    transformation_ref: str,
    projection_policy_ref: str,
    domain_policy_ref: str,
    property_matching_policy_ref: str,
    inventory_directory: Path | None = None,
) -> dict:
    """Build an unpublished candidate, using v2 when given a local inventory directory.

    The supplied metadata envelopes are the complete projection. An inventory
    must match all observations and pass verification before its reference is bound.
    """
    candidate, _ = _build_candidate(
        source_documents,
        {
            "dataset_family": dataset_family,
            "transformation_ref": transformation_ref,
            "projection_policy_ref": projection_policy_ref,
            "domain_policy_ref": domain_policy_ref,
            "property_matching_policy_ref": property_matching_policy_ref,
        },
        inventory_directory=inventory_directory,
    )
    return candidate


def validate_candidate_document(candidate: dict) -> None:
    """Check the envelope syntax of a supported candidate version."""
    name = (
        "observation-candidate-v2"
        if type(candidate) is dict and candidate.get("contract_version") == REFERENCE_VERSION
        else "observation-candidate"
    )
    validate_document(name, candidate)


def _verified_projection(
    candidate: dict,
    *,
    source_documents: list[bytes],
    expected_candidate_ref: str,
    inventory_directory: Path | None,
) -> list[dict]:
    validate_candidate_document(candidate)
    if (candidate["contract_version"] == REFERENCE_VERSION) != (inventory_directory is not None):
        raise ContractError("candidate version and inventory directory mismatch")
    if observation_candidate_digest(candidate) != candidate["candidate_digest"]:
        raise ContractError("observation candidate digest mismatch")
    if (
        type(expected_candidate_ref) is not str
        or candidate["candidate_digest"] != expected_candidate_ref
    ):
        raise ContractError("expected observation candidate identity mismatch")
    report = candidate["quality_report"]
    if observation_quality_report_digest(report) != report["report_digest"]:
        raise ContractError("observation quality report digest mismatch")
    rebuilt, observations = _build_candidate(
        source_documents,
        {key: candidate[key] for key in ("dataset_family", *PROVENANCE_FIELDS)},
        inventory_directory=inventory_directory,
        expected_manifest=candidate.get("inventory"),
    )
    if canonical_json(candidate) != canonical_json(rebuilt):
        raise ContractError("observation candidate source correspondence mismatch")
    return observations


def validate_observation_candidate(
    candidate: dict,
    *,
    source_documents: list[bytes],
    expected_candidate_ref: str,
    inventory_directory: Path | None = None,
) -> None:
    """Rebuild from supplied bytes and compare all facts, counts, provenance and IDs.

    The external expected reference fixes the recipe/artifact under comparison;
    neither it nor successful validation proves authorization or source truth.
    """
    _verified_projection(
        candidate,
        source_documents=source_documents,
        expected_candidate_ref=expected_candidate_ref,
        inventory_directory=inventory_directory,
    )


def project_candidate_observations(
    candidate: dict,
    *,
    source_documents: list[bytes],
    expected_candidate_ref: str,
    inventory_directory: Path | None = None,
) -> list[dict]:
    """Return an independent, complete observation projection after full validation."""
    return _verified_projection(
        candidate,
        source_documents=source_documents,
        expected_candidate_ref=expected_candidate_ref,
        inventory_directory=inventory_directory,
    )
