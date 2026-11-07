"""Handwritten metadata oracles and reproducibility, without model/label execution."""

import copy
import json
import os
import subprocess
import sys

import pytest

from rent_contracts import ContractError
from rent_contracts.evaluation import (
    derive_development_memberships,
    development_split_digest,
    evaluation_policy_digest,
    validate_development_population,
    validate_development_split,
)
from rent_contracts.validation import canonical_json
from rent_data.releases import content_digest, dataset_release_digest
from rent_data.splits import build_development_split, validate_release_split


def arguments(case):
    return {
        "release": case["release"],
        "observations": case["candidate"]["observations"],
        "policy": case["policy"],
        "expected_release_ref": case["release"]["release_digest"],
        "expected_policy_ref": case["policy"]["policy_digest"],
        **case["parameters"],
    }


def build(case, **overrides):
    return build_development_split(**(arguments(case) | overrides))


def check(manifest, case, **overrides):
    context = {
        name: value for name, value in arguments(case).items() if name not in case["parameters"]
    }
    validate_release_split(
        manifest, **(context | {"expected_split_ref": manifest["split_digest"]} | overrides)
    )


def membership(
    key, partition, *, exclusions=(), cohorts=(), unseen=("not_development_validation",)
):
    # Oracle assignments are handwritten from the v1 specification, never generated.
    return {
        "observation_id": key,
        "partition": partition,
        "eligibility_exclusions": list(exclusions),
        "cohorts": list(cohorts),
        "unseen_property_exclusions": list(unseen),
    }


def test_builder_matches_complete_handwritten_assignment_and_exclusion_oracle(split_case):
    m = build(split_case)
    check(m, split_case)
    assert m["memberships"] == [
        membership("obs-end", "excluded", exclusions=("outside_development_windows",)),
        membership("obs-gap", "excluded", exclusions=("outside_development_windows",)),
        membership("obs-invalid", "excluded", exclusions=("invalid_non_target_domain",)),
        membership(
            "obs-multi",
            "excluded",
            exclusions=(
                "invalid_non_target_domain",
                "outside_development_windows",
                "temporal_evidence_missing",
                "temporal_order_invalid",
            ),
        ),
        membership(
            "obs-new",
            "development_validation",
            cohorts=("future_market", "unseen_property"),
            unseen=(),
        ),
        membership("obs-notime", "excluded", exclusions=("temporal_evidence_missing",)),
        membership("obs-pending", "excluded", exclusions=("unresolved_non_target_domain",)),
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
        membership(
            "obs-seen",
            "development_validation",
            cohorts=("future_market",),
            unseen=("property_overlap_training",),
        ),
        membership("obs-train-a", "training"),
        membership("obs-train-b", "training"),
        membership(
            "obs-unresolved",
            "development_validation",
            cohorts=("future_market",),
            unseen=("property_identity_unconfirmed",),
        ),
    ]
    assert len(m["memberships"]) == split_case["release"]["observation_count"] == 13
    assert m["dataset_ref"] == split_case["release"]["release_digest"]
    assert m["policy_ref"] == split_case["policy"]["policy_digest"]
    assert m["observations_digest"] == split_case["release"]["observations_digest"]


def test_pure_membership_helper_matches_builder_and_does_not_alias_inputs(split_case):
    before = copy.deepcopy(split_case)
    rows = derive_development_memberships(
        split_case["candidate"]["observations"],
        policy=split_case["policy"],
        training_cutoff=split_case["parameters"]["training_cutoff"],
        validation_window=split_case["parameters"]["validation_window"],
    )
    assert rows == build(split_case)["memberships"]
    rows[0]["eligibility_exclusions"].append("invented")
    artifact = build(split_case)
    artifact["validation_window"]["start_inclusive"] = "changed"
    artifact["creation_provenance"]["created_at"] = "changed"
    assert split_case == before


