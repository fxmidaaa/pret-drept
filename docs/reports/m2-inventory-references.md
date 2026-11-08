# M2 increment 6 — verified inventory references

2026-11-07, L1 engineering on `main` at `7f69b17`. The [task plan](../tasks/2026-11-07-m2-inventory-references/plan.md)
and [record](../tasks/2026-11-07-m2-inventory-references/task.json) identify the
scope, verification and recovery for this uncommitted review.

## Implementation

- Opt-in candidate and release v2 embed the closed observation inventory manifest.
  The logical digest still identifies the full ordered v1 observation population.
  The manifest and release roster additionally bind the exact Parquet bytes.
- Candidate rebuild compares every source envelope, record lineage, quality count
  and logical observation identity. Validation pins the canonical manifest before
  opening Parquet, then checks its physical integrity, schema and full population.
- The versioned DVC payload adds the canonical inventory manifest and Parquet file.
  Staging copies in bounded chunks and checks the copied bytes before installing
  the candidate. Local push rejects stale tracked content. Restore and readback
  require full verification, with a completion report installed only after recovery.
- The original v1 schema names, defaults and roster remain supported. At this checkpoint the
  split APIs required an inline v1 release; [increment 7](m2-reference-splits.md) replaced that
  gate. The [v2 design](../architecture/observation-inventory-references-v2.md)
  documents the public workflow and version boundaries.

## Verification

| Check | Result |
| --- | --- |
| Focused | 549 passed, including 31 new v2 cases |
| Actual local Git and DVC | 14 passed, including exact older v2 recovery of 1,800 observations and failures for corrupt, missing or stale content |
| Checkout | 875 passed, 12 private-model checks deselected, one existing deprecation warning |
| Extracted source and wheel | 680 passed each |
| Ruff, architecture, workflow, notebooks and frontend | Passed, including 38 frontend tests |
| Compatibility and preservation | Synthetic v1 documents and roster byte-identical to the starting revision. Both prior edits and all 18 verified implementation hashes preserved. |

The [verification record](../tasks/2026-11-07-m2-inventory-references/plan.md#final-verification)
records commands, the recovered interruption failure and exact recovery.
Linux CI for the uncommitted revision is unavailable. The increment is
`READY_FOR_REVIEW`.

## Limits and next increment

V2 still reconstructs source envelopes and lineage in memory under its 4 MiB
aggregate source cap and 1 MiB per-document limits. A larger supported Parquet
inventory can exceed the candidate limits. Version bounded source and lineage
transport if reviewed inputs require greater capacity.

Real use requires authorized projection and data handling, defensible observation
chronology or approved remediation, reviewed property evidence and policy, and
storage, access, retention and quality decisions. Local synthetic checks establish
artifact integrity and correspondence with declared facts. Isolated reproducible
training, feature and target-aggregate lineage, independent verification and
exact-artifact approval need their own evidence. A14 and the M2 exit gate remain open.

**Next increment.** Teach development split materialization to consume the verified
v2 inventory, with complete membership and parity with v1 on the same synthetic
observations. This completes the verified inventory-to-evaluation-input path before
baseline work.
