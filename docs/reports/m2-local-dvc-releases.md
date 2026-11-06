# M2 increment 3 — development releases and local DVC restoration

Date: 2026-11-06. Approved Option A, L1 engineering. Branch
`feat/m2-local-dvc-releases`, unchanged base HEAD `d920ffc`. This is one increment,
not completion of M2. See the [persistent plan](../tasks/2026-11-06-m2-local-dvc-releases/plan.md),
[record](../tasks/2026-11-06-m2-local-dvc-releases/task.json) and
[contract design](../architecture/dataset-releases-v1.md).

## Implementation

Two additive public contracts describe sealed **development candidates** and local
restoration evidence. A release binds the full candidate/source/quality lineage,
actual Git metadata commit, native DVC MD5 object, independent SHA-256 artifact
roster, schema, acquisition/transform/policy provenance and pending retention.
Manifest construction follows the metadata commit, avoiding a digest cycle.

Pure release helpers, bounded exclusive payload IO and the pinned public-CLI adapter
remain separate modules in `rent_data`. New output workspaces get their own config,
local copy-based cache and explicit filesystem store. Actual DVC recovery is followed
by SHA-256 checks and full source-backed candidate reconstruction before an atomic,
non-overwriting completion marker. Readers require that marker and revalidate bytes.
Existing interfaces and prior uncommitted work are preserved.

DVC 3.67.1 and its dependency closure are separately hash-locked, with an explicitly
bootstrapped locked setuptools backend for the ANTLR source build. ML/runtime locks
are unchanged. Packaging includes self-contained core tests; checkout CI additionally
installs the separate tooling and runs actual local DVC integration. No repository
commit/push, real-data operation, experiment, policy activation or deployment is part
of this work.

Source publication follow-up: the user subsequently requested **"push please"**,
authorizing commit/push of the reviewed source and increment-2 dependency on
`feat/m2-local-dvc-releases`. Earlier no-publication statements describe the
implementation phase. The two unrelated reporting edits remain local. Current
publication progress and exact recovery are in the task's
[publication follow-up](../tasks/2026-11-06-m2-local-dvc-releases/plan.md#source-publication-follow-up).
No data publication, merge, experiment or deployment is authorized by this request.

## Verification

Locally **READY_FOR_REVIEW**. Final checks ran on CPython 3.13.16/macOS ARM64;
source, schemas, tests, locks and workflow stayed unchanged afterward.

| Check | Result |
| --- | --- |
| Separate tool installation | Fresh pip install/build passed; DVC 3.67.1, setuptools 82.0.1, 97 active pins checked from the 99-pin universal lock; `pip check` passed |
| Focused core/CI tests | 115 passed |
| Full checkout | **690 passed**, zero failed/skipped; includes 10 actual local DVC integration cases and existing synthetic-request model regressions; one existing Starlette/httpx warning |
| Extracted source / installed wheel | **487 passed each**, including all 15 schemas; no editable-checkout imports |
| Frontend / notebooks | 38 tests passed / two tracked notebooks passed |
| Ruff, format, architecture, actionlint | All passed; checker and effective policies unchanged |
| Documentation/preservation | 167 baseline files accounted for; 155 byte-identical plus 12 precisely scoped edits, 17 new files, all 20 implementation hashes unchanged; prior implementation and both unrelated edits preserved; task records/links/whitespace/Git state checked |

Real integration restored A after B from an independent empty consumer cache and
rejected unavailable/corrupted objects, incorrect identities and unsafe states.
Unit checks cover source/report reconstruction, population/provenance contradictions,
unsupported metadata/remote overrides, paths/symlinks/FIFOs, process failure/timeout
and interrupted completion writes. No real-data experiment was run.

Earlier fixture failures (a `target` substring assertion and read-only copied DVC
objects) were corrected before final checks. The [task verification](../tasks/2026-11-06-m2-local-dvc-releases/plan.md#verification--final-implementation)
records exact commands, logs, failed/passed/skipped/unavailable checks and recovery.
Linux CI for this uncommitted revision and protected/production verification are
unavailable; source publication requires separate authorization. Real-data/publication,
ML/feature-lineage and runtime checks were skipped as outside scope, with prerequisites
recorded. Prior milestone/PR passes do not certify this working tree.

## Limits and next increment

This small JSON transport preserves metadata, not the referenced raw source itself,
and retains the existing 1 MiB limits. A sealed candidate is not a published dataset,
retention approval or authorized input to a trusted runner. Local SHA checks and a
report are development evidence, not host isolation, authenticated attestations or
proof that features/evaluations are leakage-free. No production remote/access or
garbage collection policy is chosen. M2's reproducible-run/development-evaluation
exit gate and A14's benchmark work remain open.

The **single recommended next increment** is a deterministic development-split
materializer that consumes a verified sealed metadata release plus an explicitly
reviewed policy and produces the existing development-split contract. Start with
synthetic releases, fixed complete membership/exclusions and temporal/property/
population negative tests; do not start model training in that increment.

Before it can use real data, review eligibility/cutoff/unseen-property and projection
policies; supply authorized defensible chronology or approved remediation and reviewed
property pairs/identity policy; approve permitted input handling plus storage/access/
retention/quality requirements; and design scalable inventory transport. M0's
historical CSV has no observation timestamps; present source dates and the scraper's
known-listing behavior do not repair that history. No times, matching thresholds,
identities or benchmark results are inferred by this implementation.

## Source publication

The user's subsequent **"push please"** request was fulfilled on
[`feat/m2-local-dvc-releases`](https://github.com/fxmidaaa/pret-drept/tree/feat/m2-local-dvc-releases).
The dependency is [4ad339e](https://github.com/fxmidaaa/pret-drept/commit/4ad339edc5bd7b6cebbfbe766d3ca0dd7b5350e4);
release source is [0c23de6](https://github.com/fxmidaaa/pret-drept/commit/0c23de6ee8aa78043ef44ec6a5ed93c8a51e07d5).
The remote feature ref matched that exact source SHA after push. No force push,
change to `main`, new PR, merge or data publication occurred. Both unrelated
report-consistency edits remain local and byte-identical.

[Linux CI 42190500570](https://github.com/fxmidaaa/pret-drept/actions/runs/42190500570)
passed for that exact source SHA: **678 passed / 12 private-model skips**,
**487 tests per distribution**, **38 frontend passes**, and the remaining static,
architecture, workflow, notebook and separate DVC installation/integration checks.
The private model is absent in CI; no fake model or training hides its skips. Linux
CI is now available for this source; earlier unavailable/no-publication statements
describe the implementation checkpoint. Protected/real-data/M2 gates remain open.

The bounded source task is **COMPLETED** after user review and source publication.
This documentation follow-up records that evidence; resolve the feature branch's
actual HEAD for its latest commit/CI. Exact publication verification and recovery
are in the [task](../tasks/2026-11-06-m2-local-dvc-releases/plan.md#publication-verification).