def test_reordered_inventory_and_fresh_hash_seeds_produce_identical_bytes(split_case):
    expected = canonical_json(build(split_case))
    assert (
        canonical_json(
            build(split_case, observations=list(reversed(split_case["candidate"]["observations"])))
        )
        == expected
    )
    code = """
import json, sys
sys.path[:] = json.loads(sys.argv[1])
from rent_contracts.validation import canonical_json
from rent_data.splits import build_development_split
print(canonical_json(build_development_split(**json.load(sys.stdin))))
"""
    for seed in ("1", "97"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-S", "-P", "-c", code, json.dumps(sys.path)],
            input=json.dumps(arguments(split_case)),
            text=True,
            capture_output=True,
            env=environment,
            check=True,
            timeout=15,
        )
        assert result.stdout == expected + "\n"


@pytest.mark.parametrize("field", ["expected_release_ref", "expected_policy_ref"])
def test_independently_fixed_input_identities_cannot_be_substituted(split_case, field):
    with pytest.raises(ContractError):
        build(split_case, **{field: content_digest(b"different external identity")})
    if field == "expected_release_ref":
        with pytest.raises(ContractError):
            build(split_case, expected_release_ref=split_case["candidate"]["candidate_digest"])


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "duplicate",
        "substitute",
        "changed-time",
        "changed-identity",
        "empty",
        "invalid-type",
    ],
)
def test_inventory_must_be_the_complete_exact_release_projection(split_case, kind):
    rows = copy.deepcopy(split_case["candidate"]["observations"])
    if kind == "missing":
        rows.pop()
    elif kind == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif kind == "substitute":
        rows[0]["observation_id"] = "substitute-observation"
    elif kind == "changed-time":
        rows[0]["features_available_at"] = "2026-03-02T12:00:00Z"
    elif kind == "changed-identity":
        rows[0]["property_identity"]["property_id"] = "different-property"
    elif kind == "empty":
        rows = []
    else:
        rows = None
    with pytest.raises(ContractError):
        build(split_case, observations=rows)


def test_self_consistent_declared_release_count_still_must_match_supplied_inventory(split_case):
    release = copy.deepcopy(split_case["release"])
    release["observation_count"] += 1
    release["acquisition_sources"][0]["record_count"] += 1
    release["release_digest"] = dataset_release_digest(release)
    with pytest.raises(ContractError, match="inventory correspondence"):
        build(split_case, release=release, expected_release_ref=release["release_digest"])


@pytest.mark.parametrize("reference", ["domain_policy_ref", "property_matching_policy_ref"])
@pytest.mark.parametrize("level", ["release", "observation"])
def test_policy_references_must_match_release_and_every_observation(split_case, reference, level):
    policy = copy.deepcopy(split_case["policy"])
    policy[reference] = content_digest(b"other policy")
    policy["policy_digest"] = evaluation_policy_digest(policy)
    release = copy.deepcopy(split_case["release"])
    if level == "observation":
        release["provenance"][reference] = policy[reference]
        release["release_digest"] = dataset_release_digest(release)
    with pytest.raises(ContractError):
        build(
            split_case,
            policy=policy,
            expected_policy_ref=policy["policy_digest"],
            release=release,
            expected_release_ref=release["release_digest"],
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("training_cutoff", None),
        ("training_cutoff", True),
        ("training_cutoff", "2026-02-30T00:00:00Z"),
        ("training_cutoff", "2026-01-20"),
        ("training_cutoff", "2026-01-20T00:00:00-00:00"),
        ("training_cutoff", "2026-01-20T00:00:00.0000001Z"),
        ("training_cutoff", "2026-02-02T00:00:00Z"),
        ("validation_window", {}),
        (
            "validation_window",
            {"start_inclusive": "2026-02-01T00:00:00Z", "end_exclusive": "2026-02-01T00:00:00Z"},
        ),
        (
            "validation_window",
            {"start_inclusive": "2026-02-30T00:00:00Z", "end_exclusive": "2026-03-01T00:00:00Z"},
        ),
        (
            "validation_window",
            {
                "start_inclusive": "2026-02-01T00:00:00Z",
                "end_exclusive": "2026-03-01T00:00:00Z",
                "selector": "private-untrusted-selector",
            },
        ),
        ("creation_provenance", {}),
        ("creation_provenance", None),
        (
            "creation_provenance",
            {"source_snapshot_ref": "main", "created_at": "2026-03-03T12:00:00Z"},
        ),
        (
            "creation_provenance",
            {
                "source_snapshot_ref": content_digest(b"fixture"),
                "created_at": "2026-02-30T00:00:00Z",
            },
        ),
    ],
)
def test_invalid_explicit_boundaries_and_provenance_fail_safely(split_case, field, value):
    with pytest.raises(ContractError) as failure:
        build(split_case, **{field: value})
    assert "private-untrusted-selector" not in str(failure.value)


