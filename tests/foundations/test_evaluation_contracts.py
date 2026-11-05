"""Invented metadata only: no historical timestamps, matching scores or benchmark results."""

import copy
import hashlib

import pytest

from rent_contracts import ContractError, validate_document
from rent_contracts.evaluation import (
    development_split_digest,
    evaluation_policy_digest,
    observation_inventory_digest,
    validate_development_population,
    validate_development_split,
    validate_evaluation_policy,
    validate_observation_reference,
)


def synthetic_ref(label):
    return "sha256:" + hashlib.sha256(f"invented fixture: {label}".encode()).hexdigest()


DATASET = synthetic_ref("dataset envelope")
DOMAIN = synthetic_ref("non-target domain policy")
MATCHING = synthetic_ref("property matching policy")
EVIDENCE = synthetic_ref("temporal evidence")


def observation(key, listing, property_id, instant, *, status="confirmed", domain="valid"):
    return {
        "contract_version": "1.0.0",
        "observation_id": key,
        "listing_id": listing,
        "property_identity": {
            "policy_ref": MATCHING,
            "status": status,
            "property_id": property_id,
            "confidence": None,
        },
        "domain_policy_ref": DOMAIN,
        "domain_status": domain,
        "published_at": instant,
        "collected_at": instant,
        "features_available_at": instant,
        "prediction_cutoff_at": instant,
        "temporal_evidence_ref": EVIDENCE,
    }


def membership(
    key, partition, *, exclusions=(), cohorts=(), unseen=("not_development_validation",)
):
    # Expected assignments are explicit fixture decisions, never produced by the validator.
    return {
        "observation_id": key,
        "partition": partition,
        "eligibility_exclusions": list(exclusions),
        "cohorts": list(cohorts),
        "unseen_property_exclusions": list(unseen),
    }


def seal(manifest):
    manifest["split_digest"] = development_split_digest(manifest)


def check(case):
    policy, observations, manifest = case
    validate_development_split(
        manifest, policy=policy, observations=observations, expected_dataset_ref=DATASET
    )


@pytest.fixture
def evaluation_case():
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
    observations = [
        observation("obs-train", "ad-a", "property-a", "2026-01-10T12:00:00Z"),
        observation("obs-repeat", "ad-b", "property-a", "2026-02-10T12:00:00Z"),
        observation("obs-new", "ad-c", "property-c", "2026-02-11T12:00:00Z"),
        observation("obs-unknown", "ad-d", None, "2026-02-12T12:00:00Z", status="unresolved"),
        observation(
            "obs-probable", "ad-e", "property-e", "2026-02-13T12:00:00Z", status="probable"
        ),
        observation("obs-refresh", "ad-a", "property-a", "2026-02-14T12:00:00Z"),
        observation("obs-no-time", "ad-f", "property-f", None),
    ]
    observations[-1]["temporal_evidence_ref"] = None
    manifest = {
        "contract_version": "1.0.0",
        "access_domain": "development",
        "dataset_ref": DATASET,
        "observations_digest": observation_inventory_digest(observations),
        "policy_ref": policy["policy_digest"],
        "training_cutoff": "2026-02-01T00:00:00Z",
        "validation_window": {
            "start_inclusive": "2026-02-01T00:00:00Z",
            "end_exclusive": "2026-03-01T00:00:00Z",
        },
        "memberships": [
            membership("obs-train", "training"),
            membership(
                "obs-repeat",
                "development_validation",
                cohorts=("future_market",),
                unseen=("property_overlap_training",),
            ),
            membership(
                "obs-new",
                "development_validation",
                cohorts=("future_market", "unseen_property"),
                unseen=(),
            ),
            membership(
                "obs-unknown",
                "development_validation",
                cohorts=("future_market",),
                unseen=("property_identity_unconfirmed",),
            ),
            membership(
                "obs-probable",
                "development_validation",
                cohorts=("future_market",),
                unseen=("property_identity_unconfirmed",),
            ),
            membership(
                "obs-refresh",
                "development_validation",
                cohorts=("future_market",),
                unseen=("listing_seen_in_training", "property_overlap_training"),
            ),
            membership("obs-no-time", "excluded", exclusions=("temporal_evidence_missing",)),
        ],
        "creation_provenance": {
            "source_snapshot_ref": synthetic_ref("source snapshot"),
            "created_at": "2026-03-02T00:00:00Z",
        },
    }
    seal(manifest)
    return policy, observations, manifest


