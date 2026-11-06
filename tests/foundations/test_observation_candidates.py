"""Synthetic metadata only; no private inputs, source access or benchmark execution."""

import copy
import hashlib
import json
import os
import subprocess
import sys

import pytest

from rent_contracts import ContractError, load_document, validate_document
from rent_contracts.evaluation import (
    development_split_digest,
    evaluation_policy_digest,
    observation_eligibility_exclusions,
    observation_inventory_digest,
    validate_development_split,
)
from rent_contracts.validation import MAX_DOCUMENT_BYTES, canonical_json
from rent_data.candidates import (
    build_observation_candidate,
    observation_candidate_digest,
    observation_quality_report_digest,
    project_candidate_observations,
    validate_observation_candidate,
)


def ref(label):
    return "sha256:" + hashlib.sha256(f"synthetic candidate fixture: {label}".encode()).hexdigest()


DOMAIN = ref("domain")
MATCHING = ref("matching")


def observation(key, listing, property_id, instant, *, status="confirmed", domain="valid"):
    return {
        "contract_version": "1.0.0",
        "observation_id": key,
        "listing_id": listing,
        "property_identity": {
            "status": status,
            "property_id": property_id,
            "confidence": None,
            "policy_ref": MATCHING,
        },
        "domain_policy_ref": DOMAIN,
        "domain_status": domain,
        "published_at": instant,
        "collected_at": instant,
        "features_available_at": instant,
        "prediction_cutoff_at": instant,
        "temporal_evidence_ref": ref("time evidence") if instant else None,
    }


@pytest.fixture
def candidate_case():
    unknown = observation("obs-c0", "ad-c", None, None, status="unresolved")
    inconsistent = observation(
        "obs-d0", "ad-d", "property-d", "2026-01-14T12:00:00Z", domain="invalid"
    )
    inconsistent["features_available_at"] = "2026-01-13T12:00:00Z"
    pending = observation(
        "obs-e0", "ad-e", "property-e", "2026-01-15T12:00:00Z", domain="unresolved"
    )
    pending["temporal_evidence_ref"] = None
    groups = [
        [
            observation("obs-a0", "ad-a", "property-a", "2026-01-10T12:00:00Z"),
            observation("obs-a1", "ad-a", "property-a", "2026-01-11T12:00:00Z"),
            observation("obs-b0", "ad-b", "property-b", "2026-01-12T12:00:00Z", status="probable"),
        ],
        [
            unknown,
            inconsistent,
            pending,
            observation("obs-f0", "ad-f", "property-f", "2026-02-10T12:00:00Z"),
        ],
    ]
    sources = [
        {
            "contract_version": "1.0.0",
            "raw_source_ref": ref(f"raw source {index}"),
            "acquisition_provenance_ref": ref("acquisition evidence") if index == 0 else None,
            "acquisition_period": {
                "start": "2026-01-01T00:00:00Z" if index == 0 else None,
                "end": "2026-01-31T23:59:59Z" if index == 0 else None,
            },
            "records": [
                {"source_record_id": f"capture-{row_index}", "observation": row}
                for row_index, row in enumerate(group)
            ],
        }
        for index, group in enumerate(groups)
    ]
    return {
        "sources": sources,
        "recipe": {
            "dataset_family": "synthetic-listings",
            "transformation_ref": ref("transformation"),
            "projection_policy_ref": ref("projection policy"),
            "domain_policy_ref": DOMAIN,
            "property_matching_policy_ref": MATCHING,
        },
    }


def source_bytes(case):
    return [json.dumps(source, ensure_ascii=False).encode("utf-8") for source in case["sources"]]


def build(case):
    return build_observation_candidate(source_bytes(case), **case["recipe"])


def check(candidate, case, *, expected_ref=None):
    validate_observation_candidate(
        candidate,
        source_documents=source_bytes(case),
        expected_candidate_ref=expected_ref or candidate["candidate_digest"],
    )


def reseal(candidate):
    candidate["quality_report"]["report_digest"] = observation_quality_report_digest(
        candidate["quality_report"]
    )
    candidate["candidate_digest"] = observation_candidate_digest(candidate)


