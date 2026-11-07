"""Pure development split materialization; no I/O, clock, training or policy authority."""

import copy

from rent_contracts import ContractError
from rent_contracts.evaluation import (
    derive_development_memberships,
    development_split_digest,
    observation_inventory_digest,
    validate_development_split,
    validate_evaluation_policy,
)
from rent_contracts.validation import canonical_json

from .releases import validate_dataset_release


def _validate_inputs(
    release: dict,
    observations: list[dict],
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
) -> str:
    validate_dataset_release(release, expected_release_ref=expected_release_ref)
    validate_evaluation_policy(policy)
    if policy["policy_digest"] != expected_policy_ref:
        raise ContractError("expected development policy identity mismatch")
    for name in ("domain_policy_ref", "property_matching_policy_ref"):
        if release["provenance"][name] != policy[name]:
            raise ContractError("release evaluation policy correspondence mismatch")
    inventory_digest = observation_inventory_digest(observations)
    if (
        inventory_digest != release["observations_digest"]
        or len(observations) != release["observation_count"]
    ):
        raise ContractError("release split inventory correspondence mismatch")
    return inventory_digest


def validate_release_split(
    manifest: dict,
    *,
    release: dict,
    observations: list[dict],
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
    expected_split_ref: str,
) -> None:
    """Check fixed external identities and the complete release-bound v1 population.

    Metadata correspondence alone does not prove storage recovery, authorization,
    policy review or feature/label lineage. The I/O wrapper revalidates recovery.
    """
    _validate_inputs(release, observations, policy, expected_release_ref, expected_policy_ref)
    validate_development_split(
        manifest,
        policy=policy,
        observations=observations,
        expected_dataset_ref=expected_release_ref,
    )
    if manifest["split_digest"] != expected_split_ref:
        raise ContractError("expected development split identity mismatch")


def build_development_split(
    *,
    release: dict,
    observations: list[dict],
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
    training_cutoff: str,
    validation_window: dict,
    creation_provenance: dict,
) -> dict:
    """Create the existing v1 split from explicit, fully bound metadata inputs.

    Creation provenance is supplied, never inferred from a clock or local path.
    Empty training/cohorts remain representable; this is not execution admission.
    """
    inventory_digest = _validate_inputs(
        release, observations, policy, expected_release_ref, expected_policy_ref
    )
    canonical_json(creation_provenance)
    memberships = derive_development_memberships(
        observations,
        policy=policy,
        training_cutoff=training_cutoff,
        validation_window=validation_window,
    )
    manifest = {
        "contract_version": "1.0.0",
        "access_domain": "development",
        "dataset_ref": expected_release_ref,
        "observations_digest": inventory_digest,
        "policy_ref": expected_policy_ref,
        "training_cutoff": training_cutoff,
        "validation_window": copy.deepcopy(validation_window),
        "memberships": memberships,
        "creation_provenance": copy.deepcopy(creation_provenance),
    }
    manifest["split_digest"] = development_split_digest(manifest)
    validate_release_split(
        manifest,
        release=release,
        observations=observations,
        policy=policy,
        expected_release_ref=expected_release_ref,
        expected_policy_ref=expected_policy_ref,
        expected_split_ref=manifest["split_digest"],
    )
    return manifest