def rebind_observations(case):
    _, observations, manifest = case
    manifest["observations_digest"] = observation_inventory_digest(observations)
    seal(manifest)


def test_development_views_overlap_and_preserve_represented_properties(evaluation_case):
    check(evaluation_case)
    _, _, manifest = evaluation_case
    primary = ["obs-repeat", "obs-new", "obs-unknown", "obs-probable", "obs-refresh"]
    for candidate_order in (primary, list(reversed(primary))):
        validate_development_population(
            manifest,
            candidate_order,
            cohort="future_market",
            expected_split_ref=manifest["split_digest"],
        )
    validate_development_population(
        manifest,
        ["obs-new"],
        cohort="unseen_property",
        expected_split_ref=manifest["split_digest"],
    )
    assert "obs-new" in primary  # These views are explicitly not independent samples.


def test_inventory_identity_is_independent_of_input_row_order(evaluation_case):
    _, observations, _ = evaluation_case
    assert observation_inventory_digest(observations) == observation_inventory_digest(
        list(reversed(observations))
    )
    evaluation_case[1].reverse()
    check(evaluation_case)


def test_validation_does_not_mutate_caller_metadata_or_assignments(evaluation_case):
    original = copy.deepcopy(evaluation_case)
    check(evaluation_case)
    assert evaluation_case == original


@pytest.mark.parametrize("index", [0, 2])
def test_policy_and_split_reject_unknown_contract_versions(evaluation_case, index):
    document = evaluation_case[index]
    document["contract_version"] = "2.0.0"
    if index == 0:
        document["policy_digest"] = evaluation_policy_digest(document)
    else:
        seal(document)
    with pytest.raises(ContractError):
        check(evaluation_case)


@pytest.mark.parametrize("field", ["training_cutoff", "validation-start", "created-at"])
def test_manifest_calendar_instants_do_not_depend_on_optional_format_support(
    evaluation_case, field
):
    manifest = evaluation_case[2]
    impossible = "2026-02-30T00:00:00Z"
    if field == "validation-start":
        manifest["validation_window"]["start_inclusive"] = impossible
    elif field == "created-at":
        manifest["creation_provenance"]["created_at"] = impossible
    else:
        manifest[field] = impossible
    seal(manifest)
    with pytest.raises(ContractError):
        check(evaluation_case)


@pytest.mark.parametrize("change", ["duplicate-id", "aliased-capture", "conflicting-property"])
def test_observation_identity_collisions_fail(evaluation_case, change):
    _, observations, _ = evaluation_case
    extra = copy.deepcopy(observations[0])
    if change != "duplicate-id":
        extra["observation_id"] = "different-observation"
    if change == "aliased-capture":
        # Equivalent offset spelling cannot disguise the same listing collection instant.
        extra["collected_at"] = "2026-01-10T14:00:00+02:00"
    if change == "conflicting-property":
        extra["collected_at"] = "2026-01-11T12:00:00Z"
        extra["property_identity"]["property_id"] = "conflicting-property"
    with pytest.raises(ContractError):
        observation_inventory_digest([*observations, extra])


@pytest.mark.parametrize("observations", [[], {}, None, [None]])
def test_missing_or_invalid_inventory_is_not_a_dataset(observations):
    with pytest.raises(ContractError):
        observation_inventory_digest(observations)


