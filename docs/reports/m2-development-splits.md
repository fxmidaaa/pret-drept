# M2 increment 4 — deterministic development splits

Date: 2026-11-06. Approved Option A, L1 engineering; branch
`feat/m2-development-splits` at base `e56c115`. Implement only this increment and
stop uncommitted for the user's second HITL. See the
[plan](../tasks/2026-11-06-m2-development-splits/plan.md),
[record](../tasks/2026-11-06-m2-development-splits/task.json) and
[design](../architecture/development-splits-v1.md).

## Implementation

One public helper derives existing v1 membership/exclusion/cohort semantics and is
shared with validation. The pure data builder binds the expected sealed release,
complete inventory, expected policy and explicit temporal/creation provenance into
the existing split contract. Generated ordering is deterministic; prior valid
ordering remains accepted. No new schema, dependency, selector or rule is added.

Local I/O rechecks a restored release's report, bytes and source-backed candidate,
creates a separate new split artifact atomically, and revalidates expected release,
policy and split identities on readback. Restoration and split output share the
same extracted atomic create-without-replacement primitive. The restored workspace,
prior output and both unrelated reporting edits are preserved.

Publication follow-up: the user subsequently requested **"push please"**, authorizing
source commit/push on `feat/m2-development-splits`. Earlier uncommitted/second-review
statements describe the implementation checkpoint. The
[publication plan](../tasks/2026-11-06-m2-development-splits/plan.md#source-publication-follow-up)
records current scope and recovery. Both unrelated edits stay local; no merge, new
PR, data publication or experiment is included.

## Verification

Locally **READY_FOR_REVIEW** on CPython 3.13.16/macOS ARM64. Final source checks
ran after the last implementation/test/package edit; all 11 implementation hashes
remain unchanged through the evidence update.

| Check | Result |
| --- | --- |
| Focused builder/I/O/evaluation/restoration | **223 passed**: 49 new builder cases, 39 new I/O cases, 114 unchanged evaluation cases, 21 restoration cases |
| Actual local DVC integration | **11 passed**, including old A after B, two independent restores, identical split bytes, handwritten assignments and source preservation |
| Full checkout | **779 passed**, zero failed/skipped; existing private-model regressions use synthetic requests, no training; one existing Starlette/httpx warning |
| Extracted source / wheel | **575 passed each**, including all fifteen schemas and new deterministic tests; editable checkout bypassed |
| Frontend / notebooks | **38 passed** / two tracked notebooks passed |
| Ruff/format, architecture, actionlint | All passed; 50 formatted files, checker/workflow/dependencies unchanged; exact DVC 3.67.1 reused |
| Documentation/task/preservation | All 184 baseline files accounted for: 172 byte-identical, 12 scoped edits, nine new files / 21 increment files; both unrelated edits preserved; 11 frozen implementation hashes, 24 task records, local links/anchors, whitespace and unchanged branch HEAD/empty index checked |

Existing v1 evaluation fixtures remain byte-identical. New expected assignments are
handwritten; mutation/boundary/uncertainty and fresh-process tests avoid relying only
on generator/validator agreement. Initial I/O failure (**59 passed / 1 failed**) was
an overbroad write-interruption fixture also intercepting reads; corrected its scope
and all final checks passed. Exact commands, logs, statuses and recovery are in
[task verification](../tasks/2026-11-06-m2-development-splits/plan.md#verification--final-implementation).

Real-data/publication, ML/feature/target-lineage and protected/runtime checks were
skipped as outside scope; new-revision Linux CI and independent protected evidence
are unavailable for this uncommitted tree. The task records exact prerequisite/
recovery actions. Prior CI certifies only its published revision. Final evidence-only
edits are followed by task/link/preservation checks; no source is changed or pushed.

## Limits and next increment

This is a synthetic-first local metadata operation. Explicit creation provenance
must be reused for byte-identical reproduction; it is not invented or read from the
clock. The existing 1 MiB limits, representable empty populations and conservative
identity rules remain. Empty cohorts are not runnable comparisons. No real data,
scraping, training, source/data publication, trusted policy activation or protected
evaluation occurs. Metadata consistency is not proof of leakage-free features,
target aggregates, identity quality, runtime isolation or M2 exit-gate completion.

The **single recommended next increment** is a reviewed scalable metadata-inventory
transport for release and split processing, initially synthetic, preserving the
current identity/population semantics. This addresses the existing bounded-JSON
limit before a real release workflow. Before real data: approve projection/handling,
eligibility/cutoff/unseen and matching policies; provide authorized defensible
chronology or approved remediation and reviewed property pairs; and decide storage/
access/retention/quality requirements. M0/A14's historical chronology and scraper
limitations remain unresolved. This next increment is not started here.

## Source publication

The user's subsequent **"push please"** request was fulfilled on
[`feat/m2-development-splits`](https://github.com/fxmidaaa/pret-drept/tree/feat/m2-development-splits).
Source [52654bc](https://github.com/fxmidaaa/pret-drept/commit/52654bc23fe54b8d529d476f8c87ae53a9c1652a)
contains the exact 21 reviewed paths and unchanged 11 implementation hashes. The
remote feature ref matched that exact SHA after push. Both unrelated reporting
edits remain local and byte-identical; `main` was not changed and no new PR/merge
or data publication was created.

[Linux CI 42206582156](https://github.com/fxmidaaa/pret-drept/actions/runs/42206582156)
passed for the exact source SHA: **767 passes / 12 private-model skips**,
**575 tests per distribution**, **38 frontend passes**, and all remaining workflow,
notebook, static/architecture and DVC setup/integration checks. The private model
is absent in CI; no fake model or training hides its skips. Earlier unavailable
Linux CI/no-push statements describe the implementation checkpoint.

The bounded engineering/source-publication task is **COMPLETED**. This evidence-only
follow-up records the source anchor; resolve the actual feature branch HEAD/CI for
recovery. Exact [publication verification](../tasks/2026-11-06-m2-development-splits/plan.md#publication-verification)
and remaining gates are in the task. Source publication does not establish feature
leakage freedom, protected acceptance or the M2 exit gate.
