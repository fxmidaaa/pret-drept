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
from rent_contracts.validation import MAX_DOCUMENT_BYTES, DocumentSizeError, canonical_json

from .candidates import INLINE_VERSION
from .releases import validate_dataset_release

# The complete split is one canonical JSON document with a row for every observation,
# so the smallest row any observation can derive bounds the population that could fit.
# A population above this ceiling is rejected before any derivation. At or below it,
# the exact canonical size decides. This is a shortcut, never a promise that it fits.
_SMALLEST_MEMBERSHIP = {
    "observation_id": "a",
    "partition": "training",
    "eligibility_exclusions": [],
    "cohorts": [],
    "unseen_property_exclusions": ["not_development_validation"],
}
MAX_SPLIT_OBSERVATIONS = MAX_DOCUMENT_BYTES // (
    len(canonical_json(_SMALLEST_MEMBERSHIP).encode("utf-8")) + 1
)
_OUTPUT_LIMIT = "development split output size limit exceeded"


def _inventory_limit(release: dict) -> int | None:
    """Select the inventory bound for an already validated release.

    An inline v1 release keeps the single-document inventory bound. A v2 release carries
    its inventory as verified Parquet, so only the split output bounds its population.
    """
    return None if release["contract_version"] == INLINE_VERSION else MAX_SPLIT_OBSERVATIONS


def _validate_inputs(
    release: dict,
    observations: list[dict],
    policy: dict,
    expected_release_ref: str,
    expected_policy_ref: str,
) -> tuple[str, int | None]:
    validate_dataset_release(release, expected_release_ref=expected_release_ref)
    limit = _inventory_limit(release)
    if limit is not None and type(observations) is list and len(observations) > limit:
        raise ContractError(_OUTPUT_LIMIT)
    validate_evaluation_policy(policy)
    if policy["policy_digest"] != expected_policy_ref:
        raise ContractError("expected development policy identity mismatch")
    for name in ("domain_policy_ref", "property_matching_policy_ref"):
        if release["provenance"][name] != policy[name]:
            raise ContractError("release evaluation policy correspondence mismatch")
    inventory_digest = observation_inventory_digest(observations, max_inventory_records=limit)
    if (
        inventory_digest != release["observations_digest"]
        or len(observations) != release["observation_count"]
    ):
        raise ContractError("release split inventory correspondence mismatch")
    return inventory_digest, limit


def _seal(manifest: dict) -> str:
    """Identify the split, requiring the stored document to fit its one-document bound.

    Every other field is validated before this point, so a size error here is the
    complete split exceeding its output bound. It is reported before anything is written.
    """
    try:
        digest = development_split_digest(manifest)
        canonical_json({**manifest, "split_digest": digest})
    except DocumentSizeError:
        raise ContractError(_OUTPUT_LIMIT) from None
    return digest


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
    """Check fixed external identities and the complete release-bound population.

    Inline v1 and reference-backed v2 releases share the same split contract and rules.
    Metadata correspondence alone does not prove storage recovery, authorization,
    policy review or feature/label lineage. The I/O wrapper revalidates recovery.
    """
    _, limit = _validate_inputs(
        release, observations, policy, expected_release_ref, expected_policy_ref
    )
    validate_development_split(
        manifest,
        policy=policy,
        observations=observations,
        expected_dataset_ref=expected_release_ref,
        max_inventory_records=limit,
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
    """Create the existing v1 split document from explicit, fully bound metadata inputs.

    The release may be an inline v1 or a reference-backed v2 release; the document,
    rules and ordering are identical and only the release identity differs. A split
    whose complete document would exceed one JSON document is rejected here.
    Creation provenance is supplied, never inferred from a clock or local path.
    Empty training/cohorts remain representable; this is not execution admission.
    """
    inventory_digest, limit = _validate_inputs(
        release, observations, policy, expected_release_ref, expected_policy_ref
    )
    canonical_json(creation_provenance)
    memberships = derive_development_memberships(
        observations,
        policy=policy,
        training_cutoff=training_cutoff,
        validation_window=validation_window,
        max_inventory_records=limit,
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
    manifest["split_digest"] = _seal(manifest)
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