def test_candidate_conserves_every_source_record_and_reports_overlapping_issues(candidate_case):
    candidate = build(candidate_case)
    check(candidate, candidate_case)
    assert candidate["release_state"] == "UNPUBLISHED_CANDIDATE"
    assert len(candidate["lineage"]) == len(candidate["observations"]) == 7
    assert sum(source["record_count"] for source in candidate["sources"]) == 7
    assert candidate["observations_digest"] == observation_inventory_digest(
        candidate["observations"]
    )
    report = candidate["quality_report"]
    assert report["observation_count"] == 7
    assert report["listing_count"] == 6
    assert report["observations_with_eligibility_issues"] == 3
    assert report["property_resolution_counts"] == {"confirmed": 5, "probable": 1, "unresolved": 1}
    assert report["eligibility_issue_counts"] == {
        "invalid_non_target_domain": 1,
        "unresolved_non_target_domain": 1,
        "temporal_evidence_missing": 2,
        "temporal_order_invalid": 1,
    }
    assert report["source_counts"] == {
        "total": 2,
        "missing_acquisition_provenance": 1,
        "missing_period_start": 1,
        "missing_period_end": 1,
    }


def test_rebuild_is_byte_deterministic_independent_of_source_input_order(candidate_case):
    original = copy.deepcopy(candidate_case)
    first = build(candidate_case)
    assert canonical_json(first) == canonical_json(build(candidate_case))
    candidate_case["sources"].reverse()
    assert canonical_json(first) == canonical_json(build(candidate_case))
    candidate_case["sources"].reverse()
    assert candidate_case == original
    check(first, candidate_case)
    assert candidate_case == original


def test_wire_reordering_changes_source_identity_but_preserves_observations_and_counts(
    candidate_case,
):
    first = build(candidate_case)
    candidate_case["sources"][0]["records"].reverse()
    second = build(candidate_case)
    assert first["observations"] == second["observations"]
    assert first["observations_digest"] == second["observations_digest"]
    assert first["candidate_digest"] != second["candidate_digest"]
    for field in (
        "observation_count",
        "listing_count",
        "eligibility_issue_counts",
        "source_counts",
    ):
        assert first["quality_report"][field] == second["quality_report"][field]


