# RP-20261106-M2-SPLITS — deterministic development split materialization

State: COMPLETED — bounded source increment and authorized source publication only.
Risk: **L1 engineering** under frozen architecture §§4–6, 8–9,
15–16. This implements existing proposed v1 rules on synthetic metadata; it does
not change evaluation methodology or activate trusted policy. The first HITL
approved Option A. Stop for the second HITL after implementation/verification.

## Starting state and authorization

Read AGENTS.md, frozen responsibility/identity/temporal/leakage requirements, M0,
A14, development guide, current report checkpoint and increment-3 task/design/code.
Starting branch `feat/m2-local-dvc-releases`, HEAD
`e56c1155e7e570fd665ccd3f2700db8d963ecacf`. Created local
`feat/m2-development-splits` at unchanged HEAD. Only two pre-existing unrelated
report-consistency files were dirty; preserve both byte-identically. Snapshot:
184 nonignored file hashes, diff/status under
`/private/tmp/pret-drept-m2-splits-1t27abqi`. No raw/private file was inspected.

Approval is recorded in [request.md](request.md). No new versioned split-plan
document, schema migration, dependency update, framework or CLI. Approved tests
include actual DVC operations and fixture commits only in disposable synthetic
repositories/local stores. No repository commit/push or PR operation until the
user's second review and a later publication instruction.

## Scope and design

1. Public membership derivation in `rent_contracts.evaluation`, sharing the existing
   v1 assignment rules with validation. Keep full validator signatures, schema and
   set-based reason/cohort acceptance unchanged. Temporal inputs reuse the bundled
   split field schemas and calendar checks; no duplicate timestamp grammar.
2. Pure `rent_data.splits`: validate expected release/policy refs, complete supplied
   observation digest/count, and release/observation policy correspondence. Build
   the existing development-split with explicit cutoff/window and creation
   provenance. Validate the resulting self-digest and complete semantic envelope.
   Pure verification does not prove storage recovery, authorization or metadata truth.
3. `rent_data.split_io`: obtain observations only from `read_verified_restore`,
   call the pure builder, atomically create `development-split.json` in an exclusive
   new output directory outside the restored workspace. Never modify that release,
   its metadata/cache or a prior output. Readback requires expected release, policy
   and split refs and rechecks the restored release and split semantics.
4. Extract the existing atomic non-overwriting file primitive in release I/O for
   reuse. Keep restoration validation in its existing wrapper and preserve tested
   failure/recovery semantics. No generic storage framework or new authority type.
5. Keep data implementation independent of ML, harness and privileged platform.
   No schema/dependency/checker weakening. Ship deterministic core tests and retain
   actual DVC integration as a checkout check in the existing CI/test scopes.

Rules remain: training prediction cutoff strictly before training cutoff; validation
in `[start, end)` with `cutoff <= start < end`; gap/outside rows explicitly excluded;
all applicable reasons accumulate. Every observation receives exactly one assignment.
All eligible validation rows belong to future-market; secondary unseen-property
membership uses the complete declared training partition, confirmed identities and
the existing overlap/uncertainty rules. No candidate-specific training subset or
target-based selector affects membership. Empty training/cohorts remain representable;
an empty evaluation cohort still fails the existing comparison population validator.
No fallback split or new minimum-size policy is invented.

Generated arrays are sorted deterministically; old validators continue accepting
their previously valid ordering. All complete inputs, including supplied source
snapshot/creation timestamp, determine canonical bytes and split identity. No clock,
filesystem location, random seed or environment-dependent metadata enters generation.
Changing provenance intentionally changes identity even if membership is unchanged.
Existing 1 MiB bounds fail closed; no row dropping/sharding/transport migration here.

## Acceptance criteria

1. Existing fifteen wire schemas and evaluation/regression interfaces remain
   compatible; old handwritten evaluation tests pass unchanged. One shared v1
   derivation implementation supplies generation/validation, with safe diagnostics.
