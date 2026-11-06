# RP-20261106-M2-RELEASES — local DVC restoration

State: READY_FOR_REVIEW. Risk: **L1 engineering** under architecture v1 §§4–6, 8, 9 and
15–16. This implements the explicitly approved Option A: immutable development
release manifests and verified local DVC restoration using synthetic metadata.
No evaluation methodology, effective trusted policy or data access is changed.

## Authorization and starting state

The user approved the detailed Option A plan after a read-only design review.
Approval includes separate locked DVC tooling and Git/DVC operations in disposable
synthetic repositories and local stores. At completion provide a brief summary and
proposed commit message, then stop for the user's review. Repository commits/pushes,
PR changes, real/private data, acquisition, cloud storage, experiments, promotion
and deployment are outside this authorization. Task records grant no permissions.

Starting HEAD: `d920ffc89a2673945142c5eb6442a56069cc27d7`. Increment 2's 19-file
uncommitted implementation and the two unrelated reporting edits are preserved.
Starting status/diff and 167 nonignored file hashes live under
`/private/tmp/pret-drept-m2-releases-vjccaxd5`. Work moved to the new local branch
`feat/m2-local-dvc-releases` without changing HEAD or file contents. Private raw data
and model files were not read for discovery. The frozen specification, M0/A14,
development guide, current checkpoint and increment-2 task are the relevant context.

## Scope, modules and invariants

- `rent_contracts`: two new local versioned schemas, dataset release and restoration
  report; no weakening of existing requests, candidate limits or evaluation rules.
- `rent_data.releases`: pure release identity, manifest/candidate correspondence
  and report validation. Metadata revision precedes manifest construction.
- `rent_data.release_io`: exact artifact roster, SHA-256/size verification, exclusive
  staging and completion report. Existing destinations are not overwritten.
- `rent_data.dvc_local`: narrow pinned public-CLI adapter, local stores only,
  validated DVC metadata and controlled subprocess configuration.
- Separate DVC tool lock/environment; optional declared YAML dependency for data
  functionality; unchanged ML/runtime pins. Packaging, tests, unprivileged CI,
  architecture/development/evidence documentation are affected.

Git identifies DVC metadata; DVC preserves objects. Native DVC MD5 directory identity
and independent artifact SHA-256 are separate. Sealed development candidates are
not published/accepted datasets. Retention remains PENDING_REVIEW; no garbage
collection or automatic lifecycle advancement. Candidate source references remain
declarations about raw data; restoration verifies only supplied synthetic metadata.
No labels, matching, split selection, Parquet migration or training in this increment.

## Acceptance criteria

1. DVC 3.67.1 and its complete dependency closure are hash-locked separately and
   operate on Python 3.13 without changing the ML lock. Exact executable version
   is checked; absence/wrong version fails with setup guidance, never auto-install.
2. A closed development release manifest binds dataset/schema identity, exact Git
   metadata commit/path/SHA-256, DVC object identity, tool profile, artifact paths/
   SHA-256/sizes and existing candidate acquisition/transformation/policy/quality
   facts. Its canonical self-digest has no Git/DVC/candidate/report hash cycle.
3. Fixed payload: `candidate.json`, `quality-report.json`, and exact source bytes
   at `sources/<sha256>.json`. Preserve complete inventory/lineage and unknown facts.
   Refuse unsafe paths, extra/missing/nonregular files and symlinks.
4. Real DVC add/push/pull round trip through a local filesystem store succeeds in
   disposable synthetic repositories. Consumer workspace, object cache and tool
   configuration are separate from producer. No fallback to producer cache/latest.
5. Metadata is read from the exact recorded commit. Validate the supported `.dvc`
   profile before invoking DVC; reject imports/dependencies, output remote overrides
   and unsupported fields. The metadata revision must actually contain those bytes.
6. Restore A after producing B; recover identical bytes, observation population,
   lineage, uncertainty and report counts by rebuilding with increment-2 APIs.
   Recompute SHA-256 rather than treating DVC's object hash as integrity approval.
