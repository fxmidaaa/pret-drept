# M2 increment 5 — observation inventory transport

The user approved Option A on 2026-11-07. This L1 increment is based on
`003ada8` on local branch `feat/m2-inventory-transport`. Scope, evidence and
recovery are recorded in the [task plan](../tasks/2026-11-07-m2-observation-inventory/plan.md)
and [task record](../tasks/2026-11-07-m2-observation-inventory/task.json).

## Implementation

The [v1 inventory design](../architecture/observation-inventory-v1.md) adds a
closed JSON manifest and typed Parquet file for observation metadata. The writer
accepts ordered v1 references, applies the shared population rules, and hashes
the same canonical bytes as the existing JSON inventory digest. Original
timestamp text, unknown chronology and identity, and JSON numeric distinctions
survive transport. The manifest separates the logical digest from file SHA-256
and size.

The optional pinned PyArrow backend writes batches under explicit limits.
Verification checks the two-file directory, expected logical reference, file
bytes, exact schema, metadata and full population before yielding records.
Manifest installation follows verified readback. A disposable local DVC fixture
exercises recovery from an exact synthetic Git revision through an empty cache.
The existing release and split APIs and the v1 DVC payload roster are preserved.

## Verification

Local implementation verification used CPython 3.13.16 and macOS ARM64. The synthetic
1,800-row inventory round-tripped with 1,796,401 logical JSON bytes and
1,373,881 physical Parquet bytes. The original 1 MiB JSON limit still applies.

| Check | Result |
| --- | --- |
| Focused contracts and I/O | 297 passed, including 74 new inventory cases |
| Actual local DVC | 12 passed, including fresh-cache inventory restoration |
| Checkout | 854 passed, zero failed or skipped, one existing Starlette/httpx warning |
| Extracted source and wheel | 649 passed each |
| Static, workflow, notebooks and frontend | All passed, including 38 frontend tests |
| Context and preservation | 13 fixed implementation hashes, 25 valid task records and both unrelated edits preserved |

The local evidence predates source publication. Interim failures, out-of-scope
checks and recovery commands are in the
[verification record](../tasks/2026-11-07-m2-observation-inventory/plan.md#verification-on-final-implementation).
The user approved the implementation at the second review and subsequently
requested source publication on `feat/m2-inventory-transport`. See the
[publication plan](../tasks/2026-11-07-m2-observation-inventory/plan.md#source-publication-follow-up).

## Next increment and prerequisites

The recommended next increment is a reviewed versioned candidate and release
reference to a verified inventory, initially exercised with synthetic data.
Split adoption follows the reference boundary. Real-data use requires approved
projection and handling, defensible observation chronology or remediation,
reviewed property evidence and policy, and storage, access, retention and
quality decisions. The [M0 audit](m0-alignment.md) and
[A14 handoff](a14-evaluation-handoff.md) explain the missing historical
timestamps and skipped detail refresh for known listings.

This increment verifies local transport integrity and correspondence with
declared metadata. Feature and target-derived lineage, isolated reproducible
training, and official development evaluations still need their own evidence.
The M2 exit gate remains open.
