# RP-20261106-M2-CANDIDATES — observation provenance and candidates

State: READY_FOR_REVIEW. Risk: **L1 engineering** under frozen architecture §§4–6, 8–9,
15.3 and 16.2. This increment adds non-publishing data validation and public
metadata contracts. It preserves the first increment's evaluation methodology,
legacy interfaces and effective policies. Reclassify before any protected action;
there is no such action in this plan.

## Authorization, checkpoint and affected modules

The user requested the second M2 increment, asked for a brief plan before action,
and prioritized engineering quality, reproducibility, consistency, extensibility
and modularity with continuous architecture alignment. The initial commentary
stated the synthetic-first, non-publishing scope and verification approach.

Read AGENTS.md, the current reports/development checkpoint, M0/A14 handoffs, the
first M2 task/contracts and relevant frozen architecture requirements. PR #1 is
now merged. GitHub comparison from local `d920ffc89a2673945142c5eb6442a56069cc27d7`
to `main` reports one merge commit and **no file changes**. The local source tree
therefore matches the merged implementation. Work is on the new local branch
`feat/m2-observation-candidates`, at the same HEAD. Two pre-existing unrelated
report-consistency files remain uncommitted and must stay byte-identical.
Starting status/diff and 156 nonignored source hashes are retained under
`/private/tmp/pret-drept-m2-candidates-im6ab3qz`; no private data/model was read.

Affected modules: public source/candidate/aggregate-report schemas in
`rent_contracts`; a small public helper extracting existing observation eligibility
checks without changing their semantics; `rent_data.candidates` for pure data
validation/projection; synthetic tests, package inclusion and architecture/docs.
The `rent_data` domain and its dependency restrictions already exist in the checker.
No new dependency, generic framework, service, database, DVC remote or ML adapter.

## Bounded design and acceptance criteria

1. Accept explicit UTF-8 **metadata source envelopes**, supplied as bytes, with a
   raw-source reference, nullable acquisition evidence/period and stable source
   record IDs mapped to the existing observation-reference contract. No raw CSV,
   source text/contact/address/target payloads, path readers or acquisition client.
2. Bind the exact supplied source bytes, sizes, counts, raw-source references,
   projection/transformation/domain/matching references and full observation lineage.
   Account for every supplied record. Reject duplicate sources/raw references,
   source record IDs, observation identities, aliased captures, contradictory lineage,
   incompatible policies and impossible/inconsistent acquisition metadata.
3. Deterministically project **all** observations, including unknown/invalid ones,
   and produce an unpublished candidate and aggregate quality report. Reordering
   source inputs or projections must not alter observation semantics or counts;
   candidate ordering is canonical by identity, source wire bytes remain exact
   identity. Unknown dates/identities/confidence stay unknown; generate none.
4. Reuse the first increment's non-window eligibility checks. Aggregate domain,
   temporal, property-resolution and missing acquisition evidence counts; report no
   observation/listing/property IDs, source rows, target statistics or private text.
   No report claims eligibility, publication, reviewed identity or leakage freedom.
5. Revalidation rebuilds expected projection, lineage, counts and digests from the
   supplied source bytes. Resealing a tampered candidate/report must not hide omitted
   records, substituted metadata, changed counts, false lineage or corrupted inputs.
6. Synthetic positive/negative tests demonstrate deterministic rebuilding, exact
   population conservation, uncertainty preservation, safe diagnostics, source-byte
   integrity, caller-mutation independence and first-increment consistency.
7. Keep data implementation dependent on public contracts/stdlib only. Exercise
   new schemas/data code from both source distribution and wheel; verify forbidden
   data-to-harness/platform and contracts-to-data imports without executing fixtures.
8. Run relevant development checks after the last source/test edit, then final
   documentation/task/preservation checks after evidence edits. Persist exact
   passed/failed/skipped/unavailable outcomes and recovery actions.

## Implementation plan

1. Persist this plan, risk, acceptance criteria and authorization before code edits.
2. Add the three small versioned metadata schemas using existing strict local
   JSON resources. Define exact-byte versus canonical-content identities and the
   acyclic candidate/report digest relationship.
3. Extract a public helper for the existing observation quality/eligibility reasons;
   use it unchanged from development splits and the new aggregate report.
4. Implement pure candidate building, validation and validated observation projection
   in `rent_data`; no host I/O, mutable registry, timestamps from the clock or side effects.
5. Add synthetic regression/invariant fixtures and package/architecture integration.
6. Review against the frozen responsibilities and M0/A14 limits, run checks and
   document the exact scope, evidence, remaining gates and one recommended next step.