def test_fresh_interpreters_and_hash_seeds_rebuild_identical_canonical_candidates(candidate_case):
    request = json.dumps(
        {
            "sources": [raw.decode("utf-8") for raw in source_bytes(candidate_case)],
            "recipe": candidate_case["recipe"],
        }
    )
    code = """
import json, sys
sys.path[:] = json.loads(sys.argv[1])
from rent_contracts.validation import canonical_json
from rent_data.candidates import build_observation_candidate
request = json.load(sys.stdin)
candidate = build_observation_candidate(
    [text.encode('utf-8') for text in request['sources']], **request['recipe']
)
print(canonical_json(candidate))
"""
    expected = canonical_json(build(candidate_case)) + "\n"
    for seed in ("1", "97"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        # Preserve source/wheel paths without running editable-install .pth files;
        # schema resources are loaded anew in each child.
        completed = subprocess.run(
            [sys.executable, "-S", "-P", "-c", code, json.dumps(sys.path)],
            input=request,
            text=True,
            capture_output=True,
            env=environment,
            check=True,
        )
        assert completed.stdout == expected


def test_exact_source_bytes_and_source_record_lineage_are_bound(candidate_case):
    candidate = build(candidate_case)
    raw_documents = source_bytes(candidate_case)
    by_ref = {"sha256:" + hashlib.sha256(raw).hexdigest(): raw for raw in raw_documents}
    for summary in candidate["sources"]:
        raw = by_ref[summary["source_ref"]]
        assert summary["size_bytes"] == len(raw)
        source = load_document(raw)
        assert summary["record_count"] == len(source["records"])
        for record in source["records"]:
            assert {
                "source_ref": summary["source_ref"],
                "source_record_id": record["source_record_id"],
                "observation_id": record["observation"]["observation_id"],
            } in candidate["lineage"]
    # capture-0 is intentionally reused in the separate source namespaces.
    assert sum(row["source_record_id"] == "capture-0" for row in candidate["lineage"]) == 2


def test_projection_preserves_unknowns_and_returns_independent_mutable_documents(candidate_case):
    candidate = build(candidate_case)
    before = copy.deepcopy(candidate)
    projected = project_candidate_observations(
        candidate,
        source_documents=source_bytes(candidate_case),
        expected_candidate_ref=candidate["candidate_digest"],
    )
    unknown = next(row for row in projected if row["observation_id"] == "obs-c0")
    assert unknown["collected_at"] is None
    assert unknown["published_at"] is None
    assert unknown["features_available_at"] is None
    assert unknown["prediction_cutoff_at"] is None
    assert unknown["temporal_evidence_ref"] is None
    assert unknown["property_identity"]["property_id"] is None
    assert unknown["property_identity"]["confidence"] is None
    projected.clear()
    assert candidate == before
    candidate["observations"][0]["listing_id"] = "caller-mutation"
    assert build(candidate_case) == before
    with pytest.raises(ContractError):
        project_candidate_observations(
            candidate,
            source_documents=source_bytes(candidate_case),
            expected_candidate_ref=before["candidate_digest"],
        )


def test_aggregate_report_contains_no_record_identity_or_caller_text(candidate_case):
    candidate = build(candidate_case)
    encoded = canonical_json(candidate["quality_report"])
    for record in candidate["observations"]:
        assert record["observation_id"] not in encoded
        assert record["listing_id"] not in encoded
        if record["property_identity"]["property_id"] is not None:
            assert record["property_identity"]["property_id"] not in encoded
    validate_document("observation-quality-report", candidate["quality_report"])


@pytest.mark.parametrize("raw", [b"{}", b"\xff", b"\xef\xbb\xbf{}", b"{}\x00", b'{"x":1,"x":2}'])
def test_wire_failures_are_rejected_before_projection(candidate_case, raw):
    with pytest.raises(ContractError):
        build_observation_candidate([raw], **candidate_case["recipe"])


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_source_bytes_require_explicit_utf8(candidate_case, encoding):
    raw = json.dumps(candidate_case["sources"][0]).encode(encoding)
    with pytest.raises(ContractError):
        build_observation_candidate([raw], **candidate_case["recipe"])


@pytest.mark.parametrize("documents", [None, [], {}, ["{}"], [bytearray(b"{}")], [True]])
def test_source_input_is_nonempty_bounded_and_not_implicitly_coerced(candidate_case, documents):
    with pytest.raises(ContractError):
        build_observation_candidate(documents, **candidate_case["recipe"])


def test_combined_source_and_candidate_limits_fail_without_partial_results(candidate_case):
    raw = source_bytes(candidate_case)[0]
    with pytest.raises(ContractError, match="size limit"):
        build_observation_candidate(
            [raw * (MAX_DOCUMENT_BYTES // len(raw) + 1)], **candidate_case["recipe"]
        )
    # Every source is individually small, but the complete supplied inventory is bounded.
    with pytest.raises(ContractError, match="size limit"):
        build_observation_candidate(
            [raw] * (MAX_DOCUMENT_BYTES // len(raw) + 1), **candidate_case["recipe"]
        )


def test_expanded_candidate_cannot_silently_exceed_the_document_bound(candidate_case):
    source = candidate_case["sources"][0]
    template = copy.deepcopy(source["records"][0])
    source["records"] = []
    # Explicit synthetic labels exercise the wire bound; no production ID allocation.
    for index in range(1400):
        record = copy.deepcopy(template)
        record["source_record_id"] = f"capture-{index}"
        record["observation"]["observation_id"] = f"obs-{index}"
        record["observation"]["listing_id"] = f"ad-{index}"
        source["records"].append(record)
    raw = json.dumps(source).encode()
    assert len(raw) < MAX_DOCUMENT_BYTES
    with pytest.raises(ContractError, match="document size limit"):
        build_observation_candidate([raw], **candidate_case["recipe"])


def test_failure_in_a_later_source_does_not_return_a_partial_candidate(candidate_case):
    with pytest.raises(ContractError):
        build_observation_candidate(
            [source_bytes(candidate_case)[0], b"malformed-private-source"],
            **candidate_case["recipe"],
        )


def test_an_entirely_unresolved_inventory_can_be_reported_without_inventing_facts(candidate_case):
    source = candidate_case["sources"][1]
    source["records"] = [source["records"][0]]
    candidate_case["sources"] = [source]
    candidate = build(candidate_case)
    check(candidate, candidate_case)
    assert candidate["quality_report"]["observation_count"] == 1
    assert candidate["quality_report"]["observations_with_eligibility_issues"] == 1
    assert candidate["quality_report"]["property_resolution_counts"]["unresolved"] == 1
    assert candidate["sources"][0]["acquisition_period"] == {"start": None, "end": None}


@pytest.mark.parametrize(
    "change",
    [
        "source-duplicate",
        "raw-alias",
        "record-duplicate",
        "observation-duplicate",
        "capture-alias",
        "property-conflict",
    ],
)
def test_duplicate_or_conflicting_lineage_is_never_silently_deduplicated(candidate_case, change):
    sources = candidate_case["sources"]
    if change == "source-duplicate":
        sources.append(copy.deepcopy(sources[0]))
    elif change == "raw-alias":
        sources[1]["raw_source_ref"] = sources[0]["raw_source_ref"]
    elif change == "record-duplicate":
        sources[0]["records"][1]["source_record_id"] = "capture-0"
    elif change == "observation-duplicate":
        sources[1]["records"][0]["observation"]["observation_id"] = "obs-a0"
    elif change == "capture-alias":
        sources[0]["records"][1]["observation"]["collected_at"] = "2026-01-10T14:00:00+02:00"
    else:
        sources[0]["records"][1]["observation"]["property_identity"]["property_id"] = (
            "other-property"
        )
    with pytest.raises(ContractError):
        build(candidate_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", "2.0.0"),
        ("raw_source_ref", "mutable-branch"),
        ("records", []),
        ("acquisition_provenance_ref", "copied date"),
        ("contact", "private-contact-value"),
        ("targets", [700]),
        ("final_holdout", ["private-id"]),
        ("approval", "self-approved"),
    ],
)
def test_source_envelopes_have_a_closed_nonprivileged_metadata_boundary(
    candidate_case, field, value
):
    candidate_case["sources"][0][field] = value
    with pytest.raises(ContractError) as failure:
        build(candidate_case)
    assert "private-contact-value" not in str(failure.value)
    assert "private-id" not in str(failure.value)


@pytest.mark.parametrize("field", ["price", "target", "address", "knn_ppm", "selector"])
def test_source_observation_cannot_smuggle_targets_or_unapproved_features(candidate_case, field):
    candidate_case["sources"][0]["records"][0]["observation"][field] = "private-payload"
    with pytest.raises(ContractError) as failure:
        build(candidate_case)
    assert "private-payload" not in str(failure.value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30T00:00:00Z",
        "2026-01-01",
        "2026-01-01T00:00:00",
        "2026-01-01T00:00:00-00:00",
        "2026-01-01T23:59:60Z",
    ],
)
def test_acquisition_periods_use_real_calendar_instants_without_guesses(candidate_case, value):
    candidate_case["sources"][0]["acquisition_period"]["start"] = value
    with pytest.raises(ContractError):
        build(candidate_case)


@pytest.mark.parametrize("change", ["reversed", "collection-before", "collection-after"])
def test_source_period_must_agree_with_known_collection_times(candidate_case, change):
    period = candidate_case["sources"][0]["acquisition_period"]
    if change == "reversed":
        period.update(start="2026-02-01T00:00:00Z", end="2026-01-01T00:00:00Z")
    elif change == "collection-before":
        period["start"] = "2026-01-11T00:00:00Z"
    else:
        period["end"] = "2026-01-11T00:00:00Z"
    with pytest.raises(ContractError):
        build(candidate_case)


def test_source_period_is_inclusive_and_offsets_compare_by_time(candidate_case):
    period = candidate_case["sources"][0]["acquisition_period"]
    period.update(start="2026-01-10T14:00:00+02:00", end="2026-01-12T14:00:00+02:00")
    check(build(candidate_case), candidate_case)


@pytest.mark.parametrize("field", ["start", "end"])
def test_partly_unknown_acquisition_period_is_preserved_and_counted(candidate_case, field):
    candidate_case["sources"][0]["acquisition_period"][field] = None
    candidate = build(candidate_case)
    check(candidate, candidate_case)
    assert candidate["quality_report"]["source_counts"][f"missing_period_{field}"] == 2
    assert len(candidate["observations"]) == 7


@pytest.mark.parametrize("field", ["domain_policy_ref", "property_matching_policy_ref"])
def test_candidate_cannot_mix_domain_or_matching_policy_versions(candidate_case, field):
    candidate_case["recipe"][field] = ref("other-policy")
    with pytest.raises(ContractError, match="policy identity mismatch"):
        build(candidate_case)


@pytest.mark.parametrize("field", ["domain_policy_ref", "matching_policy_ref"])
def test_one_source_record_cannot_use_a_different_policy(candidate_case, field):
    record = candidate_case["sources"][1]["records"][0]["observation"]
    if field == "domain_policy_ref":
        record[field] = ref("different domain")
    else:
        record["property_identity"]["policy_ref"] = ref("different matching")
    with pytest.raises(ContractError, match="policy identity mismatch"):
        build(candidate_case)


@pytest.mark.parametrize("identifier", [None, 1, "", "row/1", "capture-0\n"])
def test_source_record_identity_is_explicit_and_unambiguous(candidate_case, identifier):
    candidate_case["sources"][0]["records"][0]["source_record_id"] = identifier
    with pytest.raises(ContractError):
        build(candidate_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("dataset_family", "unsafe/family"),
        ("transformation_ref", "main"),
        ("projection_policy_ref", "/private/path"),
    ],
)
def test_recipe_requires_explicit_immutable_references(candidate_case, field, value):
    candidate_case["recipe"][field] = value
    with pytest.raises(ContractError):
        build(candidate_case)


@pytest.mark.parametrize(
    "change",
    [
        "omit-observation",
        "duplicate-observation",
        "replace-observation",
        "omit-lineage",
        "false-lineage",
        "false-size",
        "false-source-count",
        "false-issue-count",
        "false-property-count",
        "false-union-count",
        "false-digest",
        "source-summary-substitution",
        "reordered-projection",
        "reordered-lineage",
    ],
)
def test_resealing_cannot_hide_forged_projection_provenance_or_report(candidate_case, change):
    candidate = build(candidate_case)
    if change == "omit-observation":
        candidate["observations"].pop()
    elif change == "duplicate-observation":
        candidate["observations"].append(copy.deepcopy(candidate["observations"][0]))
    elif change == "replace-observation":
        candidate["observations"][0]["listing_id"] = "substituted-listing"
    elif change == "omit-lineage":
        candidate["lineage"].pop()
    elif change == "false-lineage":
        candidate["lineage"][0]["source_record_id"] = "false-capture"
    elif change == "false-size":
        candidate["sources"][0]["size_bytes"] += 1
    elif change == "false-source-count":
        candidate["sources"][0]["record_count"] += 1
    elif change == "false-issue-count":
        candidate["quality_report"]["eligibility_issue_counts"]["temporal_evidence_missing"] = 0
    elif change == "false-property-count":
        candidate["quality_report"]["property_resolution_counts"]["unresolved"] = 0
    elif change == "false-union-count":
        candidate["quality_report"]["observations_with_eligibility_issues"] = 5
    elif change == "false-digest":
        candidate["observations_digest"] = ref("substituted inventory")
    elif change == "source-summary-substitution":
        candidate["sources"][0]["raw_source_ref"] = ref("substituted raw")
    elif change == "reordered-projection":
        candidate["observations"].reverse()
    else:
        candidate["lineage"].reverse()
    reseal(candidate)
    with pytest.raises(ContractError, match="source correspondence"):
        check(candidate, candidate_case)


def test_fixed_expected_candidate_ref_prevents_recipe_substitution(candidate_case):
    candidate = build(candidate_case)
    fixed_ref = candidate["candidate_digest"]
    candidate_case["recipe"]["transformation_ref"] = ref("different transformation")
    alternate = build(candidate_case)
    with pytest.raises(ContractError, match="expected observation candidate identity"):
        check(alternate, candidate_case, expected_ref=fixed_ref)


@pytest.mark.parametrize("change", ["whitespace", "metadata", "omitted-source"])
def test_validation_binds_exact_supplied_source_bytes(candidate_case, change):
    candidate = build(candidate_case)
    raw = source_bytes(candidate_case)
    if change == "whitespace":
        raw[0] += b"\n"
    elif change == "metadata":
        candidate_case["sources"][1]["acquisition_provenance_ref"] = ref("new provenance")
        raw = source_bytes(candidate_case)
    else:
        raw.pop()
    with pytest.raises(ContractError, match="source correspondence"):
        validate_observation_candidate(
            candidate, source_documents=raw, expected_candidate_ref=candidate["candidate_digest"]
        )


def test_self_digest_covers_nested_report_and_excludes_only_itself(candidate_case):
    candidate = build(candidate_case)
    original = candidate["candidate_digest"]
    candidate["candidate_digest"] = ref("ignored self")
    assert observation_candidate_digest(candidate) == original
    candidate["candidate_digest"] = original
    candidate["quality_report"]["listing_count"] += 1
    with pytest.raises(ContractError, match="candidate digest"):
        check(candidate, candidate_case)
    candidate["candidate_digest"] = observation_candidate_digest(candidate)
    with pytest.raises(ContractError, match="quality report digest"):
        check(candidate, candidate_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", "2.0.0"),
        ("release_state", "PUBLISHED"),
        ("access_domain", "protected"),
        ("final_holdout_ids", ["secret-id"]),
        ("approval", "self-approved"),
    ],
)
def test_candidate_does_not_grant_publication_approval_or_protected_access(
    candidate_case, field, value
):
    candidate = build(candidate_case)
    candidate[field] = value
    reseal(candidate)
    with pytest.raises(ContractError) as failure:
        check(candidate, candidate_case)
    assert "secret-id" not in str(failure.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", "2.0.0"),
        ("assessment_version", "2.0.0"),
        ("observation_count", True),
        ("observation_count", -1),
        ("rows", ["private-row"]),
        ("targets", [700]),
    ],
)
def test_report_schema_stays_versioned_aggregate_and_numeric(candidate_case, field, value):
    candidate = build(candidate_case)
    candidate["quality_report"][field] = value
    reseal(candidate)
    with pytest.raises(ContractError) as failure:
        check(candidate, candidate_case)
    assert "private-row" not in str(failure.value)