7. Corruption, absent objects, wrong refs, process failure/timeout, interrupted
   writes and existing destinations fail without a successful completion report or
   modification of prior completed artifacts. Only complete reverified outputs
   are accepted by the reader. Single-writer filesystem evidence is not isolation.
8. Reproducibility, negative/security-relevant contracts, source/wheel packaging,
   architecture, workflow, notebooks, frontend and checkout checks pass after final
   edits. Preserve earlier uncommitted work; record passed/failed/skipped/unavailable
   checks, exact recovery and remaining prerequisites. No M2 exit-gate claim.

## Implementation sequence

1. Persist task/authorization and baseline before source changes.
2. Add separate tool input/lock and ignored tool environment; resolve/install the
   approved public DVC package; verify actual CLI/metadata format/configuration in
   a small synthetic repository. If a material version/pin change is needed, stop
   for revised approval rather than changing the ML environment.
3. Implement two schemas and pure release/report integrity/correspondence functions.
4. Implement bounded payload I/O and exclusive finalization; no existing output
   replacement, raw CSV adapter or arbitrary archive extraction.
5. Implement controlled local DVC/Git CLI operations with explicit local paths,
   safe metadata parsing and bounded process timeouts/diagnostics.
6. Add unit, failure/recovery and real integration fixtures, including two revisions
   and an independent empty-cache consumer. Temporary fixture commits are allowed;
   this repository is never committed by tests or implementation.
7. Integrate optional dependency metadata, shipped deterministic tests, explicit
   integration prerequisites and read-only unprivileged CI setup/test steps.
8. Run relevant checks, inspect the final delta against the increment-2 baseline,
   persist evidence and stop READY_FOR_REVIEW with summary and commit message.

## Verification strategy and gates

Use CPython 3.13 and the existing locked development environment. DVC runs from a
separate environment. Its system/global config and site cache use owned temporary
directories; analytics/Studio/update behavior is disabled in that profile. Local
cache uses copies; no shared user cache/credentials/remotes or shell commands.
This is configuration/dependency control, not a certified OS security sandbox.

Deterministic tests cover schema rejection, digest/reference mismatch, malformed
YAML, path/roster/symlink violations, candidate/source/quality reconstruction,
immutable output/failure markers, process failure/timeout and old revision recovery.
Real successful integration uses the installed DVC executable. Missing tooling is
an explicit setup failure. Integration stays in checkout tests; source/wheel ship
the self-contained core tests. CI changes retain existing read-only permissions,
pinned actions and timeout, with runner paths only at valid step scope.

Commands/outcomes will be recorded here after execution. Run the development
guide's checkout pytest, source/wheel, scoped Ruff, architecture, actionlint,
notebook and offline frontend checks plus actual local DVC integration. Capture
safe logs/command results in the evidence directory; no row-level private data.

Risks: DVC dependency/platform compatibility is not proved by package metadata;
actual installation and integration decide it. DVC object IDs are not authorization;
independent hashes/reconstruction and an externally fixed release ref are required.
Raw data truth, projection approval, historical chronology/property identity,
scalable inventory transport, production remote/access/retention, protected
verification and reproducible baseline ML remain later gates. Unknown facts are
never replaced with assumed dates, identities, thresholds or benchmark results.

## Exact recovery

Run `git branch --show-current`, `git rev-parse HEAD`, `git status --short` and
`git diff --check`; read this task, approved scope, increment-2 record and current
report checkpoint. Expect `feat/m2-local-dvc-releases` based on `d920ffc`, carrying
the preserved earlier uncommitted work. Compare against `starting-files.json` and
`starting.diff`; do not restore an old branch tip or overwrite prior edits.
Continue only the recorded increment. Rerun affected checks after further edits.
If interrupted restore has no valid completion report, treat it as incomplete.
Delete only this task's owned disposable test resources when needed; no user data,
real cache garbage collection, repository commit/push or protected operation.

## Implemented decisions and architecture review

- The three modules follow the existing public contract/candidate patterns. There
  is no `rent_agent`, `rent_platform` or ML import in the data implementation, and
  no legacy interface or evaluation methodology changed.