@pytest.mark.parametrize(
    "instant,partition,cohorts",
    [
        ("2026-01-19T23:59:59.999999Z", "training", []),
        ("2026-01-20T00:00:00Z", "excluded", []),
        ("2026-02-01T00:00:00Z", "development_validation", ["future_market", "unseen_property"]),
        (
            "2026-02-01T02:00:00+02:00",
            "development_validation",
            ["future_market", "unseen_property"],
        ),
        ("2026-03-01T00:00:00Z", "excluded", []),
    ],
)
def test_exact_boundaries_and_offsets_use_prediction_instant(
    split_case, split_case_factory, instant, partition, cohorts
):
    row = copy.deepcopy(
        next(o for o in split_case["candidate"]["observations"] if o["observation_id"] == "obs-new")
    )
    for field in ("published_at", "collected_at", "features_available_at", "prediction_cutoff_at"):
        row[field] = instant
    case = split_case_factory(observations=[row])
    assignment = build(case)["memberships"][0]
    assert assignment["partition"] == partition
    assert assignment["cohorts"] == cohorts
    assert assignment["eligibility_exclusions"] == (
        ["outside_development_windows"] if partition == "excluded" else []
    )


@pytest.mark.parametrize("status", ["probable", "unresolved"])
def test_uncertain_training_blocks_secondary_for_complete_training_reference(
    split_case, split_case_factory, status
):
    observations = copy.deepcopy(split_case["candidate"]["observations"])
    train = next(o for o in observations if o["observation_id"] == "obs-train-a")
    train["property_identity"]["status"] = status
    if status == "unresolved":
        train["property_identity"]["property_id"] = None
    case = split_case_factory(observations=observations)
    m = build(case)
    new = next(row for row in m["memberships"] if row["observation_id"] == "obs-new")
    assert new["cohorts"] == ["future_market"]
    assert new["unseen_property_exclusions"] == ["training_identity_unresolved"]
    with pytest.raises(ContractError):
        validate_development_population(
            m, [], cohort="unseen_property", expected_split_ref=m["split_digest"]
        )
    m["memberships"] = [row for row in m["memberships"] if row["observation_id"] != "obs-train-a"]
    m["split_digest"] = development_split_digest(m)
    with pytest.raises(ContractError, match="population"):
        check(m, case)


def test_empty_primary_and_empty_training_are_explicit_metadata_not_execution_admission(
    split_case, split_case_factory
):
    rows = split_case["candidate"]["observations"]
    only_training = build(
        split_case_factory(
            observations=[o for o in rows if o["observation_id"].startswith("obs-train")]
        )
    )
    assert all(row["partition"] == "training" for row in only_training["memberships"])
    with pytest.raises(ContractError):
        validate_development_population(
            only_training,
            [],
            cohort="future_market",
            expected_split_ref=only_training["split_digest"],
        )
    only_validation = build(
        split_case_factory(observations=[o for o in rows if o["observation_id"] == "obs-new"])
    )
    assert only_validation["memberships"][0]["cohorts"] == ["future_market", "unseen_property"]
    assert not any(row["partition"] == "training" for row in only_validation["memberships"])