@pytest.mark.parametrize("field", ["published_at", "collected_at", "features_available_at"])
def test_metadata_changes_are_bound_even_when_record_ids_stay_the_same(evaluation_case, field):
    evaluation_case[1][2][field] = "2026-02-11T11:59:00Z"
    with pytest.raises(ContractError, match="inventory digest"):
        check(evaluation_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("contract_version", "2.0.0"),
        ("observation_id", 3),
        ("observation_id", "row/3"),
        ("listing_id", "ad\n"),
        ("domain_status", "assumed_valid"),
        ("domain_policy_ref", "main"),
        ("published_at", "2026-02-11"),
        ("collected_at", "2026-02-11T12:00:00"),
        ("collected_at", "2026-02-11T12:00:00-00:00"),
        ("features_available_at", "2026-02-30T00:00:00Z"),
        ("features_available_at", "2026-02-11T23:59:60Z"),
        ("prediction_cutoff_at", "2026-02-11T12:00:00.0000001Z"),
        ("temporal_evidence_ref", "copied file date"),
        ("price", 900),
        ("target", 900),
        ("knn_ppm", 12),
        ("first_seen", "2026-02-11"),
        ("row_index", 3),
    ],
)
def test_observation_contract_rejects_labels_guesses_and_bad_references(
    evaluation_case, field, value
):
    record = evaluation_case[1][2]
    record[field] = value
    with pytest.raises(ContractError):
        validate_observation_reference(record)


def test_known_times_and_missing_time_are_not_interchangeable(evaluation_case):
    record = evaluation_case[1][2]
    del record["collected_at"]
    with pytest.raises(ContractError):
        observation_inventory_digest(evaluation_case[1])
    record["collected_at"] = None
    rebind_observations(evaluation_case)
    with pytest.raises(ContractError, match="eligibility"):
        check(evaluation_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("property_id", None),
        ("property_id", 1),
        ("status", "unseen"),
        ("confidence", -0.01),
        ("confidence", 1.01),
        ("confidence", True),
        ("confidence", float("nan")),
        ("target_similarity", 1),
    ],
)
def test_property_reference_is_not_a_listing_or_target_matching_shortcut(
    evaluation_case, field, value
):
    record = evaluation_case[1][2]
    record["property_identity"][field] = value
    with pytest.raises(ContractError):
        validate_document("observation-reference", record)


@pytest.mark.parametrize("field,value", [("property_id", "pretend-property"), ("confidence", 0.5)])
def test_unresolved_identity_does_not_invent_a_group_or_confidence(evaluation_case, field, value):
    record = evaluation_case[1][3]
    record["property_identity"][field] = value
    with pytest.raises(ContractError):
        validate_document("observation-reference", record)


@pytest.mark.parametrize(
    "field,value",
    [
        ("selection_basis", "rent_quantiles"),
        ("property_matching_basis", "asking_price"),
        ("eligibility_rule", "training_fitted_price_filter"),
        ("unseen_property_rule", "absence_means_unseen"),
        ("rent_cap", 2000),
        ("price_per_area_bounds", [1, 100]),
        ("local_rent_ratio", [0.5, 2]),
        ("selector", "arbitrary Python"),
        ("target_unit", "MDL/month"),
    ],
)
def test_policy_cannot_select_evaluation_by_targets_or_arbitrary_code(
    evaluation_case, field, value
):
    policy = evaluation_case[0]
    policy[field] = value
    policy["policy_digest"] = evaluation_policy_digest(policy)
    with pytest.raises(ContractError):
        validate_evaluation_policy(policy)


def test_policy_identity_binds_even_a_version_change(evaluation_case):
    policy = evaluation_case[0]
    original = policy["policy_digest"]
    policy["policy_digest"] = synthetic_ref("ignored self-reference")
    assert evaluation_policy_digest(policy) == original
    policy["policy_digest"] = original
    policy["policy_version"] = "different-version"
    with pytest.raises(ContractError, match="policy digest"):
        validate_evaluation_policy(policy)
    policy["policy_digest"] = evaluation_policy_digest(policy)
    with pytest.raises(ContractError, match="policy identity"):
        check(evaluation_case)