2. Builder binds externally fixed release and policy identities, exact full inventory
   and referenced domain/matching policies. Wrong refs, omissions/substitutions,
   conflicting metadata, invalid windows/provenance and unsupported inputs fail.
3. Handwritten expected membership fixtures verify exact partitions, all exclusion
   reasons, cutoff/offset boundaries, future-market overlap and conservative unseen
   handling. No target fields, implicit dates, guessed identities or selectors.
4. Identical complete inputs yield identical canonical artifact bytes/digest across
   input order, fresh interpreters/hash seeds and independently restored copies.
   Caller-owned inputs stay unchanged. A different release/policy/provenance binds
   a different split identity. Fixed-cohort comparisons reject candidate population
   changes and resealed split substitution.
5. Exclusive, bounded split I/O never modifies restored release/prior outputs. Invalid
   input writes no output. Interrupted atomic writes leave no final split file;
   readback rejects missing/corrupt files, unsafe filesystem entries and wrong refs.
6. Actual local DVC A-after-B recovery feeds split construction/readback, not a
   mocked successful restoration; complete supplied population is conserved.
7. Relevant development-guide checkout/source/wheel, scoped static/architecture,
   workflow/notebook/frontend and final documentation/task/preservation checks pass
   after final relevant edits. Record passed/failed/skipped/unavailable outcomes,
   exact recovery, limits and second-review handoff. No source publication or M2
   exit-gate claim; preserve both unrelated changes and original HEAD.

## Implementation and verification sequence

Persist task before source edits; extract public membership derivation; implement
pure release-bound split builder/validator; extract shared atomic creation; implement
thin verified split I/O; add independent handwritten and metamorphic negative tests;
extend actual disposable DVC integration; update packaging and architecture/development/
report checkpoint; run relevant checks; record exact outcomes and stop READY_FOR_REVIEW.

Use locked CPython 3.13/DVC tooling. Run focused evaluation/split/release I/O tests
while developing. After final source edits run `docs/development.md` commands:
actionlint, notebook publication, Node frontend tests, scoped Ruff check/format,
architecture, full pytest including actual DVC integration, source/wheel distribution
verification. Record environment and actual counts rather than predicting success.
After final evidence edits, rerun task/link/preservation/whitespace checks and verify
the final implementation hashes. Do not broaden/repeat passing checks without edits
or a specific unresolved concern. No real data, model training or acquisition tests.

Risks: sharing derivation can make generator/validator agree on a bug; old untouched
handwritten fixtures plus new explicit expected outputs/boundaries provide an
independent oracle. Atomic helper extraction can regress restoration; existing
failure/recovery and real DVC tests must pass. Canonical ordering must not narrow old
validator acceptance. A self-consistent digest/metadata/report is not approval or
feature/target-lineage verification. Single-writer filesystem checks are not host
isolation, concurrency or power-loss certification.

## Recovery and later work

Inspect branch/HEAD/status/index and diff; expect `feat/m2-development-splits` at
`e56c1155e7e570fd665ccd3f2700db8d963ecacf` plus only this increment and the two
preserved unrelated reporting edits. Read this task/current checkpoint and compare
against the 184-file snapshot; never reset to a historical branch tip. Continue
only approved Option A; rerun affected checks after edits and persist failures.
Keep incomplete split destinations unusable; retry at a new path or inspect/remove
only task-owned disposable fixtures. Stop uncommitted with results/commit message
for user review. Do not infer permission for publication or real data.

Later dependency order: approved scalable real-data projection/release preparation
and storage/access/retention decisions with defensible chronology/reviewed identity;
training-only transformations/target-aggregate lineage; independent baseline adapters;
isolated reproducible runs and fixed dual-view development evaluation. This increment
does not establish any of those gates. A14/M2 remain open.

## Verification — final implementation

