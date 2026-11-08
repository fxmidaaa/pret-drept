# Development splits from reference-backed releases

M2 increment 7 lets the existing [development split materializer](development-splits-v1.md)
consume sealed [reference-backed (v2) releases](observation-inventory-references-v2.md) as
well as inline v1 releases. There is no new split schema, rule or wire version. Frozen
architecture §§4–6, 8–9 and 15–16 remain authoritative. This is source for a synthetic-first
data operation, not effective policy, real-data approval or an official benchmark.

## Version dispatch and shared semantics

`build_development_split`, `validate_release_split`, `materialize_development_split` and
`read_verified_development_split` accept either release version. The sealed release is
validated first, so any other `contract_version` fails before any output exists. The
increment 6 gate that rejected v2 is gone. The release version selects only what the verified
population is checked against and which inventory bound applies:

| | Inline v1 release | Reference-backed v2 release |
| --- | --- | --- |
| Population | Source-backed rebuild, verified equal to the inline `candidate.json` observations | Source-backed rebuild, verified against the exact Parquet bytes |
| Inventory bound | The canonical array fits one 1 MiB document | Record ceiling of 7,133 observations; no single-document bound |
| Split document | `development-split` v1 | The same document |
| `dataset_ref` | The v1 release digest | The v2 release digest |

Partition, exclusion, cohort, boundary and property-matching rules are implemented once in
`rent_contracts.evaluation` and shared. For equal observations and policy both versions
produce identical membership rows (partitions, reasons and both cohorts), the same
`observations_digest` and the same creation provenance. Only release lineage differs: the
`dataset_ref`, and therefore the `split_digest`, name the release that supplied the
population. A split presented under the other version's release fails with a dataset identity
mismatch. Observation identities, declared instants, offsets and rule outcomes are preserved,
and rows are sorted by observation ID regardless of input order.

## Verified population

`rent_data.release_io.read_verified_restore_observations` returns a fresh copy of the
population from the same all-or-nothing verification as `read_verified_restore`. That pass
requires the completion report, the exact release roster and every restored byte. For v2 it
also pins the canonical inventory manifest before opening Parquet, verifies the file hash,
size, schema and complete ordered population, and rebuilds the candidate from every source
envelope. The rows are that source-backed rebuild. They are not decoded a second time from
Parquet, and nothing is returned from a payload that failed any check. A v2 restoration
directory must be reached by a resolved path without symlink components.

## Input limits and the output limit

The opt-in `max_inventory_records` keyword on `observation_inventory_digest`,
`derive_development_memberships` and `validate_development_split` replaces only the legacy
bound that the canonical inventory array fit one JSON document. Its default is that legacy
bound, so existing callers, digests and errors are unchanged. A given limit streams the
identical canonical array through the existing hasher: the digest equals the default wherever
both apply. The limit must be a positive integer and the population is never truncated.

| Limit | Applies to | Value |
| --- | --- | --- |
| Single-document inventory | Helpers called without a record limit, inline v1 | 1 MiB canonical array |
| Inventory transport | Parquet files written and read by increment 5 | 100,000 records, 128 MiB, 8 KiB manifest |
| v2 source and lineage | Candidate rebuild and release verification | 4 MiB of source bytes; 1 MiB per envelope, candidate and release |
| Split population ceiling | v2 derivation and validation | 7,133 observations |
| Split output | The complete `development-split` document | 1 MiB canonical JSON |

The input limits above decide whether a release can exist. The output limit decides whether
its complete split can be stored. A synthetic v2 inventory of 1,500 long-identifier
observations has 1.40 MiB of logical JSON, which the legacy path rejects, yet its split is
458,233 bytes. Every observation contributes one membership row, so output grows with the
population and the identifier length.

- A row is 146 to 391 bytes: a one-character training row up to a 128-character identifier
  with four unseen-property reasons. The 40 reachable row shapes are enumerated in the tests.
  The fixed fields outside `memberships` take 734 bytes.
- At most **2,673** observations always fit, whatever their identifiers or reasons. No
  population above 7,128 can fit. The ceiling is 7,133 because it divides the document size by
  the smallest row and ignores the fixed fields. Between 2,673 and 7,128 the identifier length
  and reasons decide. With 128-character identifiers and four eligibility reasons per row the
  capacity is 2,728. A one-reason excluded row fits 5,544, 5,111, 4,421 and 3,481 observations
  at 16, 32, 64 and 128 characters.