@pytest.mark.parametrize("reference", ["domain_policy_ref", "matching_policy_ref", "dataset_ref"])
def test_external_references_must_match_the_expected_release_and_policy(evaluation_case, reference):
    _, observations, manifest = evaluation_case
    if reference == "domain_policy_ref":
        observations[2][reference] = synthetic_ref("different policy")
    elif reference == "matching_policy_ref":
        observations[2]["property_identity"]["policy_ref"] = synthetic_ref("different matching")
    else:
        manifest[reference] = synthetic_ref("other release")
    rebind_observations(evaluation_case)
    with pytest.raises(ContractError, match="identity mismatch"):
        check(evaluation_case)


@pytest.mark.parametrize("change", ["omission", "duplicate", "substitution", "overlap"])
def test_every_supplied_observation_has_exactly_one_partition_assignment(evaluation_case, change):
    rows = evaluation_case[2]["memberships"]
    if change == "omission":
        rows.pop()
    elif change == "substitution":
        rows[-1]["observation_id"] = "not-in-release"
    else:
        extra = copy.deepcopy(rows[0])
        if change == "overlap":
            extra["partition"] = "development_validation"
            extra["cohorts"] = ["future_market"]
        rows.append(extra)
    seal(evaluation_case[2])
    with pytest.raises(ContractError, match="population"):
        check(evaluation_case)


@pytest.mark.parametrize(
    "change", ["cutoff-after-start", "empty-window", "reversed-window", "missing-offset"]
)
def test_invalid_temporal_boundaries_fail_even_with_a_new_digest(evaluation_case, change):
    manifest = evaluation_case[2]
    if change == "cutoff-after-start":
        manifest["training_cutoff"] = "2026-02-02T00:00:00Z"
    elif change == "empty-window":
        manifest["validation_window"]["end_exclusive"] = "2026-02-01T00:00:00Z"
    elif change == "reversed-window":
        manifest["validation_window"]["end_exclusive"] = "2026-01-31T00:00:00Z"
    else:
        manifest["training_cutoff"] = "2026-02-01T00:00:00"
    seal(manifest)
    with pytest.raises(ContractError):
        check(evaluation_case)


@pytest.mark.parametrize(
    "instant",
    ["2026-02-01T00:00:00Z", "2026-02-01T02:00:00+02:00", "2026-02-28T23:59:59.999999Z"],
)
def test_validation_start_is_inclusive_and_offsets_compare_as_instants(evaluation_case, instant):
    record = evaluation_case[1][2]
    for field in ("published_at", "collected_at", "features_available_at", "prediction_cutoff_at"):
        record[field] = instant
    rebind_observations(evaluation_case)
    check(evaluation_case)


@pytest.mark.parametrize("instant", ["2026-03-01T00:00:00Z", "2026-01-25T00:00:00Z"])
def test_window_end_and_declared_gap_are_explicit_exclusions(evaluation_case, instant):
    _, observations, manifest = evaluation_case
    manifest["training_cutoff"] = "2026-01-20T00:00:00Z"
    for field in ("published_at", "collected_at", "features_available_at", "prediction_cutoff_at"):
        observations[2][field] = instant
    manifest["memberships"][2] = membership(
        "obs-new", "excluded", exclusions=("outside_development_windows",)
    )
    rebind_observations(evaluation_case)
    check(evaluation_case)


@pytest.mark.parametrize(
    "index,instant", [(0, "2026-02-01T00:00:00Z"), (2, "2026-01-31T23:59:59Z")]
)
def test_training_validation_boundary_cannot_be_crossed_silently(evaluation_case, index, instant):
    evaluation_case[1][index]["prediction_cutoff_at"] = instant
    rebind_observations(evaluation_case)
    with pytest.raises(ContractError, match="eligibility"):
        check(evaluation_case)