7. Stop READY_FOR_REVIEW. No commit, push, PR mutation, merge or data application.

## Risks, limits and later dependencies

| Risk | Response here | Remaining requirement |
| --- | --- | --- |
| A source digest is mistaken for proof of private input truth/completeness | Verify only supplied metadata-envelope bytes and conserve their records; label raw-source/provenance references as declarations | Authorized source resolution and independently verified raw bytes/projection |
| A candidate drops difficult/unknown observations | Complete projection/lineage and recomputation from sources; quality issues are counted, never used to drop rows | Reviewed eligibility and fixed development manifests later |
| Data quality/evaluation logic diverges | Reuse existing non-window checks; run all first-increment regressions and consistency fixtures | Actual domain/feature/target-aggregate lineage review |
| Schema allowlists are mistaken for anonymization/access controls | Closed metadata-only envelopes and safe aggregate reports/errors | Approved field handling, storage/access enforcement and privacy review |
| Small JSON foundation is mistaken for a scalable/restorable release | Retain existing 1 MiB bounds and unpublished-candidate status; fail instead of truncating | Columnar/external inventory transport and Git/DVC release/restoration design |

M0 established missing historical observation times; current source dates and
date-only scraper checkpoint updates do not reconstruct history. This task does
not inspect or adapt the private CSV, infer identities, convert currencies or
activate the proposed evaluation policy. Referenced policies need independent
review; a digest or merged PR does not establish that review for real-data use.
No final-holdout fields, labels, selectors or candidate-specific filtering.

Later order: review the candidate/projection and field-handling policies; resolve
authorized inputs and chronology/identity evidence; design immutable Git/DVC release
envelopes and verified restoration with reviewed storage/access/retention choices;
then generate reviewed development splits and implement isolated baseline training.
M2's reproducible-run/development-evaluation exit gate remains open.

## Verification and exact recovery

Implementation is complete and locally verified within scope.
Verification used existing CPython 3.13.16 / Node 24.21.0 and the locked environment;
no dependency was installed. Existing legacy model checks loaded the supplied local
model using synthetic requests; no new training experiment or private observation
inspection occurred. See the [increment report](../../reports/m2-observation-candidates.md).

On recovery run `git branch --show-current`, `git rev-parse HEAD`,
`git status --short` and `git diff --check`; read this plan/task, the report checkpoint
and actual diff. Expect local branch `feat/m2-observation-candidates` based on
`d920ffc89a2673945142c5eb6442a56069cc27d7`. Reconcile against actual Git state,
not historical audit tips. Compare the two untouched reporting files and other
pre-existing source bytes with `starting-files.json`. Preserve all local work.
Continue only the recorded source increment; after edits rerun affected checks.
Do not commit/push, access private/protected inputs, acquire/publish data, change
effective policy, experiment, promote or deploy under this request.

## Verification evidence

After the final test edit, the source suite and distributions were rerun to exercise
fresh-interpreter/hash-seed rebuilding in both source and wheel contexts. The earlier
568/376 counts precede that added reproducibility case; the final counts are below.
The existing 114 evaluation cases also passed after the shared-helper extraction.
Unchanged frontend/workflow/notebook checks passed during the aggregate run.
Runner environment: `PYTHONDONTWRITEBYTECODE=1`; task-specific `MPLCONFIGDIR` and
`NUMBA_CACHE_DIR` under `/private/tmp/pret-drept-m2-candidates-im6ab3qz`.

