# M2 increment 7 — development splits from reference-backed releases

2026-11-07, L1 engineering on `main` at `7f69b17`, layered on the uncommitted and still unreviewed
[increment 6](m2-inventory-references.md) by the user's explicit authorization. The
[task plan](../tasks/2026-11-07-m2-reference-splits/plan.md) and
[record](../tasks/2026-11-07-m2-reference-splits/task.json) identify the scope, verification and
recovery for this uncommitted review. The [design](../architecture/development-splits-reference-releases.md)
documents the rules and bounds.

## Implementation

- The split builder, validator, materializer and reader accept inline v1 and reference-backed v2
  releases. The `development-split` document, rules and ordering are unchanged. Release lineage is
  the only difference: `dataset_ref`, and so `split_digest`, name the release that supplied the
  population. Unsupported versions fail before any output exists. This replaces the increment 6 gate.
- `read_verified_restore_observations` returns the population from the same all-or-nothing restore
  verification. For v2 that pass has matched the exact Parquet bytes and population to the
  source-backed rebuild.
- An optional `max_inventory_records` keyword streams the identical inventory digest instead of
  requiring the whole canonical array to fit one document. The default keeps the v1 bound.
  `DocumentSizeError` lets code tell a size limit from a malformed document.
- Input and output limits are distinct. A 1,500-observation inventory has 1.40 MiB of logical JSON,
  which the legacy path rejects, and a 458 KB split. A population above 7,133 observations is
  rejected before derivation and any other oversized split before the output directory exists, with
  `development split output size limit exceeded`. At most 2,673 observations always fit.
- One increment 6 test of the old gate was replaced by a test that rejects unsupported versions. All
  other existing evaluation, split, release and inventory tests pass unmodified.

## Verification

| Check | Result |
| --- | --- |
| Focused | **637 passed**, including 88 new cases |
| Actual local Git and DVC | **20 passed**, including six new cases: v1 and v2 parity through actual restores, an older 1,800-observation v2 revision restored after a newer one into two independent fresh caches with identical split bytes, and damaged or mis-referenced restorations |
| Checkout | **969 passed**, **12 private-model checks deselected**, 1 existing Starlette/httpx warning |
| Extracted source and wheel | **768 passed each** |
| Ruff, format, architecture, workflow, notebooks, frontend, installed dependencies | Passed: 57 formatted files, **38 frontend passes** and 59 compatible packages |
| v1 compatibility | The synthetic v1 release, pure split, materialized split file and memberships are byte-identical to the same inputs run through the saved increment 6 source |
| Failure handling | Eleven deliberate regressions of the safety properties were each caught by the new tests |
| Preservation | HEAD, branch and the empty index are unchanged, both unrelated edits are byte-identical, and every file outside the recorded edits equals its starting or increment 6 bytes |

Two interim failures were recovered or recorded: a measuring helper in the capacity test, and one
unexplained transient DVC process failure that did not recur in eight later runs. The
[final verification](../tasks/2026-11-07-m2-reference-splits/plan.md#final-verification) records
commands, the failures, the skipped and unavailable checks, and exact recovery. Linux CI for the
uncommitted revision is unavailable. The increment is `READY_FOR_REVIEW`.

## Limits and next increment

The complete split is one 1 MiB JSON document, so at most 2,673 observations always fit and none
above 7,128 can. At the M0-documented 4,528 raw rows, a synthetic probe with the production
builders showed the split exceeding its bound first as identifiers lengthen, with the 4 MiB source
cap following. See the [design](../architecture/development-splits-reference-releases.md#input-limits-and-the-output-limit).
No frozen architecture decision conflicts with the bound, since specification §12.2 treats JSON and
Parquet as selected defaults, but a real release of that size needs a larger transport.

Real use also requires authorized projection and data handling, defensible chronology or approved
remediation, reviewed property evidence and policy, and storage, access, retention and quality
decisions. Local synthetic checks establish artifact integrity and correspondence with declared
facts. Isolated reproducible training, feature and target-aggregate lineage, independent
verification and exact-artifact approval need their own evidence. A14 and the M2 exit gate remain open.

**Next increment.** Design, review and implement a versioned typed (Parquet) split-membership
artifact with a streaming verifier and the same rules, so a complete split is no longer one 1 MiB
JSON document. It changes the split wire contract, so it is L2 under specification §6.2: a formal
plan, a threat and risk assessment, explicit approval and independent verification. Bounded source
and lineage transport for v2 candidates follows. Both stay synthetic until real data is authorized.
