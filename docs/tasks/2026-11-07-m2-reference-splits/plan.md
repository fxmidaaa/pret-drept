# M2 increment 7 — development splits from reference-backed releases

## Scope and starting state

L1 engineering under [§6.2](../../architecture/specification-v1.md#62-risk-classification).
The [request](request.md) lets development split materialization and readback consume
verified v2 releases from [increment 6](../2026-11-07-m2-inventory-references/plan.md).

**Classification.** §6.2 lists split methodology changes as L2. This increment changes no
partition, exclusion, cohort, boundary or property-matching rule, no schema, policy or wire
contract, and no protected data access, security boundary, CI privilege or promotion
path. It changes where the verified observation population comes from and how a large
population is bounded. Parity tests against the unchanged v1 flow and a hand-written
closed-form oracle support that reading. The shared rules live in `rent_contracts.evaluation`,
so a reviewer who judges the additive opt-in limit to be a methodology change should
reclassify this work as L2 and require the formal plan, threat assessment and independent
verification that level needs. Nothing here activates policy or approves real data.

**Starting state.** Branch `main`, HEAD `7f69b177222e3fde58cd070e05228d81cc56539f`, index
empty. The working tree held the uncommitted, unreviewed increment 6 (19 scoped edits, 9
additions) and both unrelated report-consistency edits, whose SHA-256 values are unchanged:

| File in `docs/tasks/2026-11-05-audit-report-consistency/` | SHA-256 |
| --- | --- |
| `plan.md` | `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2` |
| `task.json` | `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6` |

The session first stopped at the user's review gate. The user then replied "Authorize
building" (see the [authorization record](request.md#authorization-record)). Because both
increments edit the same files, the exact increment 6 bytes were saved outside the
repository before the first edit: a tracked patch (SHA-256
`853762cc06eeadb798d6d3655e0c3ef27ca5ebde5a215ff658c748d2717c99a6`), copies of all 30
touched files and a manifest (SHA-256
`458e99aab0119d894fc6f8221c797cc89aa80d6ee4505a88e80b61789b626cca`). The recorded increment 6
review proof passed against those bytes immediately before the first edit.

## Design and requirements

The split document stays the existing closed `development-split` v1 contract. The sealed
release version selects only where the complete verified population comes from and which
inventory bound applies. The [design](../../architecture/development-splits-reference-releases.md)
has the full rules. In short:

- `build_development_split`, `validate_release_split`, `materialize_development_split` and
  `read_verified_development_split` accept inline v1 and reference-backed v2 releases.
  Unsupported versions fail release validation before any output exists. The increment 6
  gate that rejected v2 is replaced.
- `read_verified_restore_observations` returns the population from the same all-or-nothing
  verification as `read_verified_restore`. For v2 that pass already matched the exact
  Parquet bytes, schema and population to the source-backed rebuild.
- `rent_contracts.evaluation` gains an optional `max_inventory_records` keyword on
  `observation_inventory_digest`, `derive_development_memberships` and
  `validate_development_split`. Its default is the legacy single-document bound. A given
  limit streams the identical canonical-array digest through the existing hasher. One shared
  rule implementation serves both versions.
- The complete split stays one 1 MiB canonical JSON document. A population above the
  7,133-row ceiling (the smallest derivable row) is rejected before derivation. Any other
  oversized split fails an exact size check before the output directory exists, with
  `development split output size limit exceeded`. `DocumentSizeError` makes size limits
  distinguishable from other contract errors and keeps every existing handler working.
- Release lineage is version-specific. `observations_digest` and all memberships are equal
  across versions for equal observations. `dataset_ref` and `split_digest` differ, and a split
  presented under the other version's release fails.

## Alternatives considered

- Re-deriving membership inside `rent_data` for large populations avoids touching the
  contract module but duplicates the rules and invites drift. Rejected.
- Raising the 1 MiB default would silently change v1 behavior. Rejected.
- A Parquet or sharded split, or a new split schema, removes the output bound but is a
  wire and methodology change (L2) and needs its own review. It is the recommended next step.
- Separate v2-only entry points duplicate the verified flow. Dispatch on the validated
  release version keeps one flow and fails closed on unknown versions.
- Reading rows from the Parquet file instead of the source rebuild would add a second
  consumer of the same bytes. Increment 6 made the source rebuild authoritative and verifies
  the inventory in the same pass, so this increment adds no second reader.

## Acceptance criteria and implementation plan

1. v2 releases flow through restore verification, split materialization and readback with the
   existing contracts. v1 behavior is unchanged: every existing evaluation, split, release and
   inventory test passes unmodified apart from the single increment 6 test of the old gate.
2. For identical synthetic observations and policy, v1 and v2 yield identical memberships,
   reasons and cohorts, checked against hand-written oracles. They differ only in release
   lineage, and cross-version substitution fails.
3. A v2 inventory above the legacy 1 MiB logical JSON limit materializes and reads back. A
   complete split above its output bound is rejected before any directory, file or temporary
   exists, and the constraint and its capacity numbers are documented and tested.
4. Wrong expected references, missing or tampered inventory and restoration evidence, unsafe
   paths and incomplete or interrupted outputs fail safely without partial acceptance or leaked
   paths.
5. An actual local DVC run through a disposable synthetic Git repository and local store
   restores an older revision into independent fresh caches and produces identical splits.
6. Documentation, task evidence and packaging are complete. The focused, DVC, checkout,
   architecture, static, and source/wheel checks run after the final implementation edit.
   Stop at `READY_FOR_REVIEW`, uncommitted, with nothing pushed.

Plan: save the increment 6 bytes; read the records and code; implement the contract limit
and `DocumentSizeError`, the verified population, version dispatch and output bound; add a
shared patterned fixture and the foundation, parity, bound, failure and DVC tests; update
the design, guide, reports and this record; review the diff; run every check.

## Verification and recovery

Run the commands in the [development guide](../../development.md#development-splits-from-reference-releases)
with the pinned local CPython 3.13.16, PyArrow 26.0.1, DVC 3.67.1, actionlint 1.7.12 and Node 24.21.0.
Use `-p no:cacheprovider` and an owned `--basetemp` for every pytest run. Run the checkout suite with
`-m 'not legacy_artifact'` to stay inside the synthetic scope. The saved increment 6 bytes, the
starting fingerprints, the compatibility and preservation scripts and the logs are under
`/private/tmp/claude-501/-Users-rcimendur--claude-spares-spare-MjnXeb/75b3cda2-a626-4a56-87bc-f9597ee36988/scratchpad`.
That folder is session-local. If it has expired, reconcile the tree and rerun the guide's checks:

```bash
git rev-parse HEAD                      # 7f69b177222e3fde58cd070e05228d81cc56539f
git branch --show-current               # main
git diff --cached --name-only           # empty
git diff --check
shasum -a 256 docs/tasks/2026-11-05-audit-report-consistency/plan.md docs/tasks/2026-11-05-audit-report-consistency/task.json
.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_repository_tasks.py tests/foundations/test_tasks.py
```

Compare the two hashes with the table above. The increment 6 bytes cannot be rebuilt from `HEAD`
alone, so keep that folder until increment 6 is reviewed. With it present, these reproduce the proofs:

```bash
SNAP=/private/tmp/claude-501/-Users-rcimendur--claude-spares-spare-MjnXeb/75b3cda2-a626-4a56-87bc-f9597ee36988/scratchpad/inc6-snapshot
shasum -a 256 -c "$SNAP/inc6-files.sha256"          # fails only for the files increment 7 edited
PYTHONPATH="$PWD/src" .venv/bin/python -P /private/tmp/claude-501/-Users-rcimendur--claude-spares-spare-MjnXeb/75b3cda2-a626-4a56-87bc-f9597ee36988/scratchpad/check_increment7.py "$SNAP" READY_FOR_REVIEW
PYTHONPATH="$SNAP/baseline/src:$PWD/tests" .venv/bin/python -P /private/tmp/claude-501/-Users-rcimendur--claude-spares-spare-MjnXeb/75b3cda2-a626-4a56-87bc-f9597ee36988/scratchpad/check_split_compatibility.py "$SNAP/baseline/src" > "$SNAP/before.json"
PYTHONPATH="$PWD/src:$PWD/tests" .venv/bin/python -P /private/tmp/claude-501/-Users-rcimendur--claude-spares-spare-MjnXeb/75b3cda2-a626-4a56-87bc-f9597ee36988/scratchpad/check_split_compatibility.py "$PWD/src" > "$SNAP/after.json"
cmp "$SNAP/before.json" "$SNAP/after.json"        # v1 artifacts byte-identical
```

Retry a failed restoration or split in a fresh owned destination. Exact Linux CI for this working
tree awaits a separately authorized source publication.

## Maintainer review

Reading the final diff against the saved increment 6 bytes, and running it, found six issues. All were fixed before the final run.

- `derive_development_memberships` re-hashed and re-validated the whole population when a record
  limit was given, only to discard the digest. The pass now runs only on the legacy path.
- The design first said a v1 split stays under 60% of its inventory. Measuring every identifier
  length gives at most 65%, so the split of a 1 MiB inventory is under 680 KB. The conclusion stands
  and the number is corrected.
- The design presented 7,133 as the largest population that can fit. Exact capacity is 7,128 and
  7,133 is a shortcut. Both are documented and the capacity test asserts every figure the design cites.
- The capacity test first measured an over-limit document with the canonicalizer that rejects it. It
  now asserts the exact limit error.
- A projection test aliased its fixture and two tests duplicated manifest construction. Both were simplified.
- The increment 6 report still said the split APIs require v1. It now points to this increment.

A mutation pass on a scratch copy broke the safety properties on purpose. All eleven regressions
were caught by the new tests: the legacy bound for v2, a readback that forgets the limit, an
unclassified or unchecked output size, a removed ceiling, a ceiling applied to v1, an output
directory created before verification, an unsorted stream, a boolean limit, an indistinguishable
size error and an ignored inventory.

Not changed: the pure builders trust a self-consistent, externally pinned release's declared counts,
as before, and the I/O path verifies all bytes first. Derivation still compares training and
validation rows pairwise, and the ceiling bounds that work. Both reference formats use owned
immutable local inputs per operation. Hostile concurrent mutation and crash durability still need
separate enforcement or evidence.

## Final verification

The final checks ran after the last implementation, test and package edit on CPython 3.13.16,
Darwin ARM64, PyArrow 26.0.1, DVC 3.67.1, actionlint 1.7.12 and Node 24.21.0. Only disposable
synthetic repositories and local stores were used. The project index and branch tip stayed unchanged.

| Status | Check | Evidence |
| --- | --- | --- |
| Passed | Focused candidate, inventory, release, evaluation, split and architecture tests | **637 passed**, including 88 new cases for parity, bounds, wrong references, damaged evidence, unsafe paths and interrupted outputs |
| Passed | Actual local Git and DVC | **20 passed**, including six new cases through a disposable synthetic repository and independent fresh caches |
| Passed | Checkout regression | **969 passed**, **12 private-model checks deselected**, 1 existing deprecation warning |
| Passed | Source and wheel | **768 passed per distribution**, including the new foundation module |
| Passed | Static, workflow, notebooks, frontend and installed dependencies | Ruff and format for 57 files, architecture, actionlint, two notebooks, **38 frontend passes** and 59 compatible packages |
| Passed | v1 compatibility | The v1 release, pure split, materialized split file (3,178 bytes) and memberships are byte-identical before and after. Every existing evaluation, split, release and inventory test passes unmodified |
| Passed | Preservation | HEAD, branch and empty index unchanged. Both unrelated edits byte-identical. The increment 6 files this increment edited, the five other edited files and the six added files match the recorded lists exactly |
| Passed, not required | Mutation sanity | Eleven deliberate regressions were each caught |
| Passed, not required | Hash-seed determinism | In fresh interpreters with `PYTHONHASHSEED` 1, 97 and 4242, a separately staged v2 release and its split gave identical bytes (split SHA-256 `544c4ba23ca2088f34b8840f964ce5e7e8d0ddf576934caf8e6e8e3a84a1433e`). This ad hoc check is not retained in the repository |
| Failed, recovered | Interim capacity-test helper | The first focused run failed one test that measured an over-limit document with the canonicalizer that rejects it. It now asserts the exact limit error |
| Failed, not reproduced | Interim DVC process failure | One first run of the six new DVC cases failed once with `PROCESS_FAILED` in the older large release case. The leftover disposable repository shows revision B was tracked but not yet staged and no consumer existed, so a `dvc add` tail or `git add` subprocess exited nonzero before any code from this increment ran. The adapter discards tool stderr by design, so the cause is unknown. The failing case passed in eight later runs, seven of them with all six new cases and six with a throwaway plugin that captures subprocess stderr. None logged an error. The final standalone and checkout DVC runs passed. If it recurs, rerun in a fresh workspace and capture stderr |
| Failed, recovered | Interim preservation check | The first run of the preservation script stopped at its own expected-set assertion, not at a tree change. It compares with increment 6's start-of-work hashes, in which the two unrelated edits already existed, but its expectation counted them as changes. The expectation was corrected and the unchanged tree passed: 12 increment 6 files edited, five other tracked files edited and six added |
| Skipped | Private-model checks and work outside this increment | The 12 model-dependent regressions were deselected. Baseline training, real data, protected labels, publication and promotion are out of scope |
| Unavailable | Exact-tree Linux CI, protected verification and the M2 exit gate | A later authorized source publication enables exact-revision CI. Real-data and official evaluation need approved input handling, defensible chronology, reviewed property evidence and policy, storage and retention decisions, a scalable split transport, and isolated reproducible execution with independent evidence |

## Review handoff

The bounded increment is `READY_FOR_REVIEW` on `main` at `7f69b17`, uncommitted with an empty index,
layered on increment 6, which is still unreviewed. See the
[increment report](../../reports/m2-reference-splits.md). The single next increment is a versioned,
typed split-membership artifact with a streaming verifier, because a complete split is one 1 MiB
document. It changes the split wire contract, so it is L2.
