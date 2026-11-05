# RP-20261105-M2-CONTRACTS — first M2 increment

State: READY_FOR_REVIEW. Risk: **L2 source proposal**, because eligibility and split semantics
affect evaluation methodology (§6.2). The user authorized this bounded contract/test
increment, not application to real data or effective protected-policy changes.
Independent policy review remains external. M2 is started, not completed.

## Starting checkpoint and scope

Read all 2,343 lines of the frozen specification, AGENTS.md, M0/M1 evidence,
development guide, current audit checkpoint, M1/audit-completion/A14 records and
the actual public contracts, packaging, tests and legacy data/training boundaries.
Branch: `fix/repository-audit`; HEAD: `36e67b75ad562cec6dd98dc5bff7f411f383db4d`.
Existing A16/A18 and reporting work is uncommitted. Starting status, diff and
146 nonignored source-file digests are saved under
`/private/tmp/pret-drept-m2-contracts-rkyw61fp`. No private data/model was read for
discovery. Preserve all pre-existing work; append only necessary documentation.

Affected modules: additive `rent_contracts` schemas and evaluation validators,
synthetic foundation tests, source-distribution test inclusion, public contract
documentation, development guide, report checkpoint and this task record.
Legacy training, acquisition, inference, API, artifacts and interfaces stay intact.

## Acceptance criteria

1. Distinct listing/observation/property references, dataset-release and split
   digests; no positional observation identity or implicit missing-time defaults.
2. Explicit publication, collection, feature-availability and prediction-cutoff
   semantics, versioned policy and complete development assignments/exclusions.
3. Fixed evaluation membership across candidates, independent of target values,
   residuals, rent/m², local-rent ratios and candidate preprocessing success.
4. Future-market and conservative unseen-property development views; unresolved
   or probable identities never automatically become unseen. No final-holdout
   details, labels, executable selectors or matching thresholds in these contracts.
5. Synthetic tests reject malformed/contradictory metadata, population changes,
   duplicate observations, invalid cutoffs, unsafe unseen assignments and declared
   target-dependent selection. Repeated properties may enter future-market but
   must be identified as represented in the unseen-property view.
6. Relevant development, full checkout and distribution checks pass after final
   edits, with explicit failed/skipped/unavailable outcomes and recovery actions.
7. Policy remains reviewable before real-data use. References/metadata checks do
   not prove source truth, isolation, feature lineage or leakage-free evaluation.
   No claim of the M2 reproducible-run/development-evaluation exit gate.

## Implementation plan

1. Capture and inspect the starting tree; persist this plan and authorization.
2. Define the smallest reusable observation-reference, eligibility-policy and
   development-split schemas using existing local-schema/digest patterns. Document
   temporal intervals, exclusions, identity uncertainty and candidate correspondence.
3. Implement deterministic semantic validation and population correspondence,
   without a real-data reader, split publisher, model, experiment or policy activation.
4. Add meaningful synthetic valid/invalid and leakage/population fixtures; ship
   the self-contained tests with both source and wheel verification.
5. Review the proposal against §§8–9, 12.7, 13.4 and the A14 handoff. Run relevant
   checks after the last source edit, persist evidence, update the checkpoint and
   stop with this increment READY_FOR_REVIEW.

## Dependency-ordered later M2 increments

1. **Recommended next:** observation provenance and release-candidate validation.
   Build a synthetic-first, non-publishing validator/projector for a versioned
   observation inventory and aggregate quality report. Resolve time/identity,
   privacy and eligibility review gates before any authorized real-data application.
2. Implement immutable Git/DVC release envelopes and verified offline restoration
   after storage/access/retention decisions; do not publish data incidentally.
3. Evaluate identity resolution using reviewed property pairs; generate reviewed
   development manifests against defensible time evidence and immutable releases.
4. Add shared deterministic domain semantics and training-only fitted boundaries,
   including cutoff-aware/cross-fitted target aggregate lineage and fixed evaluation.
5. Implement XGBoost then CatBoost through independent public ML interfaces and
   authorized isolation; establish reproducible runs and dual development metrics.

## Risks, decisions and external prerequisites

M0 §8 establishes that the historical CSV has no observation timestamps. Its copy
date or recalled month cannot supply chronology. M0 §9 verifies current source
date-field capability only. The scraper updates date-only `last_seen` while skipping
detail refresh; it does not preserve observations. A14 still documents target-based
validation filtering and price-based deduplication. No private rows are needed here.