def test_identity_binds_release_policy_and_explicit_creation_facts(split_case):
    original = build(split_case)
    release = copy.deepcopy(split_case["release"])
    release["metadata"]["commit"] = "d" * 40
    release["release_digest"] = dataset_release_digest(release)
    changed_release = build(
        split_case, release=release, expected_release_ref=release["release_digest"]
    )
    provenance = {
        **split_case["parameters"]["creation_provenance"],
        "created_at": "2026-03-04T12:00:00Z",
    }
    changed_creation = build(split_case, creation_provenance=provenance)
    policy = copy.deepcopy(split_case["policy"])
    policy["policy_version"] = "synthetic-split-v2-label"
    policy["policy_digest"] = evaluation_policy_digest(policy)
    changed_policy = build(split_case, policy=policy, expected_policy_ref=policy["policy_digest"])
    for artifact in (changed_release, changed_creation, changed_policy):
        assert artifact["memberships"] == original["memberships"]
        assert artifact["split_digest"] != original["split_digest"]
        with pytest.raises(ContractError):
            validate_development_population(
                artifact,
                ["obs-new"],
                cohort="unseen_property",
                expected_split_ref=original["split_digest"],
            )


@pytest.mark.parametrize(
    "kind", ["omit", "duplicate", "substitute", "partition", "cohort", "reason"]
)
def test_resealed_wrong_membership_cannot_pass_release_split_validation(split_case, kind):
    manifest = build(split_case)
    new = next(row for row in manifest["memberships"] if row["observation_id"] == "obs-new")
    if kind == "omit":
        manifest["memberships"].pop()
    elif kind == "duplicate":
        manifest["memberships"].append(copy.deepcopy(new))
    elif kind == "substitute":
        new["observation_id"] = "substituted-observation"
    elif kind == "partition":
        new["partition"] = "training"
    elif kind == "cohort":
        new["cohorts"] = ["future_market"]
    else:
        new["eligibility_exclusions"] = ["outside_development_windows"]
    manifest["split_digest"] = development_split_digest(manifest)
    with pytest.raises(ContractError):
        check(manifest, split_case)


def test_legacy_order_acceptance_and_fixed_candidate_populations_are_preserved(split_case):
    manifest = build(split_case)
    manifest["memberships"].reverse()
    for row in manifest["memberships"]:
        for name in ("eligibility_exclusions", "cohorts", "unseen_property_exclusions"):
            row[name].reverse()
    manifest["split_digest"] = development_split_digest(manifest)
    check(manifest, split_case)
    validate_development_split(
        manifest,
        policy=split_case["policy"],
        observations=split_case["candidate"]["observations"],
        expected_dataset_ref=split_case["release"]["release_digest"],
    )
    primary = ["obs-unresolved", "obs-refresh", "obs-seen", "obs-new", "obs-probable"]
    validate_development_population(
        manifest, primary, cohort="future_market", expected_split_ref=manifest["split_digest"]
    )
    validate_development_population(
        manifest, ["obs-new"], cohort="unseen_property", expected_split_ref=manifest["split_digest"]
    )
    for changed in (primary[:-1], primary + primary[:1], primary[:-1] + ["obs-invalid"]):
        with pytest.raises(ContractError):
            validate_development_population(
                manifest,
                changed,
                cohort="future_market",
                expected_split_ref=manifest["split_digest"],
            )


def test_whole_inventory_limit_fails_without_truncation(split_case):
    prototype = next(
        o for o in split_case["candidate"]["observations"] if o["observation_id"] == "obs-new"
    )
    oversized = []
    for index in range(2000):
        row = copy.deepcopy(prototype)
        row.update(observation_id=f"observation-{index}", listing_id=f"listing-{index}")
        oversized.append(row)
    with pytest.raises(ContractError, match="size limit"):
        build(split_case, observations=oversized)