@pytest.mark.parametrize(
    "change,reasons",
    [
        ("invalid-domain", ("invalid_non_target_domain",)),
        ("unresolved-domain", ("unresolved_non_target_domain",)),
        ("missing-evidence", ("temporal_evidence_missing",)),
        ("late-features", ("temporal_order_invalid",)),
        ("late-collection", ("temporal_order_invalid",)),
        ("late-publication", ("temporal_order_invalid",)),
    ],
)
def test_unusable_metadata_requires_the_exact_explicit_exclusions(evaluation_case, change, reasons):
    _, observations, manifest = evaluation_case
    record = observations[2]
    if change.endswith("domain"):
        record["domain_status"] = change.split("-")[0]
    elif change == "missing-evidence":
        record["temporal_evidence_ref"] = None
    else:
        field = {
            "late-features": "features_available_at",
            "late-collection": "collected_at",
            "late-publication": "published_at",
        }[change]
        record[field] = "2026-02-12T00:00:00Z"
    rebind_observations(evaluation_case)
    with pytest.raises(ContractError, match="eligibility"):
        check(evaluation_case)
    manifest["memberships"][2] = membership("obs-new", "excluded", exclusions=reasons)
    seal(manifest)
    check(evaluation_case)


def test_exclusions_accumulate_without_dropping_a_source_record(evaluation_case):
    record = evaluation_case[1][2]
    record["domain_status"] = "invalid"
    record["features_available_at"] = None
    record["prediction_cutoff_at"] = "2026-03-01T00:00:00Z"
    evaluation_case[2]["memberships"][2] = membership(
        "obs-new",
        "excluded",
        exclusions=(
            "invalid_non_target_domain",
            "temporal_evidence_missing",
            "outside_development_windows",
        ),
    )
    rebind_observations(evaluation_case)
    check(evaluation_case)


@pytest.mark.parametrize("index", [1, 3, 4, 5])
def test_represented_and_ambiguous_properties_never_automatically_become_unseen(
    evaluation_case, index
):
    row = evaluation_case[2]["memberships"][index]
    row["cohorts"] = ["future_market", "unseen_property"]
    row["unseen_property_exclusions"] = []
    seal(evaluation_case[2])
    with pytest.raises(ContractError, match="cohort"):
        check(evaluation_case)


@pytest.mark.parametrize("training_status", ["unresolved", "probable"])
def test_uncertain_training_identities_prevent_absence_from_becoming_unseen(
    evaluation_case, training_status
):
    _, observations, manifest = evaluation_case
    train = observations[0]
    train["property_identity"]["status"] = training_status
    if training_status == "unresolved":
        train["property_identity"]["property_id"] = None
    observations[:] = [train, observations[2]]
    manifest["memberships"] = [
        membership("obs-train", "training"),
        membership(
            "obs-new",
            "development_validation",
            cohorts=("future_market",),
            unseen=("training_identity_unresolved",),
        ),
    ]
    rebind_observations(evaluation_case)
    check(evaluation_case)
    with pytest.raises(ContractError, match="population"):
        validate_development_population(
            manifest, [], cohort="unseen_property", expected_split_ref=manifest["split_digest"]
        )
    manifest["memberships"][1]["cohorts"].append("unseen_property")
    manifest["memberships"][1]["unseen_property_exclusions"] = []
    seal(manifest)
    with pytest.raises(ContractError, match="cohort"):
        check(evaluation_case)