Environment: **CPython 3.13.16, macOS ARM64**, Node **24.21.0**, Ruff **0.17.3**,
actionlint **1.7.12**, separately installed DVC **3.67.1**. No dependency, schema,
workflow or checker was changed. Reused the existing locked development/tool
environments; no package download, scraping, private input inspection or training.

Evidence directory: `/private/tmp/pret-drept-m2-splits-1t27abqi`. `verify.py`
records exact commands, durations, return codes and safe logs. It uses
`PYTHONDONTWRITEBYTECODE=1`, the absolute `.venv-data-tools/bin/dvc` through
`RENT_DATA_DVC`, and owned temporary Matplotlib/Numba caches. All source checks
below ran after the last implementation/test/package edit. The 11 implementation
hashes remain frozen; only documentation/task evidence changed afterward. Final
task/link/preservation/whitespace checks follow this evidence edit.

| Check/command | Outcome |
| --- | --- |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_development_splits.py tests/foundations/test_split_io.py tests/foundations/test_evaluation_contracts.py tests/foundations/test_release_io.py` | **223 passed**, zero failed/skipped. Includes 49 new builder cases, 39 new I/O cases, all 114 byte-identical existing evaluation cases and 21 restoration I/O cases. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/integration/test_dvc_restoration.py` | **11 passed**, including the new actual restore→materialize→readback path. Old A is restored twice from independent consumer caches after B exists; exact handwritten four-row assignments and identical canonical split bytes are checked. Source A and producer B payloads remain intact. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` | **779 passed**, zero failed/skipped. Existing 12 private-model regressions ran with synthetic requests; no fitting/training. One existing Starlette/httpx deprecation warning remains. |
| `.venv/bin/python scripts/check_distribution.py` | **575 passed** from extracted source and **575 passed** against the wheel, with checkout editable import bypassed. All fifteen schema resources and the new self-contained tests work in both forms. Actual DVC integration remains checkout-only. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | **Passed**, unchanged workflow and pinned validator. |
| `.venv/bin/python scripts/check_notebooks.py` | **Passed**, two tracked notebooks, no execution/output changes. |
| `node --test tests/frontend/app.test.cjs` | **38 passed**, no failures/skips; UI unchanged. |
| Scoped `ruff check` and `ruff format --check` from the development guide | **Passed**, 50 files formatted; no suppressed findings. |
| `.venv/bin/rent-check-architecture --root .` | **Passed**, unchanged checker; runtime isolation is not assessed. |
| `.venv-data-tools/bin/dvc --version` | **Passed**, exact 3.67.1; no install/update attempted. |
| `.venv/bin/python /private/tmp/pret-drept-m2-splits-1t27abqi/check_documentation.py` | **Passed**, rerun after final evidence updates. All 184 baseline files accounted for: 172 byte-identical, 12 authorized modifications to initially clean files, nine new files / 21 increment files. Original rule functions and unaffected release I/O are AST-identical; original evaluation tests, all 15 schemas and locks remain byte-identical. All 11 implementation hashes, 24 task records, links/anchors across nine Markdown files, whitespace, branch/HEAD and empty index checked. Both unrelated edits preserved. |

The shared generator/validator do not constitute an independent correctness oracle.
The unchanged original evaluation fixtures plus new handwritten full assignments,
explicit boundary/offset and uncertainty cases, fixed-population mutation checks
and source-backed recovery tests provide the relevant independent expectations.
Readback accepts existing valid array order; generated output is deterministic.
Changing release/policy/explicit provenance changes identity even when membership
is unchanged. Empty cohorts/training are represented without fabricating a runnable
experiment or silently choosing a new benchmark.

Earlier failure, resolved before final verification: the initial focused I/O run
was **59 passed / 1 failed**. Its partial-write injection replaced `os.fdopen` for
read streams too, so it failed before reaching the write being tested. Restricted
that fixture to write mode; reads now proceed normally, the actual partial write
raises, cleanup removes staging output and no final split is created. No production
behavior was weakened. Final I/O/restoration suite passed 60 cases, and the aggregate
checks above passed. Ruff import/format findings were corrected before final checks.

| Status | Deferred check | Exact recovery action |
| --- | --- | --- |
| **Skipped** | Real/private data projection, acquisition, actual split/data publication and production storage | Obtain independently reviewed projection/handling and domain/eligibility/cutoff/unseen/matching policies; authorized defensible chronology or approved remediation; reviewed property pairs; scalable transport and storage/access/retention/quality decisions. Implement a separately approved increment; do not infer acquisition or enrichment permission. |
| **Skipped** | Model/feature/target-aggregate execution, real benchmarks, protected labels/runtime, promotion/deployment | After approved inputs/splits and supported isolated runtime exist, obtain appropriate external authorization and run exact-source reproducible baselines plus independent verification. Metadata tests cannot replace actual lineage/leakage or runtime checks. |
| **Skipped** | New browser smoke test | UI boundary is unchanged and 38 offline frontend checks pass. Run a synthetic browser smoke check if that boundary changes later. |
| **Unavailable** | New-revision Linux CI | This tree is intentionally uncommitted/unpushed for the second HITL. After review and explicit publication instruction, publish the exact approved source and verify its own Linux CI. Previous `e56c115` CI is historical evidence, not this diff. |
| **Unavailable** | Independent real-data policy review, protected reference/access/isolation verification and M2 exit gate | Responsible external owners must review/provision effective data/runtime controls. Resolve chronology/identity/projection/transport and isolated baseline prerequisites, then perform the authorized real development evaluation. Do not substitute fabricated dates, source declarations or historical random scores. |

No unresolved required local check failed. Source edits require rerunning the
affected command and dependent checks; evidence-only edits require final task/link/
preservation checks. Local `/private/tmp` logs are supplemental and may expire;
persistent outcomes and exact recovery stay here. If the temporary baseline is
unavailable, inspect the full 21-file diff against unchanged `e56c115`, preserve
pre-existing work and rerun relevant checks instead of claiming a recovered hash proof.
The two preserved unrelated file SHA-256 values are:

- `2026-11-05-audit-report-consistency/plan.md`:
  `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2`.
- `2026-11-05-audit-report-consistency/task.json`:
  `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6`.

## Architecture reconciliation and handoff

| Requirement | Implementation and limit |
| --- | --- |
| §§4–5 boundaries | Public semantic derivation stays in contracts; pure assembly and local I/O stay in data. No ML/harness/platform dependency, new wire schema or framework. |
| §§8–9 identity/population | Expected release/policy/split digests bind exact full inventory and provenance. Verified local read reconstructs sources; no trusted authorization or raw-source truth is inferred. |
| §9.3 temporal behavior | Existing grammar/calendar checks and exact prediction-cutoff windows; explicit creation provenance, unknown facts preserved. No real dates chosen. |
| §§9.5–9.6 views/leakage | Primary overlap retained, unseen uncertainty conservative, fixed complete training reference and candidate cohort checks. Features/target-lineage leakage remains unverified. |
| §§6, 15–16 evidence | Persistent L1 plan/approval, independent fixtures, actual synthetic DVC integration, source/wheel and static checks. Local evidence does not certify protected execution or M2 completion. |

Outcome: **READY_FOR_REVIEW**, approved increment 4 only. Branch
`feat/m2-development-splits`, HEAD unchanged at
`e56c1155e7e570fd665ccd3f2700db8d963ecacf`; index empty, no commit/push or PR action.
Both unrelated reporting edits and all earlier source/task evidence are preserved.
No next increment has started. Wait for the second HITL.

The **single recommended next increment** is reviewed scalable metadata-inventory
transport for release and split processing, initially synthetic and preserving the
current identity/population semantics. It addresses the 1 MiB foundation limit before
a real release workflow. Real-data use additionally requires the policy/projection,
defensible chronology or approved remediation, reviewed identities and storage/
access/retention/quality prerequisites above. M2/A14 remain open.

Proposed commit message, not executed:
`feat(data): materialize deterministic development splits from verified releases`.

## Source publication follow-up

The user explicitly requested **"push please"** after reviewing the implementation
and discussing feature-leakage limits. This authorizes commit/push of increment 4
on `feat/m2-development-splits`. Earlier no-publication/second-HITL-wait statements
above describe the implementation checkpoint. The 21-file source scope and frozen
11 implementation hashes remain unchanged. Both unrelated report-consistency edits
must remain byte-identical and uncommitted.

Plan: record this authorization; stage only the exact reviewed 21 paths; compare
index content to the reviewed tree and frozen hashes; run relevant documentation/
task/whitespace and standalone workflow/notebook checks; commit the proposed title;
push this feature branch without force or changes to `main`; verify remote SHA and
Linux CI for that exact source; persist the resulting publication evidence. No new
PR/merge, data/split publication, real input, ML experiment or protected operation.

Recovery: inspect actual branch/HEAD/index/status and remote before continuing.
After committing, the old empty-index/`e56c115` assertions are historical; compare
the published commit tree and publication snapshot instead. Preserve local commits
on failure, inspect remote divergence and CI diagnostics, then repair/recheck only
the affected operation. Never force push, reset prior work, infer credentials or
silently treat pending/failed CI as passed. Source changes require affected checks;
evidence-only changes require final task/link/preservation checks. M2/A14 and actual
feature/target-lineage leakage verification remain open.

## Publication verification

The reviewed increment was committed as
[52654bc](https://github.com/fxmidaaa/pret-drept/commit/52654bc23fe54b8d529d476f8c87ae53a9c1652a)
with the proposed title, after exact index/content checks for all **21 paths**.
`git push --set-upstream origin HEAD:refs/heads/feat/m2-development-splits` succeeded
without force. `git ls-remote --heads origin refs/heads/feat/m2-development-splits`
independently confirmed source SHA `52654bc23fe54b8d529d476f8c87ae53a9c1652a`.
No change to `main`, new PR, merge, data publication or experiment occurred.

[Linux CI run 42206582156](https://github.com/fxmidaaa/pret-drept/actions/runs/42206582156)
completed successfully for the `push` event and that exact source SHA. Inspected
run metadata, job/step conclusions and logs: **767 passed / 12 private-model checks
skipped**, **575 passed per distribution**, **38 frontend passes**, plus all
workflow/notebook/static/format/architecture and separate DVC installation/integration
steps. One existing Starlette/httpx warning remains. CI has no private model, which
explains its 12 skips versus 779 local passes; no substitute model or training was
used. Skips do not certify private-artifact behavior.

Publication baseline/proofs: `/private/tmp/pret-drept-m2-splits-publish-ho_rfili`
contains 193 starting file hashes, diff/status and source/final index/content
proofs. All **11 implementation hashes** still match local verification. Only five
authorization/evidence documents changed during publication; all other reviewed
files and both unrelated edits remain byte-identical. After the source commit/push,
the index was empty and only the two unrelated reporting edits remained local.

This documentation-only follow-up records source publication and CI. Its final
task/link/preservation, task tests, standalone workflow and notebook checks run
before commit/push; it changes no implementation. Resolve the feature branch's actual
HEAD and its own CI for recovery rather than resetting to the source anchor above.
The source task is complete after user review/publication. M2/A14, real-data policy,
chronology/identity/transport, actual feature/target-lineage leakage verification,
protected acceptance and deployment gates remain open. No next increment started.

Current recovery: inspect actual local/remote `feat/m2-development-splits` HEAD,
status/index/diff and exact-head CI; expect only the two original report-consistency
edits to be dirty. Check publication proofs and original source hashes. Retain
commits and record/repair actual push/CI failures if interrupted; never force push,
reset prior work or infer production readiness. Propose any next increment under
the user's intent/proposals/HITL/implementation/HITL workflow before coding it.