- The release self-digest binds the prior Git metadata commit and artifact roster.
  DVC's MD5 directory object is retained separately from independent SHA-256 checks.
  Manifests/reports stay outside the DVC payload. Expected release references must
  come from the caller's independent context; local digests are not authentication.
- Canonical candidate/quality bytes and exact original source envelopes are restored.
  All records, eligibility issues, unknown acquisition periods, times and unresolved
  property identities survive reconstruction. Nothing is silently selected/dropped.
- Only a development `SEALED_CANDIDATE` with pending retention is supported. Local
  object recovery is implemented, while publication, source-data truth, protected
  access and effective retention remain external. No DVC project was initialized in
  this checkout; fixtures use owned temporary repositories/stores.
- The supported `.dvc` profile is deliberately narrow, including rejection of
  per-output remote overrides, imports, aliases and duplicate YAML keys. Metadata
  from the exact commit is checked before recovery, and existing metadata before
  retracking. Consumer config/cache is independent of producer/global user state.
- The backend bootstrap was made explicit after noticing ANTLR uses an sdist.
  Both data locks now bind setuptools 82.0.1; source build isolation is disabled
  after installing that pinned backend. A fresh pip installation, including a fresh
  ANTLR build, verified the same setup used in CI. The original ML locks are unchanged.
- Exclusive destinations and the atomic report marker define local single-writer
  completion. Interrupted outputs lack a valid marker. Reader-side rehashing detects
  later changes. This does not certify power-loss durability, host quotas, hostile
  subprocess/storage isolation or independently authenticated verification.

| Frozen requirement | Evidence and practical limit |
| --- | --- |
| §§8.1–8.2 responsibility/identity | Exact Git/DVC metadata and native object identity plus independent artifact SHA-256; full source/acquisition/transform/schema/quality facts. Raw-source references remain declarations. |
| §§8.3–8.5 lifecycle/restoration | Actual local push/pull, old revision recovery, pending retention, no overwrite/publication/GC. Production access/retention still undecided. |
| §9 identities/time/population | Existing contracts and candidate rebuilding preserve uncertainty and full membership. No split materialization, feature-lineage proof or policy activation. |
| §§6, 15–16 engineering evidence | Persistent L1 task, explicit approval, synthetic negative/integration checks, source/wheel tests and unchanged dependency boundary checker. No trusted-runtime or M2 gate claim. |

## Verification — final implementation

CPython **3.13.16**, macOS ARM64; Node **24.21.0**, Ruff **0.17.3**,
actionlint **1.7.12**, PyYAML **6.0.3**. DVC **3.67.1** runs in a separate tool
environment. The universal data lock has **99 pins**; **97 active pins** were checked
against the fresh macOS installation. Platform markers do not establish Linux or
Windows execution success.