def test_listing_reappearance_remains_known_even_if_property_resolution_is_missing(evaluation_case):
    record = evaluation_case[1][5]
    record["property_identity"].update(status="unresolved", property_id=None)
    evaluation_case[2]["memberships"][5]["unseen_property_exclusions"] = [
        "listing_seen_in_training",
        "property_identity_unconfirmed",
    ]
    rebind_observations(evaluation_case)
    check(evaluation_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("eligibility_exclusions", ["price_out_of_range"]),
        ("eligibility_exclusions", ["invalid_non_target_domain"]),
        ("cohorts", ["future_market", "future_market"]),
        ("cohorts", ["final_holdout"]),
        ("cohorts", []),
        ("unseen_property_exclusions", ["property_identity_unconfirmed"]),
    ],
)
def test_candidates_cannot_change_reasons_or_cohorts(evaluation_case, field, value):
    evaluation_case[2]["memberships"][2][field] = value
    seal(evaluation_case[2])
    with pytest.raises(ContractError):
        check(evaluation_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("access_domain", "protected"),
        ("final_holdout_period", {"start": "restricted"}),
        ("final_holdout_ids", ["restricted"]),
        ("final_holdout_count", 1),
        ("protected_labels", [900]),
        ("approval", "self-approved"),
    ],
)
def test_development_envelope_has_no_final_holdout_or_approval_surface(
    evaluation_case, field, value
):
    evaluation_case[2][field] = value
    seal(evaluation_case[2])
    with pytest.raises(ContractError):
        check(evaluation_case)


@pytest.mark.parametrize("change", ["omit", "duplicate", "extra", "substitute", "invalid-type"])
def test_candidate_failure_cannot_shrink_or_substitute_the_fixed_cohort(evaluation_case, change):
    manifest = evaluation_case[2]
    population = ["obs-repeat", "obs-new", "obs-unknown", "obs-probable", "obs-refresh"]
    if change == "omit":
        population.pop()  # Includes preprocessing/prediction failures; never silently omit.
    elif change == "duplicate":
        population.append(population[0])
    elif change == "extra":
        population.append("obs-train")
    elif change == "substitute":
        population[-1] = "another-observation"
    else:
        population[-1] = {"private-key": "private-value"}
    with pytest.raises(ContractError, match="population") as failure:
        validate_development_population(
            manifest,
            population,
            cohort="future_market",
            expected_split_ref=manifest["split_digest"],
        )
    assert "private-key" not in str(failure.value)
    assert "private-value" not in str(failure.value)


def test_candidate_cannot_reseal_a_different_split_under_a_comparison(evaluation_case):
    manifest = evaluation_case[2]
    fixed_ref = manifest["split_digest"]
    manifest["creation_provenance"]["source_snapshot_ref"] = synthetic_ref("other source")
    with pytest.raises(ContractError, match="split digest"):
        check(evaluation_case)
    seal(manifest)
    check(evaluation_case)
    with pytest.raises(ContractError, match="comparison split identity"):
        validate_development_population(
            manifest, ["obs-new"], cohort="unseen_property", expected_split_ref=fixed_ref
        )


@pytest.mark.parametrize("cohort", ["training", "final_holdout", "unsupported-private-value"])
def test_only_development_comparison_views_are_supported(evaluation_case, cohort):
    manifest = evaluation_case[2]
    with pytest.raises(ContractError, match="unsupported development cohort") as failure:
        validate_development_population(
            manifest, ["obs-new"], cohort=cohort, expected_split_ref=manifest["split_digest"]
        )
    assert "unsupported-private-value" not in str(failure.value)


@pytest.mark.parametrize(
    "field", ["dataset_ref", "policy_ref", "observations_digest", "training_cutoff"]
)
def test_split_self_digest_binds_references_and_cutoffs(evaluation_case, field):
    manifest = evaluation_case[2]
    original = manifest["split_digest"]
    manifest["split_digest"] = synthetic_ref("ignored split self-reference")
    assert development_split_digest(manifest) == original
    manifest["split_digest"] = original
    manifest[field] = (
        "2026-01-30T00:00:00Z" if field == "training_cutoff" else synthetic_ref("changed reference")
    )
    with pytest.raises(ContractError, match="split digest"):
        check(evaluation_case)