| Check / exact command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_observation_candidates.py` | **98 passed**, zero failed/skipped. Includes fresh interpreters with two hash seeds, all-unknown facts, source byte/lineage integrity, resealed tampering, population conservation and size bounds. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_evaluation_contracts.py` | **114 passed**, zero failed/skipped; first-increment semantics retained. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` | **569 passed**, zero failed/skipped, 8.81 s; one existing Starlette/httpx deprecation warning. |
| `.venv/bin/python scripts/check_distribution.py` | Extracted source **377 passed** and wheel **377 passed**; zero failures/skips. New `rent_data` package and all 13 local schemas exercised without the checkout's editable install; child interpreters preserve those isolated import paths. |
| `node --test tests/frontend/app.test.cjs` | **38 passed**, zero failed/skipped; frontend is unchanged. |
| `.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed. |
| `.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed; 39 files formatted. |
| `.venv/bin/rent-check-architecture --root .` | Passed; static dependency checks do not certify isolation. Four new positive/negative data-domain cases also ran in the checkout and distributions. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | Passed with the existing pinned validator; workflow unchanged. |
| `.venv/bin/python scripts/check_notebooks.py` | Passed for both tracked notebooks; neither executed or edited. |
| `git diff --check` | Passed; repeated after final evidence edits. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-m2-candidates-im6ab3qz/check_documentation.py` | Passed: 148 starting files byte-identical and eight scoped edits verified against their original content; both unrelated reporting files preserved. Scope: 19 increment files / 11 new. All ten implementation/schema/test/package hashes still match final source checks; 22 task records, 50 local links/anchors in eight Markdown files and 13 schemas checked. Branch/HEAD unchanged after initial branch creation; no staged changes; whitespace clean. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py` | Passed after evidence edits; one test validates all persisted records. Repeated after final task/evidence synchronization. |
| Failed checks | One intermediate run had **244 passes / one failure**: expanded output correctly failed, but canonical JSON swallowed its own size diagnostic as a generic encoding error. Preserving the safe `ContractError` fixed the diagnostic without changing bounds. **No unresolved implementation/test failures.** |
| Skipped | Private/raw-data projection, acquisition, real releases, DVC restoration/publication, split generation, model training/benchmarking, feature/aggregate-lineage execution and protected/runtime tests. A new browser smoke check is skipped because the UI boundary is unchanged. |
| Unavailable | New-revision Linux CI because the increment is uncommitted/unpushed; independent protected policy/access/isolation evidence; real chronology/reviewed identity and approved release/restoration evidence. Prior merged PR CI does not certify this diff. |

The temporary `run_checks.py` records exact commands, exit codes and logs as
`<check>-result.json` and `<check>.log`. `verified-implementation.json` freezes all
ten implementation/schema/test/package file hashes after the final successful runs.
These temporary files are convenience evidence; commands and outcomes here are the
durable record. Runner/MLflow/new CI IDs: none. The input/output limits and missing
external prerequisites are explicit; no local pass closes M2's exit gate.

Recovery for a failed check: inspect its log and the scoped diff; repair only this
increment, rerun the exact affected command plus dependent checks, then update the
task evidence. If the local environment is absent, follow the locked setup in
`docs/development.md` in an authorized dependency environment; do not change pins
to hide a failure. If temporary evidence is gone, recreate the scope/preservation
probe against the recorded checkpoint and inspect both unrelated reporting files;
never restore an old tree over them. Linux CI needs separately authorized publication.
Raw-source verification, data projection and protected checks need independent
review/authorization/evidence; unknown facts remain unknown until then.

## Final architecture reconciliation and recovery

| Frozen requirement | Increment evidence / limit |
| --- | --- |
| §§4–5, independent domains | `rent_data` uses public contracts/stdlib; existing domain map and four new boundary fixtures pass. No harness/privileged/ML implementation coupling. |
| §8, reproducible data identity | Exact supplied metadata bytes, complete lineage and canonical artifacts rebuild identically in fresh interpreters/hash seeds. Raw-source truth, Git/DVC storage/restoration/retention and publication are explicitly deferred. |
| §9, identities/time/leakage | Explicit identities/null facts, collision and temporal consistency checks; every source observation retained. Shared v1 exclusion semantics and 114 unchanged evaluation tests; no matching, target selection or feature-leakage certification. |
| §§6, 15–16, evidence | Persistent L1 plan/criteria/recovery; 569 checkout tests, 377 tests per distribution and scoped static checks. Protected/runtime and real-data evidence is not inferred from local success. |

Outcome: **READY_FOR_REVIEW**, source increment 2 only. The first increment's
schemas, rules and legacy application interfaces remain compatible. No private raw
rows or protected labels were accessed; no commit/push, acquisition, data publication,
experiment, effective-policy activation, promotion or deployment occurred. M2's
reproducible-run/development-evaluation exit gate and A14 remain open.

Exact next recovery action: confirm `feat/m2-observation-candidates` at
`d920ffc89a2673945142c5eb6442a56069cc27d7`, inspect status/diff and this task/report,
and review the 19-file increment. Run the documentation/preservation command, task
test and whitespace check above; after any source/test edit rerun affected source,
distribution and architecture checks. Preserve both pre-existing report-consistency
edits. Review the metadata-source/projection assumptions and bounded transport
before any real-data application; no task state grants that permission.

The **single recommended next increment** is immutable Git/DVC release envelopes
and local restoration verification, initially synthetic. Resolve scalable inventory
transport plus storage/access/retention and release-quality policy before real
publication. Private input projection, domain/currency provenance, chronology and
matching evidence retain their independent review/authorization gates. Stop this
session at the completed source increment; do not start the release implementation.
