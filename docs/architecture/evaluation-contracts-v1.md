# Development evaluation contracts v1.0.0 — proposal

Status: **source proposal for independent policy review**, not an effective trusted
policy or an official split. Authority: frozen specification §§8–9, 12.7, 13.4 and
the [A14 handoff](../reports/a14-evaluation-handoff.md#incomplete-benchmark-prerequisites).
The contracts are additive to [public contracts v1](contracts-v1.md). No legacy
cleaning, random split, API or prediction interface changes in this increment.

## Documents and identities

Three locally bundled schemas use independent `contract_version=1.0.0` fields:

| Document | Purpose and identity |
| --- | --- |
| `observation-reference` | Metadata for one capture: opaque `listing_id`, stable `observation_id`, nullable physical `property_id`, explicit resolution status/confidence and policy/evidence references. An observation ID is assigned from source provenance, never inferred from a row number. These validators cannot establish how an ID was assigned. |
| `evaluation-policy` | Versioned, target-independent eligibility and conservative unseen-property rules; binds non-target domain and matching policies by SHA-256 reference. `policy_version` is descriptive; `policy_digest` identifies the complete content. No executable selector, thresholds, labels or self-approval fields. |
| `development-split` | Development-only assignment envelope, identified by `split_digest`: expected dataset-release reference, observation inventory digest, policy reference, training cutoff, one validation window, every assignment/exclusion/cohort and creation provenance. |

Dataset and split references remain SHA-256 envelopes, compatible with existing
`dataset_ref`/`split_ref` requests. This increment does not implement the §8.2 release
envelope, DVC object identity, restoration, authorization or publication. A release
resolver must independently establish that the supplied metadata is the complete
authorized development inventory of that exact dataset. A matching reference alone
does not establish this. Restricted records must never be supplied to these helpers.

Listing, observation and property IDs are distinct namespaces, even if their opaque
strings happen to match. Repeated listing observations are allowed at distinct
collection instants; separate listings may share a property. Duplicate observation
IDs, aliased `(listing_id, collected_at)` instants, and conflicting confirmed property
IDs for one listing fail. A source that recycles ad identifiers needs a reviewed
namespacing policy. References contain no contacts, addresses, source text or labels;
they remain potentially sensitive metadata, not a guarantee of anonymization.

`property_identity.status` is `confirmed`, `probable` or `unresolved`. Confirmed and
probable identities require a property reference. Unresolved identity requires null
property ID and confidence. Confidence may otherwise be null: it is not a guessed
probability or a decision threshold. The referenced matching policy must use reviewed
non-target signals; these helpers neither match apartments nor validate confidence
calibration. Identity assignments and their matching-policy references are included
in the inventory digest, binding the identity version used for this split.

## Proposed time and eligibility semantics

Each observation explicitly supplies nullable publication, collection,
feature-availability and prediction-cutoff instants plus a nullable
`temporal_evidence_ref`. Null means unknown; missing fields fail. No first/last-seen
date, file modification time, source reset date or recalled acquisition month is
silently converted into a time. Known instants use timezone-qualified RFC 3339-style
text with uppercase `T`/`Z`, seconds and at most six fractional digits. Date-only,
timezone-free, unknown-offset `-00:00`, impossible calendar and leap-second values
fail. Offset-qualified instants compare by time, not lexical order.

The proposed initial rule is deliberately conservative:

`published_at <= collected_at <= features_available_at <= prediction_cutoff_at`.

Here `features_available_at` is the availability of the **entire captured input
snapshot**, including collection, not the earliest date a source attribute might
have existed. A later-captured snapshot cannot be assigned an earlier availability
merely because its ad was published earlier. A future historical reconstruction
needs reviewed evidence and a separately versioned rule if these semantics change.
Evidence references are declarations to verify, not proof of reliability.

Non-target `domain_status` is `valid`, `invalid` or `unresolved`, under exactly the
policy's `domain_policy_ref`. It concerns allowed domain/feature metadata only;
it must not wrap legacy `clean_data`, which filters/deduplicates using prices.
Referenced policy implementations and evidence require independent review.

Training uses prediction cutoffs **strictly before** `training_cutoff`. Development
validation uses `[start_inclusive, end_exclusive)`. Require
`training_cutoff <= start_inclusive < end_exclusive`; any gap is explicitly excluded.
Every supplied observation appears exactly once, including excluded observations.
The following eligibility reasons accumulate; the manifest must declare the exact
set. A usable observation must enter its chronological partition, rather than be
arbitrarily excluded by a candidate.

| Eligibility exclusion | Meaning |
| --- | --- |
| `invalid_non_target_domain` | Non-target domain validation failed. |
| `unresolved_non_target_domain` | Non-target domain validation lacks a decision. |
| `temporal_evidence_missing` | Any required time or the evidence reference is null. |
| `temporal_order_invalid` | Known times contradict the proposed availability order. |
| `outside_development_windows` | Known prediction cutoff is neither in training nor validation. |

Missing/inconsistent metadata remains representable for quarantine and reporting.
It cannot enter training or evaluation under this rule. There are no price caps,
rent/m² bounds, local-rent ratios, residual filters, target-based deduplication or
candidate-specific exclusions. Label validation and difficult-price subgroup
reporting remain later work: an unusable label/prediction must not silently shrink
the fixed comparison population. Model-specific training cleaning/subsets remain
possible later, with their lineage documented separately from evaluation membership.

## Development views and property overlap

Every usable development-validation observation belongs to `future_market`,
including represented, probable and unresolved properties. Its `unseen_property`
membership requires confirmed identity, no matching listing or confirmed/probable
property reference in the complete declared training partition, and confirmed
identity for **every** training observation. This last conservative rule avoids
assuming that an unresolved training apartment could not be the evaluation apartment.
It may yield an empty secondary cohort. Do not relax it using guessed thresholds;
reviewed identity evidence or a separately reviewed/versioned rule is needed.

The complete declared training partition is the comparison reference, even if a
candidate later uses a smaller training subset. The secondary view never expands
because one candidate dropped training rows.

| Unseen-property exclusion | Meaning |
| --- | --- |
| `not_development_validation` | Training/excluded observation; no evaluation membership. |
| `listing_seen_in_training` | A training capture has the same listing reference. |
| `property_overlap_training` | A training capture has the same non-null property reference, including a probable match. |
| `property_identity_unconfirmed` | Evaluation identity is probable or unresolved. |
| `training_identity_unresolved` | At least one training identity is probable or unresolved. |

Validation observations excluded from the secondary view remain in the primary
view; property overlap is measured rather than silently removed. The two views
overlap and must not be reported as statistically independent. Strictly disjoint
property-held-out training would be a separate benchmark, not this policy.

## Validation, integrity and comparison

Use the semantic helpers in `rent_contracts.evaluation`:

- `validate_observation_reference` checks schema and calendar instants without
  optional date-format dependencies. It preserves unknown/inconsistent evidence.
- `validate_evaluation_policy` checks the closed rule declarations and self-digest.
- `observation_inventory_digest` validates references/collisions and hashes the
  complete inventory sorted by observation ID. Input order is not identity.
- `validate_development_split(..., policy=..., observations=...,
  expected_dataset_ref=...)` checks policy/dataset correspondence, inventory digest,
  complete unique assignment, temporal eligibility, reasons and cohort semantics.
- After full split validation, `validate_development_population(..., cohort=...,
  expected_split_ref=...)` checks each candidate's exact observation population.
  Record order may differ; empty, missing, extra, substituted or duplicate records
  fail the comparison. Keep one externally fixed split reference across candidates.

`validate_document` remains the low-level schema boundary; it does not replace
these semantic helpers. The split/policy hash uses the existing local canonical JSON
rule: sorted object keys, UTF-8, no insignificant whitespace, `ensure_ascii=False`,
excluding **only** the respective top-level self-digest. Manifest arrays retain
their order. Inventory hashing first sorts observations by ID. Canonicalization is
locally versioned, not an RFC 8785 claim. Helpers do not mutate caller documents.
Existing 1 MiB JSON limits apply; scalable table transport/sharding is deferred.
Changing referenced policies, metadata, assignments, exclusions, cutoffs or provenance
changes identity. Recomputing a digest is not authorization or evidence of review.

This development envelope intentionally has no final-holdout period, membership,
counts, labels, storage location or reference. It is **not** the full protected
§9.4 manifest. Later trusted code must manage restricted details separately and bind
authorized views without disclosing them. Closed fields are not a storage/access
security boundary and cannot detect secrets hidden in caller-controlled identifiers.

## Evidence limits and review gates

Synthetic fixtures verify declared overlap, eligibility and candidate population
invariants. They do not inspect features, fitted-transform inputs, target aggregate
source/cutoff/cross-fitting lineage, training-label availability, matching quality,
actual dataset completeness, final-holdout isolation or permissions. Honest metadata
cannot be assumed. Contracts alone do not establish leakage-free features/evaluation.
Target-derived features and target-dependent matching/selection require independent
source/lineage checks even when these declarations pass.

The bound training observation IDs and availability/cutoff times provide the
reference population for later checks of fitted-transform and target-aggregate
source IDs. This increment rejects labels/target aggregates as observation metadata
and rejects declared target-based selectors or price matching. It does not yet
define or verify feature/aggregate lineage records; those checks belong with the
training boundaries, rather than being inferred from a split pass.

Before real-data use, independently review this proposed eligibility/exclusion and
unseen-property policy, referenced non-target domain/currency and matching policies,
authorized private field projection, reviewed property pairs and defensible timestamp
evidence or an approved remediation. The historical CSV cannot satisfy chronology
by relabeling copy dates; current scraper dates do not reconstruct observations.
Data release/access/retention and acquisition rights remain external prerequisites.
No real split, release, training run, benchmark, protected policy or M2 exit gate is
established by this increment. Evidence and the single next increment are recorded
in the [M2 task plan](../tasks/2026-11-05-m2-evaluation-contracts/plan.md).
