# Development split materialization v1

M2 increment 4 implements the existing [development evaluation proposal](evaluation-contracts-v1.md)
on metadata from [sealed development releases](dataset-releases-v1.md). Frozen
architecture §§4–6, 8–9 and 15–16 remain authoritative. This is source for a
synthetic-first data operation, not effective policy, real-data approval or an
official benchmark. There is no new split-plan schema or wire version.

## Responsibilities and inputs

`rent_contracts.evaluation.derive_development_memberships` exposes the existing v1
partition/exclusion/cohort rules as independent, deterministically ordered rows.
The same internal derivation is used by `validate_development_split`. Temporal
parameter validation reuses the bundled split field schemas through the contract
package's local resource registry and its existing calendar parser. Data code uses
the public helper; resource internals remain inside `rent_contracts`.

`rent_data.splits.build_development_split` is pure. All inputs are explicit:

| Input | Validation/binding |
| --- | --- |
| Sealed development release and `expected_release_ref` | Existing release schema, self-digest, exact externally supplied identity and internal roster/count invariants |
| Complete observation list | Existing metadata/calendar/identity checks; exact inventory digest and count must equal the release |
| Evaluation policy and `expected_policy_ref` | Closed v1 rule declarations, self-digest and externally supplied policy identity |
| Domain and property matching references | Release provenance, policy and every observation must agree |
| Training cutoff and validation window | Existing v1 syntax/calendar/order requirements; no inferred dates |
| Creation provenance | Required `source_snapshot_ref` and `created_at`, both supplied; existing schema/calendar validation |

The pure API binds the complete supplied inventory to release metadata. It does
not read artifacts, prove DVC recovery, verify source-snapshot truth or authenticate
references. An independently fixed expected digest is necessary for substitution
checks, but cannot grant access or prove review. These APIs accept no approval flag,
model-specific selector, candidate training subset or arbitrary executable policy.

The builder produces the **existing** `development-split` v1 document, computes its
self-digest and runs full semantic validation. `validate_release_split` performs the
same release/inventory/policy checks plus existing split validation and an externally
fixed `expected_split_ref`. It does not treat a self-consistent digest as authority.

## Membership and reproducibility

Existing rules and reasons are unchanged:

- Training prediction cutoff is strictly before the declared training cutoff.
  Validation uses `[start_inclusive, end_exclusive)` with
  `training_cutoff <= start_inclusive < end_exclusive`; gaps/outside observations
  receive explicit exclusions.
- Every supplied observation receives exactly one row, including excluded rows.
  All applicable eligibility reasons accumulate. Unknown evidence remains unknown.
- Every eligible validation row enters `future_market`. Seen properties/listings
  remain in that primary view. Unconfirmed validation identities cannot become
  unseen; uncertain identities anywhere in the complete declared training partition
  block the secondary view under the current conservative v1 rule.
- Candidate-specific training subsets never change that reference partition or
  expand unseen membership. The two development views can overlap.

Generated memberships are sorted by observation ID, with sorted reason/cohort arrays.
Old validators still accept their previously valid array ordering. Readback validates
semantics and the requested digest rather than forcing other valid v1 artifacts to
match this builder's array order.

Identical **complete** inputs produce identical canonical JSON bytes and identity,
including across input order, processes/hash seeds and independently restored copies.
Creation provenance is an input: the builder never reads the clock, local path or
machine state. Changing `created_at`, source snapshot, release or policy changes
split identity even if the assignments stay equal. Callers must preserve the exact
provenance when reproducing an artifact; do not fabricate timestamps or hash a
convenient branch label as a substitute for source-snapshot evidence.

Empty training/primary/secondary populations remain representable metadata states.
There is no fallback random split or guessed minimum population. An empty evaluation
cohort continues to fail `validate_development_population`; future training admission
must separately enforce its input requirements. Successful metadata construction is
not proof that a useful training/evaluation operation can run.

All fifteen existing schemas, canonicalization rules and 1 MiB bounds remain intact.
Oversized input/output fails without truncating records. Scalable table transport,
real labels/features, currency normalization and split DVC publication/retention are
outside this local metadata operation.

## Verified local artifact flow

`rent_data.split_io.materialize_development_split(restored_directory, destination, ...)`:

1. Requires explicit absolute, separate paths; rejects symlink roots/parents,
   traversal components, output overlap with the restored workspace and prior outputs.
2. Calls `read_verified_restore` with the expected release reference. That checks the
   completion report, rehashes every payload artifact and reconstructs the complete
   source-backed candidate. A report alone is not accepted as evidence of unchanged bytes.
3. Builds the split from the candidate's complete observation list, policy and
   explicit temporal/provenance inputs. All metadata validation precedes output creation.
4. Exclusively creates a new output directory and atomically creates its sole final
   artifact, `development-split.json`, outside the restored workspace. No release
   payload, metadata, cache or prior split is modified.

The shared `rent_data.release_io.create_json_artifact` primitive serializes bounded
canonical JSON, creates an owned `.artifact-*` temporary file, flushes/fsyncs it,
then links the final name atomically without replacing any existing leaf. Restoration
keeps its existing semantic/payload checks before using this same primitive for its
completion report. A failed attempt may leave a new empty/incomplete output directory;
without the final valid split file it cannot be consumed. Cleanup is best effort and
does not invalidate a successfully installed final file. Retry with a new destination
or inspect/remove only an owned disposable failed output; never overwrite a prior one.

`read_verified_development_split` requires expected release, policy and split refs.
It rechecks the restored release, reads only the fixed bounded regular split file,
and validates all release/policy/inventory/membership correspondence. Leaf symlinks,
FIFOs, malformed/oversized JSON, missing/corrupt/substituted artifacts fail. The split
is the artifact; unrelated output-directory entries are not inputs or a verified
directory inventory. No archive extraction, network access, DVC write or CLI occurs.

These are single-writer local filesystem operations. They do not certify concurrent
adversarial access, power-loss durability, disk/process quotas, host isolation or
protected storage permissions. Filesystem/digest checks are not a trusted resolver.

## Verification and remaining gates

Handwritten expected membership fixtures independently check partitions, reason
accumulation, boundaries/offsets, seen/uncertain identities and empty populations.
Existing evaluation fixtures remain unchanged. New tests verify complete release
binding, provenance-dependent identity, legacy order acceptance, fixed candidate
populations, fresh-interpreter determinism and unsafe/interrupted I/O. Actual DVC
integration restores old A after B into independent consumer caches, materializes
splits and checks identical bytes plus source preservation; unit markers alone do
not claim a successful DVC operation.

See [development checks](../development.md) and the [increment report](../reports/m2-development-splits.md).
Before real-data use, independently review domain/eligibility/cutoff/unseen/projection
policies and permitted input handling; supply authorized defensible chronology or
approved remediation and reviewed property pairs/identity policy; decide storage,
access, retention and quality; and implement scalable transport. M0's historical CSV
has no observation timestamps, and current source dates/scraper behavior do not
reconstruct that history. Source approval here does not activate those policies.

Membership consistency does not prove feature availability, training-only fitted
preprocessing, cutoff-aware/cross-fitted target aggregates, label quality, identity
accuracy, authorized evaluation or leakage freedom. Those need execution/source/
lineage checks in later increments. A14 and M2's reproducible-run/development-
evaluation exit gate remain open.