| Risk | Response in this increment | Remaining prerequisite |
| --- | --- | --- |
| Targets influence membership or identity | Closed metadata/reason fields; fixed target-independent rule declarations; no labels or selector code | Review referenced domain/matching policies and actual computations |
| Missing evidence becomes invented time/unseen identity | Explicit null/uncertainty; conservative exclusions; no matching thresholds | Authorized timestamped history or approved remediation; reviewed property pairs/policy |
| Candidates change population or source metadata | Full inventory accounting, metadata/policy/split digests and exact cohort correspondence | Authorized immutable dataset resolution and independently verified data bytes |
| Development proposal exposes final holdout | Development-only scope, closed fields, no final period/IDs/counts/labels | Separate protected manifest and access enforcement in later milestones |
| Local contracts mistaken for security/evaluation certification | Explicit evidence limits; no experiment/release activation | Independent protected review, validated isolation, reviewed-source rebuild and exact-artifact human approval |

Before the next increment can use real data: review this eligibility/temporal/unseen
proposal; authorize a private field projection and handling of identity evidence;
establish the scope/provenance of the input and domain/currency policy; decide how
unknown or unreliable times and identities are quarantined. Missing history may be
reported as unknown, but eligible temporal cohorts require defensible chronology or
approved remediation without guessed dates. Confirmed matching/unseen claims need
reviewed property pairs/policy; otherwise preserve unresolved identity. Acquisition
and enrichment need separate authorization (U-09). DVC remote,
access and retention choices precede publication/restoration. None is silently assumed.

## Verification and recovery

Implementation complete within this increment. Verification uses CPython 3.13.16,
Node 24.21.0 and the existing locked dependencies; nothing was installed. New fixtures
use invented IDs/times solely as synthetic cases, never as historical evidence.
Command results and logs are retained under the evidence directory. See the
[increment report](../../reports/m2-evaluation-contracts.md).

Exact recovery: run `git branch --show-current`, `git rev-parse HEAD`,
`git status --short`, `git diff --check`; read this plan, task.json and the current
report checkpoint. Compare pre-existing files against `starting-files.json`, inspect
only this increment's diff, and continue from recorded verification. Preserve all
prior work. Do not commit/push, acquire/migrate/publish data, experiment, activate
policy, access protected labels, promote or deploy under this task.

## Final verification

Executed after the last source/test edit. The runner sets
`PYTHONDONTWRITEBYTECODE=1`, `MPLCONFIGDIR` and `NUMBA_CACHE_DIR` to the task's
temporary evidence directory where applicable. Existing notebooks, model and
private data were not modified. Legacy inference regression tests load the supplied
local model; they do not train or evaluate a new candidate on private observations.

| Check / exact command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_evaluation_contracts.py` | **114 passed**, zero failures/skips. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` | **467 passed**, zero failures/skips, 20.71 s. One existing Starlette/httpx deprecation warning. |
| `.venv/bin/python scripts/check_distribution.py` | Extracted source **275 passed**, wheel **275 passed**, zero failures/skips; all ten local schemas exercised without the checkout's editable install. |
| `node --test tests/frontend/app.test.cjs` | **38 passed**, zero failures/skips; synthetic offline responses. |
| `.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed. |
| `.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed; 36 files formatted. |
| `.venv/bin/rent-check-architecture --root .` | Passed; runtime isolation is not assessed. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | Passed with existing pinned validator; no workflow changes. |
| `.venv/bin/python scripts/check_notebooks.py` | Passed for both tracked notebooks; neither executed. |
| `git diff --check` | Passed after source edits; final evidence check below repeats it. |
| `.venv/bin/python /private/tmp/pret-drept-m2-contracts-rkyw61fp/check_documentation.py` | Passed: 141 starting files byte-identical, five files recover their exact starting bytes after removing only this increment's additions; 10 new files / 15 M2 files total. All 21 task records, 43 local links/anchors in seven Markdown files, unchanged branch/HEAD, clean index and whitespace checked. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py` | Passed after evidence edits; one test validates every persisted record. Final evidence changes are checked again before delivery. |
| Failed checks | Initial focused run **105 passed, 1 failed**: optional JSON Schema date-time checking did not reject an impossible date. New semantic observation/manifest helpers explicitly parse calendar times, and final regressions pass. Initial Ruff format differences corrected. **No unresolved source/test failure.** |
| Skipped checks | Real-data application, DVC publication/restoration, acquisition, baseline training/development benchmarks, feature/aggregate-lineage execution, inference-container and protected-runtime tests: outside this increment; no experiment attempted. New browser smoke check also skipped because UI is unchanged. |
| Unavailable checks | New-revision Linux CI (uncommitted tree; no commit/push), independent protected review and effective access/isolation verification. M2 exit-gate evidence is unavailable pending authorized releases, defensible times/identities and isolated reproducible runs. |

The evidence runner is `run_checks.py` in the temporary directory, with each exact
command, exit status and log in `<check>-result.json` / `<check>.log`. The directory
is convenience evidence, not a permanent audit store; the commands/outcomes above
are durable. No runner, MLflow or new CI execution IDs exist.