def test_shared_quality_reasons_match_existing_development_split_semantics(candidate_case):
    candidate = build(candidate_case)
    expected_issues = {
        "obs-c0": ["temporal_evidence_missing"],
        "obs-d0": ["invalid_non_target_domain", "temporal_order_invalid"],
        "obs-e0": ["unresolved_non_target_domain", "temporal_evidence_missing"],
    }
    for record in candidate["observations"]:
        reasons = observation_eligibility_exclusions(record)
        assert isinstance(reasons, frozenset)
        assert reasons == frozenset(expected_issues.get(record["observation_id"], []))
    policy = {
        "contract_version": "1.0.0",
        "policy_version": "synthetic-review-v1",
        "domain_policy_ref": DOMAIN,
        "property_matching_policy_ref": MATCHING,
        "selection_basis": "non_target_metadata_only",
        "property_matching_basis": "non_target_signals_only",
        "eligibility_rule": "non_target_domain_and_observation_time_v1",
        "unseen_property_rule": "confirmed_absence_from_resolved_training_v1",
        "target_unit": "EUR/month",
    }
    policy["policy_digest"] = evaluation_policy_digest(policy)
    members = []
    for key in ("obs-a0", "obs-a1", "obs-b0", "obs-c0", "obs-d0", "obs-e0", "obs-f0"):
        excluded = key in expected_issues
        members.append(
            {
                "observation_id": key,
                "partition": "excluded"
                if excluded
                else "development_validation"
                if key == "obs-f0"
                else "training",
                "eligibility_exclusions": expected_issues.get(key, []),
                "cohorts": ["future_market"] if key == "obs-f0" else [],
                "unseen_property_exclusions": ["training_identity_unresolved"]
                if key == "obs-f0"
                else ["not_development_validation"],
            }
        )
    manifest = {
        "contract_version": "1.0.0",
        "access_domain": "development",
        "dataset_ref": ref("authorized fixture release"),
        "policy_ref": policy["policy_digest"],
        "observations_digest": candidate["observations_digest"],
        "training_cutoff": "2026-02-01T00:00:00Z",
        "validation_window": {
            "start_inclusive": "2026-02-01T00:00:00Z",
            "end_exclusive": "2026-03-01T00:00:00Z",
        },
        "memberships": members,
        "creation_provenance": {
            "source_snapshot_ref": ref("split code"),
            "created_at": "2026-03-02T00:00:00Z",
        },
    }
    manifest["split_digest"] = development_split_digest(manifest)
    validate_development_split(
        manifest,
        policy=policy,
        observations=candidate["observations"],
        expected_dataset_ref=manifest["dataset_ref"],
    )


def test_public_shared_reason_helper_rejects_invalid_metadata_without_echoing_it(candidate_case):
    record = candidate_case["sources"][0]["records"][0]["observation"]
    record["domain_status"] = "private-status-value"
    with pytest.raises(ContractError) as failure:
        observation_eligibility_exclusions(record)
    assert "private-status-value" not in str(failure.value)
