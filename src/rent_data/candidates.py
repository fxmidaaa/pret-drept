"""Deterministic metadata candidates from supplied source envelopes (§§8–9).

No source-file/network access, raw-data projection, matching, split selection or publication.
Raw-source and policy references are declarations, not authorization or verified truth.
"""

import copy
import hashlib
from datetime import datetime

from rent_contracts import ContractError, load_document, validate_document
from rent_contracts.evaluation import (
    observation_eligibility_exclusions,
    observation_inventory_digest,
)
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json


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


def _source_inventory(source_documents: list[bytes]) -> tuple[list[dict], list[dict], list[dict]]:
    if (
        type(source_documents) is not list
        or not source_documents
        or any(type(raw) is not bytes for raw in source_documents)
    ):
        raise ContractError("source documents must be a nonempty list of UTF-8 bytes")
    if sum(len(raw) for raw in source_documents) > MAX_DOCUMENT_BYTES:
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


def build_observation_candidate(
    source_documents: list[bytes],
    *,
    dataset_family: str,
    transformation_ref: str,
    projection_policy_ref: str,
    domain_policy_ref: str,
    property_matching_policy_ref: str,
) -> dict:
    """Build an unpublished metadata artifact without filtering any source records.

    Supplied envelopes must already contain a reviewed metadata projection. Their
    exact bytes are verified on revalidation; underlying raw bytes are not accessed.
    """
    sources, observations, lineage = _source_inventory(source_documents)
    inventory_digest = observation_inventory_digest(observations)
    for observation in observations:
        if observation["domain_policy_ref"] != domain_policy_ref:
            raise ContractError("candidate domain policy identity mismatch")
        if observation["property_identity"]["policy_ref"] != property_matching_policy_ref:
            raise ContractError("candidate matching policy identity mismatch")
    candidate = {
        "contract_version": "1.0.0",
        "dataset_family": dataset_family,
        "access_domain": "development",
        "release_state": "UNPUBLISHED_CANDIDATE",
        "transformation_ref": transformation_ref,
        "projection_policy_ref": projection_policy_ref,
        "domain_policy_ref": domain_policy_ref,
        "property_matching_policy_ref": property_matching_policy_ref,
        "observations_digest": inventory_digest,
        "sources": sources,
        "lineage": lineage,
        "observations": observations,
        "quality_report": _quality_report(sources, observations, inventory_digest),
    }
    candidate["candidate_digest"] = observation_candidate_digest(candidate)
    validate_document("observation-candidate", candidate)
    return candidate


def validate_observation_candidate(
    candidate: dict, *, source_documents: list[bytes], expected_candidate_ref: str
) -> None:
    """Rebuild from supplied bytes and compare all facts, counts, provenance and IDs.

    The external expected reference fixes the recipe/artifact under comparison;
    neither it nor successful validation proves authorization or source truth.
    """
    validate_document("observation-candidate", candidate)
    if observation_candidate_digest(candidate) != candidate["candidate_digest"]:
        raise ContractError("observation candidate digest mismatch")
    if candidate["candidate_digest"] != expected_candidate_ref:
        raise ContractError("expected observation candidate identity mismatch")
    report = candidate["quality_report"]
    if observation_quality_report_digest(report) != report["report_digest"]:
        raise ContractError("observation quality report digest mismatch")
    rebuilt = build_observation_candidate(
        source_documents,
        dataset_family=candidate["dataset_family"],
        transformation_ref=candidate["transformation_ref"],
        projection_policy_ref=candidate["projection_policy_ref"],
        domain_policy_ref=candidate["domain_policy_ref"],
        property_matching_policy_ref=candidate["property_matching_policy_ref"],
    )
    if canonical_json(candidate) != canonical_json(rebuilt):
        raise ContractError("observation candidate source correspondence mismatch")


def project_candidate_observations(
    candidate: dict, *, source_documents: list[bytes], expected_candidate_ref: str
) -> list[dict]:
    """Return an independent, complete observation projection after full validation."""
    validate_observation_candidate(
        candidate, source_documents=source_documents, expected_candidate_ref=expected_candidate_ref
    )
    return copy.deepcopy(candidate["observations"])