Recovery for a failed or unavailable check: inspect its log and actual current diff;
repair only this increment and rerun the exact affected command plus dependent
checks. For an absent local environment, follow the locked development setup in
`docs/development.md` in an authorized dependency environment; do not update pins to
hide a failure. Restore nothing over pre-existing work. Linux CI needs separately
authorized publication; protected review/real-data access/isolation need independent
external evidence. Missing temporal/property facts remain unknown or excluded,
never replaced with assumed dates, thresholds or a random benchmark.

## Final checkpoint and exact next action

This first increment is implemented and locally verified, **READY_FOR_REVIEW**.
M2 remains incomplete, as does A14 benchmark implementation. No source/test check
has an unresolved failure; independent policy review and the real-data/isolated-run
prerequisites are still pending outside this increment. No commit/push, raw-data
inspection, acquisition, data publication, experiment, protected-label access,
effective-policy change, promotion or deployment occurred.

The actual branch/HEAD is unchanged. All 146 starting files retain their original
content, with only the five declared additive changes; in particular, all pre-existing
A16/A18, unrelated task/reporting and legacy source changes are preserved. Scope is
15 files: five existing integration/documentation files and ten new files. Existing
task histories and earlier audit evidence were not rewritten.

Exact next recovery action: run `git branch --show-current`, `git rev-parse HEAD`,
`git status --short`, `git diff --check`; read this task, the contract proposal and
M2 increment report. Reconcile against `36e67b75ad562cec6dd98dc5bff7f411f383db4d`
and the preserved uncommitted audit work, without restoring earlier branch tips.
Review the 15-file increment, especially time/quarantine and conservative identity
rules. The single recommended next increment is the synthetic-first, non-publishing
observation provenance/release-candidate validator above. Obtain policy/field-handling
review and applicable input authorization before real-data application; unknown
history/identity stays unresolved. Stop here in this session. No task text grants
data, publication, experiment or protected-action permissions.

## Pull request follow-up — 2026-11-05

The user subsequently requested a pull request into `main`. This authorizes the
source commits and push necessary to create that PR, superseding the earlier
session's no-commit/no-push constraint for this publication. It does not authorize
merge, effective policy activation, data work, experiments, promotion or deployment.

Remote state checked through GitHub: `main` is at
`0427a092426c11efe7f30110c3d26e94c9bfb969`; `fix/repository-audit` is at
`36e67b75ad562cec6dd98dc5bff7f411f383db4d`; no existing PR was returned. The PR
therefore includes the accumulated audit branch and verified A16/A18 follow-up
alongside this first M2 increment. The two unrelated
`2026-11-05-audit-report-consistency/{plan.md,task.json}` edits stay local and
byte-identical. Starting publication hashes/status/diff are retained under
`/private/tmp/pret-drept-pr-main-iroydzwc`.

Publication plan: verify documentation/task/preservation after this evidence edit;
stage only reviewed source/test/documentation paths, excluding those two files;
commit and fast-forward push the current branch; create the PR targeting `main`
with the full branch scope and explicit A10/A14/M2 limits; verify remote refs, PR
base/head and Linux CI. Record the actual PR/source/CI references once available.
Recovery: inspect actual status and PR head before any retry; do not force-push,
include private/ignored artifacts, merge or overwrite the preserved local edits.

### Publication evidence

Created [PR #1](https://github.com/fxmidaaa/pret-drept/pull/1),
`fix/repository-audit` → `main`, open for review and unmerged. Source commit:
`fa0f28c879d5180cb04fb783c22866f911ddadc1` (65 reviewed files). Its full PR diff
contains 126 files including the earlier audit commits; remote filenames exactly
match `git diff origin/main...HEAD`. Both unrelated report-consistency files remain
uncommitted and match their starting publication hashes.

The GitHub connector read the repository but PR creation returned integration
HTTP 403. The existing GitHub CLI identity was independently checked as `fxmidaaa`;
`gh pr create --repo fxmidaaa/pret-drept --base main --head fix/repository-audit`
with the prepared title/body file created the PR. No new credentials or permission
changes were needed.

Exact-source [Linux PR CI run 42116621974](https://github.com/fxmidaaa/pret-drept/actions/runs/42116621974)
passed; foundations job `127557856701` reported **455 passed, 12 private-model
checks skipped**, one existing deprecation warning. Source/wheel each passed **275**;
frontend passed **38**; semantic workflow, notebooks, static and architecture checks
passed. Logs were inspected for these counts. The omitted private model is an
explicit prerequisite skip, not an inference/privacy/runtime certification. This
development CI does not close A10, A14, independent protected review or M2's gate.

This evidence-only follow-up is committed separately; it changes no source/test
behavior. On recovery, resolve the PR's actual latest head rather than restoring
the historical `36e67b7` or source-only `fa0f28c` checkpoint. Check PR base/head,
status and the latest CI run before review/merge decisions. Recheck local evidence
with `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-pr-main-iroydzwc/check_publication.py`,
the repository task test and `git diff --check`. That probe now checks the pushed
branch head; the original probe retains the pre-publication checkpoint. Preserve
the two local reporting edits. No merge is authorized by this task.