- A population above the ceiling is rejected before any derivation, which also bounds the
  quadratic training-by-validation comparison. Otherwise an exact check of the stored document
  runs before the output directory exists. Both fail with `development split output size limit
  exceeded`, distinct from the generic `document size limit exceeded`. Nothing is truncated,
  sharded or partially written, and the restored workspace is untouched.
- Inline v1 cannot reach this limit. The largest split row is at most 65% of the smallest valid
  observation with the same identifier length, so the split of an inventory that fit 1 MiB
  stays under 680 KB.
- For orientation, the M0 audit records 4,528 raw rows. The retained
  [capacity probe](../reports/m2-pipeline-capacity.md) builds such a population with the
  production builders, so the figures are reproducible. They describe synthetic rows, not the
  private data.
  With its `typical` mix at 16, 32 and 64 characters the complete split is 875, 947 and 1,092 KB,
  as the earlier one-off probe found, so the split exceeds its bound first at 64 characters.
  Production rejects that last document, so its size is the probe's fitted prediction. At 128
  characters the 4 MiB source bound fails before the candidate is built. The v2 candidate is 733,
  806 and 951 KB with 14-character source record identifiers. The earlier 719, 791 and 936 KB used
  the shorter unpadded `capture-<n>` identifiers of the test fixtures, and the candidate grows by
  one byte per character of that identifier for every observation. Lifting only the split limit
  would add at most 17% of capacity at these shapes, because the candidate and source limits bind
  just above it, so a release of that size needs a reviewed split transport and bounded source and
  lineage transport together, not in sequence, before real-data use. They change wire contracts and
  are outside this increment.

`DocumentSizeError` is a `ContractError` subclass with the unchanged
`document size limit exceeded` message. It lets code tell a size limit from a malformed
document without changing any existing handler.

## Failure handling

All metadata, including the output size, is validated before the output directory exists. The
reader repeats every check before it consumes a split.

| Condition | Result |
| --- | --- |
| Wrong expected release, policy or split reference; another release's evidence | Identity mismatch before any output |
| Unsupported release version; v1 release with a v2 payload or the reverse | Contract or integrity failure |
| Missing, altered, resealed, non-regular or oversized completion report | Never accepted |
| Altered, missing, extra or symlinked payload, source or inventory file | Integrity or path failure |
| Output path that is relative, traversing, symlinked, existing, or inside or around the restoration | Path failure; an existing output is preserved |
| Restored directory reached through a symlink alias (v2) | `INVALID_DIRECTORY` |
| Interrupted staging, write, sync or link | `FINALIZATION_FAILED`; no final split file |
| Split file missing, malformed, with a byte-order mark, oversized, symlinked or a FIFO | Not consumed |
| Resealed split with an omitted, duplicated, substituted or reclassified row | Population or assignment mismatch |
| Resealed split with different creation provenance | Fails the fixed expected split reference |

These are single-writer local filesystem operations. Messages carry fixed reason codes and
never paths or rows. Filesystem and digest checks are not a trusted resolver, and concurrent
hostile access and power-loss durability are not certified.

## Verification and remaining gates

Hand-written closed-form oracles and the v1 builder check the assignments for a 13-row policy
fixture, five boundary instants (including an offset), a 600-row long-identifier mix, a 1,500
row inventory above 1 MiB and a 3,000-row population whose split exceeds the bound. An actual
local DVC test restores an older 1,800-observation v2 revision after a newer one into two
independent fresh caches and compares the split bytes. See the
[task plan](../tasks/2026-11-07-m2-reference-splits/plan.md) and the
[development guide](../development.md#development-splits-from-reference-releases).

Membership consistency does not prove feature availability, training-only fitted
preprocessing, target-aggregate lineage, label quality, identity accuracy, authorized
evaluation or leakage freedom. Real use still needs authorized projection and handling,
defensible chronology or approved remediation, reviewed property evidence and policy, storage,
access, retention and quality decisions, a scalable split transport, isolated reproducible
execution and independent verification. A14 and the M2 exit gate remain open.
