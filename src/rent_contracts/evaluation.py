"""Development metadata contracts, not a data resolver or leakage certification (§9).

The closed v1 rules are a reviewable source proposal. No helper reads data, resolves
references, fits transforms, evaluates labels or activates an effective policy.
"""

import hashlib
from datetime import datetime

from .validation import ContractError, canonical_json, validate_document

_TIME_FIELDS = ("published_at", "collected_at", "features_available_at", "prediction_cutoff_at")
_COHORTS = ("future_market", "unseen_property")


def _digest(document: dict | list) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()


def evaluation_policy_digest(policy: dict) -> str:
    """Use existing v1 canonical JSON, excluding only the top-level self-digest."""
    return _digest({key: value for key, value in policy.items() if key != "policy_digest"})


def development_split_digest(manifest: dict) -> str:
    """Bind policy, inventory, membership, exclusions, cutoffs and provenance."""
    return _digest({key: value for key, value in manifest.items() if key != "split_digest"})


def validate_evaluation_policy(policy: dict) -> None:
    validate_document("evaluation-policy", policy)
    if evaluation_policy_digest(policy) != policy["policy_digest"]:
        raise ContractError("evaluation policy digest mismatch")


def _instant(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError
        return instant
    except (ValueError, OverflowError):
        raise ContractError("unsupported contract timestamp") from None


def validate_observation_reference(observation: dict) -> None:
    """Validate metadata and calendar instants without optional format dependencies.

    Missing or contradictory evidence is representable; split eligibility must
    exclude it. No time or identity evidence is reconstructed here.
    """
    validate_document("observation-reference", observation)
    for field in _TIME_FIELDS:
        if observation[field] is not None:
            _instant(observation[field])


def _observation_inventory(observations: list[dict]) -> dict[str, dict]:
    if type(observations) is not list or not observations:
        raise ContractError("observation inventory must be a nonempty list")
    inventory = {}
    captures = set()
    confirmed_listings = {}
    for observation in observations:
        validate_observation_reference(observation)
        observation_id = observation["observation_id"]
        if observation_id in inventory:
            raise ContractError("duplicate observation identity")
        inventory[observation_id] = observation
        if observation["collected_at"] is not None:
            capture = (observation["listing_id"], _instant(observation["collected_at"]))
            if capture in captures:
                raise ContractError("duplicate listing collection instant")
            captures.add(capture)
        identity = observation["property_identity"]
        if identity["status"] == "confirmed":
            prior = confirmed_listings.setdefault(
                observation["listing_id"], identity["property_id"]
            )
            if prior != identity["property_id"]:
                raise ContractError("conflicting confirmed listing property identities")
    return inventory


def observation_inventory_digest(observations: list[dict]) -> str:
    """Bind every supplied reference, sorted by observation ID rather than row position.

    This cannot establish that a resolver supplied the complete authorized release.
    """
    inventory = _observation_inventory(observations)
    return _digest([inventory[key] for key in sorted(inventory)])


def observation_eligibility_exclusions(observation: dict) -> frozenset[str]:
    """Existing v1 non-window reasons, shared with candidate quality reporting.

    This validates declared metadata; it neither verifies evidence nor chooses a
    temporal partition. Property uncertainty alone does not exclude future-market rows.
    """
    validate_observation_reference(observation)
    reasons = set()
    if observation["domain_status"] != "valid":
        reasons.add(f"{observation['domain_status']}_non_target_domain")
    times = [
        None if observation[key] is None else _instant(observation[key]) for key in _TIME_FIELDS
    ]
    if None in times or observation["temporal_evidence_ref"] is None:
        reasons.add("temporal_evidence_missing")
    known_times = [instant for instant in times if instant is not None]
    if any(a > b for a, b in zip(known_times, known_times[1:])):
        reasons.add("temporal_order_invalid")
    return frozenset(reasons)


def _assignment(
    observation: dict, cutoff: datetime, start: datetime, end: datetime
) -> tuple[str, set[str]]:
    reasons = set(observation_eligibility_exclusions(observation))
    value = observation["prediction_cutoff_at"]
    prediction = None if value is None else _instant(value)
    if prediction is not None and prediction >= cutoff and not start <= prediction < end:
        reasons.add("outside_development_windows")
    partition = "excluded"
    if not reasons:
        partition = "training" if prediction < cutoff else "development_validation"
    return partition, reasons


def _unseen_exclusions(observation: dict, training: list[dict]) -> set[str]:
    reasons = set()
    identity = observation["property_identity"]
    if any(row["listing_id"] == observation["listing_id"] for row in training):
        reasons.add("listing_seen_in_training")
    if identity["property_id"] is not None and any(
        row["property_identity"]["property_id"] == identity["property_id"] for row in training
    ):
        reasons.add("property_overlap_training")
    if identity["status"] != "confirmed":
        reasons.add("property_identity_unconfirmed")
    if any(row["property_identity"]["status"] != "confirmed" for row in training):
        reasons.add("training_identity_unresolved")
    return reasons


def _validate_split_envelope(manifest: dict) -> None:
    validate_document("development-split", manifest)
    if development_split_digest(manifest) != manifest["split_digest"]:
        raise ContractError("development split digest mismatch")
    keys = [row["observation_id"] for row in manifest["memberships"]]
    if len(set(keys)) != len(keys):
        raise ContractError("duplicate development assignment population")


def validate_development_split(
    manifest: dict, *, policy: dict, observations: list[dict], expected_dataset_ref: str
) -> None:
    """Check complete supplied population, declared evidence and v1 assignments.

    Dataset/policy authorization, evidence truth, protected access and actual feature
    lineage require independent verification. This does not generate an official split.
    """
    _validate_split_envelope(manifest)
    validate_evaluation_policy(policy)
    if manifest["dataset_ref"] != expected_dataset_ref:
        raise ContractError("development dataset identity mismatch")
    if manifest["policy_ref"] != policy["policy_digest"]:
        raise ContractError("development policy identity mismatch")
    inventory = _observation_inventory(observations)
    if manifest["observations_digest"] != _digest([inventory[key] for key in sorted(inventory)]):
        raise ContractError("observation inventory digest mismatch")
    cutoff = _instant(manifest["training_cutoff"])
    start = _instant(manifest["validation_window"]["start_inclusive"])
    end = _instant(manifest["validation_window"]["end_exclusive"])
    _instant(manifest["creation_provenance"]["created_at"])
    if not cutoff <= start < end:
        raise ContractError("invalid development temporal boundaries")
    rows = manifest["memberships"]
    actual = [row["observation_id"] for row in rows]
    if len(set(actual)) != len(actual) or set(actual) != set(inventory):
        raise ContractError("development assignment population mismatch")
    for row in rows:
        observation = inventory[row["observation_id"]]
        if observation["domain_policy_ref"] != policy["domain_policy_ref"]:
            raise ContractError("observation domain policy identity mismatch")
        if observation["property_identity"]["policy_ref"] != policy["property_matching_policy_ref"]:
            raise ContractError("observation matching policy identity mismatch")
        partition, reasons = _assignment(observation, cutoff, start, end)
        if row["partition"] != partition or set(row["eligibility_exclusions"]) != reasons:
            raise ContractError("development eligibility assignment mismatch")
    training = [inventory[row["observation_id"]] for row in rows if row["partition"] == "training"]
    for row in rows:
        cohorts = set()
        unseen_reasons = {"not_development_validation"}
        if row["partition"] == "development_validation":
            cohorts.add("future_market")
            unseen_reasons = _unseen_exclusions(inventory[row["observation_id"]], training)
            if not unseen_reasons:
                cohorts.add("unseen_property")
        if (
            set(row["cohorts"]) != cohorts
            or set(row["unseen_property_exclusions"]) != unseen_reasons
        ):
            raise ContractError("development cohort assignment mismatch")


def validate_development_population(
    manifest: dict, observation_ids: list[str], *, cohort: str, expected_split_ref: str
) -> None:
    """Require each candidate's complete cohort against a previously validated split.

    Records may be reordered. Missing/duplicate/extra records or a substituted split
    fail the comparison, rather than silently changing evaluation membership.
    """
    _validate_split_envelope(manifest)
    if manifest["split_digest"] != expected_split_ref:
        raise ContractError("comparison split identity mismatch")
    if cohort not in _COHORTS:
        raise ContractError("unsupported development cohort")
    expected = {
        row["observation_id"] for row in manifest["memberships"] if cohort in row["cohorts"]
    }
    if (
        not expected
        or type(observation_ids) is not list
        or any(type(key) is not str for key in observation_ids)
        or len(set(observation_ids)) != len(observation_ids)
        or set(observation_ids) != expected
    ):
        raise ContractError("development evaluation population mismatch")
