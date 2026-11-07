# M2 increment 5 — observation inventory transport

## Risk and starting state

L1 engineering. This is an additive data artifact and a development dependency.
Eligibility, split methodology, data access, and trusted policy remain governed
by the frozen specification. The [approved request](request.md) covers only
Option A. Existing JSON releases and development splits continue to use v1.

Started on `feat/m2-development-splits` at
`003ada8b79e7e45c1b4cfab71bf776425ac11103`, matching its local upstream ref,
and created `feat/m2-inventory-transport` at the same HEAD. The index was empty.
Captured 193 tracked/nonignored file hashes and the starting diff/status under
`/private/tmp/pret-drept-m2-inventory-i3anr50v`. Preserve the prior edits to
`docs/tasks/2026-11-05-audit-report-consistency/{plan.md,task.json}` byte-for-byte.

| Existing file | Starting SHA-256 |
| --- | --- |
| `plan.md` | `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2` |
| `task.json` | `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6` |

The [frozen specification](../../architecture/specification-v1.md) separates
observation, property, release and split identities in §9 and selects typed
Parquet plus versioned JSON in §12.2. The [M0 audit](../../reports/m0-alignment.md)
and [A14 handoff](../../reports/a14-evaluation-handoff.md) document the missing
historical observation times, skipped refreshes for known listings and
target-dependent legacy evaluation filters. Preserve declared observations,
including unknown chronology and unresolved identity. No real-data projection,
matching, policy, acquisition, experiment, access, publication, or deployment
action is authorized by this record.

## Implementation plan

1. Preserve the public v1 JSON behavior in `rent_contracts.evaluation` while
   sharing row/population rules with a strictly ordered incremental digest.
2. Add a closed inventory manifest schema with independent logical and physical
   identities and a fixed file name. Keep Parquet-specific code and the optional
   backend in `rent_data`.
3. Encode every v1 field losslessly. Verify file size and bytes, exact schema,
   count, semantic population and digest under explicit bounds. Require an
   independently supplied expected logical digest at read time. Create the
   completion manifest atomically after successful readback. Document local
   filesystem and memory assumptions.
4. Pin PyArrow 26.0.1 with wheel hashes in the development lock and declare the
   optional `parquet` extra. Preserve all existing pins and the separate DVC
   environment. Check the installed wheel and dependency closure.
5. Exercise the codec with handwritten synthetic oracles, adversarial failures,
   larger-than-JSON inventory and isolated process checks. Verify actual local
   DVC restoration through a disposable fixture and fresh cache using its exact
   synthetic Git revision. Preserve the production v1 payload roster.
6. Run the focused and aggregate [development checks](../../development.md)
   after implementation edits. Record exact results, preserve both existing
   edits, validate task context and stop uncommitted for the second review.

## Acceptance criteria

- The existing fifteen schemas, v1 public behavior, legacy interfaces and JSON
  bounds remain intact. The added manifest is bounded, closed and versioned.
- Lossless row semantics and exact v1 logical digest match for small inputs,
  across batches and interpreters. At least one inventory exceeds 1 MiB of
  logical canonical JSON and round trips without changing that legacy bound.
- Duplicate observations, duplicate listing captures and conflicting confirmed
  properties fail across batch boundaries. No inferred chronology, target
  fields or eligibility selection enter the inventory.
- Malformed schema/metadata, tampering, wrong expected identity, limits, unsafe
  paths and failed writes yield safe errors. An existing output stays unchanged.
  A successful write publishes its manifest only after verified readback.
- Synthetic Git/DVC add, push and pull preserve complete bytes and inventory
  identity with an independent empty cache. Production v1 restoration behavior
  stays intact.
- Persist passed, failed, skipped and unavailable checks with exact recovery
  actions. Stop for second review with a proposed commit message and M2 open.

## Verification and recovery

Planned evidence includes focused contracts/IO, isolated process and synthetic
DVC checks, full checkout tests, extracted source/wheel, Ruff, architecture,
workflow, notebook, frontend and task/preservation checks. Store logs outside
the checkout. Use the active [task record](task.json) for current state.