Evidence directory: `/private/tmp/pret-drept-m2-releases-vjccaxd5`. The explicit pip
bootstrap/tool-install commands in [development setup](../../development.md#separate-local-data-tools)
passed in its fresh `pip-dvc-tools` environment, using public PyPI, `--require-hashes`,
`--no-cache-dir` and `--no-build-isolation`. The earlier `.venv-data-tools` installation
and real DVC probe also passed; ANTLR was explicitly rebuilt using the pinned backend.
No setup operation changed ML pins or installed DVC into the ML environment.

`verify.py` in that directory records exact commands, durations, return codes and
safe logs. It sets `PYTHONDONTWRITEBYTECODE=1`, `RENT_DATA_DVC` to the fresh tool
executable and Matplotlib/Numba caches to owned temporary directories. Static,
checkout and distribution groups ran after the final implementation/schema/test/
workflow/dependency edits; no implementation file changed afterward. Final
documentation/task edits are followed by the documentation/preservation and task
checks below, with all 20 implementation hashes frozen.

| Check/command | Final result |
| --- | --- |
| Fresh tool setup; `pip check`; actual `dvc --version`; installed-pin comparison | **Passed**. DVC 3.67.1, setuptools 82.0.1; all 97 active lock pins match, no broken requirements. A cache-permission warning on offline `pip check` simply disabled its cache. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_dataset_releases.py tests/foundations/test_release_io.py tests/foundations/test_dvc_local.py tests/foundations/test_ci_source.py` | **115 passed**. Includes 110 new core release/IO/adapter cases and five CI checks. No failed/skipped checks. |
| Actual DVC checkout integration | **10 passed** within the final full suite: two revisions, B then A restored into fresh caches, absent/corrupt directory/corrupt artifact objects, wrong refs/commits/bindings, existing output and changed config rejection. Successful recovery uses real DVC, not a mock. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` | **690 passed**, zero failed/skipped; 12 existing private-model regression checks ran against synthetic requests without training. One existing Starlette/httpx deprecation warning; no dependency update made to hide it. |
| `.venv/bin/python scripts/check_distribution.py` | **487 passed** from extracted source and **487 passed** against the wheel, including all 15 local schemas. Editable checkout bypassed. Integration requires checkout tooling and is not shipped as a package test. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | **Passed**. New runner-dependent tool path is at step scope; regression also rejects it at job scope. Existing read-only permissions, pinned actions and timeout preserved. |
| `.venv/bin/python scripts/check_notebooks.py` | **Passed**, two tracked notebooks; no execution or saved-output changes. |
| `node --test tests/frontend/app.test.cjs` | **38 passed**, no failures/skips. UI source unchanged. |
| Scoped `ruff check` and `ruff format --check` from the development guide, including `tests/integration` | **Passed**, all checks and 46 formatted files. |
| `.venv/bin/rent-check-architecture --root .` | **Passed**; runtime isolation is not assessed. Checker/policies unchanged. |
| `.venv/bin/python /private/tmp/pret-drept-m2-releases-vjccaxd5/check_documentation.py` | **Passed** after evidence updates: 167 baseline files accounted for, 155 byte-identical and 12 shared files recover their exact baseline by reversing only this increment's additions. Scope: 17 new / 29 increment files; 20 implementation hashes frozen; both unrelated reporting files and prior increment-2 source/tests/tasks preserved. All 23 task records, Markdown links/anchors, 15 schemas, branch/HEAD, empty index and whitespace checked. |

Earlier failures, resolved before final verification:

- Initial core run: **105 passed / 1 failed**. A brittle fixture assertion searched
  for the substring `target`, which also occurs in the legitimate
  `invalid_non_target_domain` reason. Removed that assertion; field closure and
  unchanged eligibility tests provide the actual boundary evidence.
- Initial integration run: **8 passed / 2 failed** before corruption was injected:
  copied DVC objects retained read-only permissions. The fixture now makes only
  its owned copied object writable and corrupts the exact A artifact. Original
  producer/store bytes remain unchanged. All three negative-store cases passed.
- Initial documentation proof script reconstructed a fixture file with an extra
  newline. Corrected the temporary checker; repository content did not change.
  The exact baseline hashes then matched. Earlier Ruff format/import findings were
  corrected before final static checks; none remains outstanding.

| Status | Deferred check | Exact recovery action |
| --- | --- | --- |
| **Skipped** | Real/private input, acquisition, actual dataset publication/production remote, raw-source preservation and scalable table transport | First obtain authorized reviewed projection/data handling and storage/access/retention/quality decisions, design bounded scalable transport, and establish defensible chronology/identity evidence. Use a separate reviewed increment; do not scrape/enrich or apply policies by implication. |
| **Skipped** | Model experiments/benchmarks, feature/target-aggregate execution, protected labels/runtime and promotion/deployment | After approved input/split policies and isolated runtime exist, request the appropriate external authorization and perform exact-source reproducible runs/independent verification. Local metadata tests cannot substitute. |
| **Skipped** | New browser smoke check | UI is unchanged and its 38 offline checks pass. Run a synthetic browser smoke test if a later increment changes that boundary. |
| **Unavailable** | Linux CI for this revision | Source is intentionally uncommitted/unpushed. After user review and explicit publication authorization, publish the exact approved revision and inspect that revision's Linux CI; prior merged PR evidence is historical. |
| **Unavailable** | Production access/isolation/retention enforcement and independent protected verification | Responsible external owners must provision/review supported storage, access, retention and trusted runtime/CI controls, then verify their effective state. Do not grant credentials through task records or source proposals. |
| **Unavailable** | M2 reproducible-run/development-evaluation exit evidence | Resolve authorized chronology or approved remediation, reviewed property identities, fixed split/policies, scalable release transport and isolated baseline runs. M0/A14 remain binding limitations; do not substitute fabricated dates or historical random scores. |

No unresolved required local check failed. Further source changes require rerunning
the affected command and its dependent checks; documentation-only evidence changes
require the final task/link/preservation checks. Retain failed restore destinations
as incomplete or inspect/remove only owned synthetic resources before retrying at
a fresh path. The local `/private/tmp` logs are supplemental, not durable trusted
evidence; persistent outcomes and exact recovery remain in this task/report.

## Handoff and later increments

Outcome: **READY_FOR_REVIEW**, implementation of approved increment 3 only. HEAD
remains `d920ffc89a2673945142c5eb6442a56069cc27d7`; nothing is staged, committed or
pushed. All pre-existing changes are preserved. No raw/private dataset inspection,
acquisition, protected labels, training, effective policy activation or promotion/
deployment occurred. Existing model regression tests do not repair A10's missing
fitted medians or A14's evaluation gaps. M2's exit gate remains open.

The **single recommended next increment** is a deterministic development-split
materializer consuming a verified sealed metadata release and an explicitly reviewed
policy, producing the existing `development-split` contract. Use synthetic inputs
first, fixed full membership/exclusions and temporal/property/population invariants.
No training in that increment. Before real data: review eligibility/cutoff/unseen and
projection policies; provide authorized defensible chronology or approved remediation
and reviewed property pairs/matching policy; decide permissible inputs, storage/
access/retention/quality requirements; and support scalable inventory transport.

Dependency-ordered work after that: reviewed/scalable real-data release preparation
and actual approved-storage recovery; training-only transformation/target-aggregate
boundaries; independent XGBoost/CatBoost baseline adapters; reproducible isolated
development runs and dual-view evaluation. TabPFN and protected acceptance retain
their own later eligibility/runtime/governance gates. None is started here.

On recovery run the commands in **Exact recovery**, this task's final documentation
checker and task-record checks. Review only the 29-file increment against the
captured baseline; retain increment 2 and the two unrelated edits. Wait for the
user's second review. Proposed commit message (no commit performed):
`feat(data): add local DVC release sealing and verified restoration`.

## Source publication follow-up

After the implementation review, the user explicitly requested **"push please"**.
This authorizes source commit/push on `feat/m2-local-dvc-releases`; the earlier
no-commit/no-push and second-review-wait statements above are historical. M2's
data/evaluation/protected gates remain open. No merge, PR creation, data publication,
ML experiment or deployment is included in this follow-up.

Publication plan: verify the saved source hashes and exact baseline; commit the
19-file increment-2 dependency from its recorded, verified bytes first, then the
29-file release increment and this authorization/recovery update. Stage explicit
paths only; exclude both unrelated report-consistency files, private data, local
environments and caches. Review each index against its expected paths/content and
run whitespace, task/link and workflow checks after documentation edits. Push the
feature branch without force or changes to `main`, verify remote HEAD, then inspect
Linux CI for that exact revision. Persist source-publication evidence afterward.
Any further implementation changes require the corresponding development checks;
unchanged code retains its recorded local evidence.

Recovery during publication: inspect actual branch/HEAD/index before resuming.
Do not replay the old empty-index/`d920ffc` assertions after creating a commit;
compare the actual commit trees with the captured increment baselines instead.
Preserve all working-tree files and the two unrelated edits. If push fails, retain
local commits and retry only the same feature branch after inspecting the remote;
do not force push, reset, merge or recreate credentials. A pending/failed Linux run
must remain explicit until its exact revision passes.