Reconcile `git status --short --branch`, HEAD, index and the snapshot before
resuming. Use the locked development and separate DVC setup in the development
guide. Retry a failed synthetic write in a fresh destination and preserve
existing artifacts. Compare any resumed changes with the saved start hashes.

## Verification on final implementation

Environment was CPython 3.13.16 on macOS ARM64, PyArrow 26.0.1, DVC 3.67.1,
actionlint 1.7.12 and Node 24.21.0. The 1,800-observation synthetic fixture
produced 1,796,401 canonical JSON bytes and 1,373,881 Parquet bytes. The
legacy digest rejected the aggregate JSON size while the new digest matched the
independent canonical-byte oracle. DVC restored the Parquet and 449-byte
manifest exactly from committed synthetic metadata in a fresh consumer cache.

| Status | Check | Evidence and recovery |
| --- | --- | --- |
| Passed | Focused inventory, evaluation, release I/O and split checks | 297 cases, including 74 new inventory cases and 223 existing checks. Run the focused commands in the [development guide](../../development.md#observation-inventory-transport). Cases include exact numeric/time round trips, invalid schemas and manifests, bounds, interruption, stable digest, cross-batch conflicts and safe errors. |
| Passed | Actual local Git/DVC integration | 12 cases including the inventory above the legacy bound, exact metadata revision, empty independent cache, both file hashes, logical digest and unchanged producer bytes. Restore setup via the [separate data tools](../../development.md#separate-local-data-tools) and rerun the integration file. The v1 release roster rejects the inventory layout. |
| Passed | Locked backend and dependencies | uv 0.13.1 resolved one package from the public PyPI index for Python 3.13, using `--universal --generate-hashes --only-binary pyarrow`. The lock has 50 wheel hashes and no PyArrow runtime dependencies. The local macOS ARM64 wheel installed with `--require-hashes --no-deps --only-binary :all:`. Offline uv and bundled pip lock dry runs, dependency check and editable reinstall passed. |
| Passed | Full checkout | 854 passed, zero failed or skipped. Existing private-model checks used their synthetic requests. One existing Starlette/httpx deprecation warning. Run `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` with the locked setup. |
| Passed | Extracted source and wheel | 649 tests each from `.venv/bin/python scripts/check_distribution.py`, including the new manifest schema and codec. Each run bypassed the checkout editable import. |
| Passed | Static, workflow, notebooks and frontend | Guide commands passed Ruff and format (54 files), architecture, actionlint, two tracked notebook checks and 38 Node tests. |
| Passed | Task, documentation and preservation | 193 starting files accounted for with 183 byte-identical, ten scoped edits and ten added paths. Both unrelated edits, all 15 original schemas, existing dependency pins, v1 DVC roster and frozen architecture verified byte-for-byte. 13 implementation/package/test hashes frozen and 25 task records validated. Local links, whitespace, unchanged HEAD and empty index checked. |
| Failed, recovered | Interim setup and test passes | uv's default cache was unwritable. Set `UV_CACHE_DIR` to the task-owned cache. The tool venv has no pip entry point, so run pip from the Python-bundled wheel with `--no-cache-dir --no-index --require-hashes --dry-run` for the lock syntax check. An early integration test was inserted before the previous test's end. Move the new test below the unchanged prior body, rerun Ruff and actual DVC. An interim footer-metadata fixture produced no metadata with `store_schema=False` (295 passed, one failed). Write actual footer keys via `ParquetWriter.add_key_value_metadata`, then rerun the focused suite. The first aggregate shell wrapper used zsh's reserved `status` variable after the commands completed. Use `inventory_check_rc` or a conditional shell block to preserve real exit codes and rerun against the review tree. |
| Skipped | Real-data work, UI smoke, acquisition, features/labels, experiments, data publication and protected operations | This scope uses synthetic metadata and has no UI change. Review scope separately before real-data work. Provide approved handling/projection and eligibility/identity policy, defensible chronology or remediation, reviewed property evidence, and storage, access, retention and quality decisions. Feature availability and target-derived lineage need isolated, independently checked execution. |
| Unavailable | Linux CI for this review tree, independent runtime/real-data verification and M2 exit gate | Obtain second review and a separate source publication instruction, then verify Linux CI at the exact published SHA. External owners must resolve the real-data and protected prerequisites before official development benchmarks and acceptance. |

The relevant aggregate commands are in [development and verification](../../development.md).
Focused and aggregate logs, the baseline diff and hashes, and the preservation
checker are under `/private/tmp/pret-drept-m2-inventory-i3anr50v`. For recovery,
run the guide checks with `PYTHONDONTWRITEBYTECODE=1`, task-owned Matplotlib and
Numba cache directories, and disposable pytest roots. Re-run after the evidence
update with the implementation hashes fixed and confirm all task records, links
and working-tree preservation. Use `check_context.py READY_FOR_REVIEW` in the
evidence directory from the repository root with `PYTHONPATH="$PWD/src"` and the
development Python. If the temporary directory has expired, compare each scoped
path to HEAD, confirm both pre-existing SHA-256 values above, validate task context
and rerun the relevant commands with new temporary storage.

## Review handoff

The uncommitted 20-file increment was presented for the second review. The
starting HEAD and the two unrelated local reporting edits were preserved. See the
[inventory design](../../architecture/observation-inventory-v1.md) and
[summary](../../reports/m2-observation-inventory.md). The proposed commit message
is `feat(data): add verified Parquet observation inventory transport`.

## Second review approval

On 2026-11-07 the user replied “approved.” to the implementation review.
The local L1 engineering task is complete. All 203 paths matched the review
snapshot before recording approval, and all nine final check groups had zero
exit status. The four approval documents are the only follow-up edits. The
reviewed implementation and both unrelated edits are preserved.

The increment remains uncommitted on `feat/m2-inventory-transport` at `003ada8`.
Source publication requires a separate instruction and Linux CI for the
published revision. The review covers the synthetic inventory increment.

For recovery, reconcile the current tree with `review-files.json` in the
evidence directory and allow only the four approval document edits. Run
`check_context.py COMPLETED` using the same setup as above and
`.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_repository_tasks.py tests/foundations/test_tasks.py`.
The documentation follow-up check output is stored in `approval-checks.log`.

## Later work

Introduce reviewed reference-based candidate/release adoption of the verified
inventory, then adopt those references in development split materialization,
then build reproducible isolated baseline/feature-lineage execution and the
development comparisons. Before real-data use, require authorized and reviewed
projection, chronology or remediation, property evidence and policy, and
storage/access/retention/quality decisions. Isolation and independent evaluation
evidence are separate gates.

## Source publication follow-up

On 2026-11-07, after the second review, the user requested “push please”.
Publish the approved 20-path increment on `feat/m2-inventory-transport` using
the proposed title. The local approval section records the state before this
instruction. Publication covers the reviewed code and the associated evidence
documents on this feature branch. Real-data and protected gates remain separate.

All 203 files matched the approval snapshot at the start of publication.
The destination branch did not yet exist at origin. The pre-publication
diff, status and hashes are under
`/private/tmp/pret-drept-m2-inventory-publish-509w1mbt`. The 13 verified
implementation hashes and two unrelated local edits must match throughout.

Check task context, links, workflow semantics, notebooks and whitespace.
Stage only the 20 scoped files and verify their indexed bytes. Commit and
push to the explicit feature ref, then independently confirm the remote SHA
and Linux CI for that exact push. Record the observed source and CI evidence
and verify the documentation follow-up revision.

For recovery, reconcile branch, HEAD, index, remote and the saved snapshot.
After a source commit, use its parent and content proofs in place of the
pre-commit HEAD check. Preserve commits on a failed push, check the remote
ref and retry the affected operation after diagnosis. For CI failures,
inspect the exact revision's failed step and record the recovery before
claiming a pass. Keep both unrelated edits out of the index.
