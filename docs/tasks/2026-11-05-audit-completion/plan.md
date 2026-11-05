# RP-20261105-AUDIT-FINAL — remaining audit fixes

Authorized by the user's 2026-11-05 request. Risk: **L1** source/test/documentation work
under frozen architecture v1 §§6.2–6.8 and 7.2–7.3. No trusted policy is activated.

## Starting checkpoint and preservation

`fix/repository-audit` is at `36e67b7`, following the reviewed A17 source and evidence.
Uncommitted A16 work spans the existing page, Node tests, unprivileged CI step,
development guide, report/index and task record. The two unrelated report-consistency
plan/task updates must remain byte-identical. Starting files, diff and SHA-256 digests
are retained under `/private/tmp/pret-drept-audit-final-w6tw2k5l` (also recorded in
`task.json`). No model or dataset is copied or inspected for this checkpoint.

## Plan and affected modules

1. Review A16's response adapter, safe text rendering and loading/submission controller;
   retain the existing candidate and test the actual script plus a synthetic real browser.
2. Reproduce A18's non-UTF-8 byte decoding and direct-constructor validation bypass.
   Fix `rent_contracts.validation` and `requests` with meaningful contract regressions.
   Keep `from_document` compatible; require registered schemas for direct construction.
3. Correct the M0 baseline inventory against its exact Git tree, clarify runtime versus
   development installation in README/development documentation, and document the public
   construction/encoding contract. No dependency or frozen wire-schema changes.
4. Reconcile current recovery pointers with actual Git state while retaining dated
   historical checkpoints. Keep unrelated reporting work unchanged.
5. Keep A10 and A14 incomplete in summaries/current records. Record the missing legacy
   median provenance and temporal/property/cohort prerequisites and next actions.
6. Run relevant checks after final edits, persist passed/failed/skipped/unavailable
   outcomes and finish with a reviewable uncommitted diff and exact recovery action.

## Acceptance criteria

- Strict UTF-8 bytes and text succeed; UTF-16/32, BOMs and invalid encodings fail safely.
- Ordinary request construction requires a schema registry and validates the envelope
  and model configuration; canonical storage/digest stay independent of caller mutation.
- A16 rejects invalid status/schema, shows useful safe 422 messages, renders HTML-like
  strings literally, gates on options and recovers after failed/duplicate submissions.
- M0 correctly records **25 tracked files and five root Python modules** at `e08344d`.
- Runtime installation and the locked development/test setup have distinct commands.
- Current pointers resolve through the audit index to `36e67b7` plus this working diff;
  historical evidence and unrelated report-consistency files are preserved.
- A10's future-export repair does not certify the existing artifact; A14 documentation
  does not close target-dependent evaluation or implement the dual benchmarks.

## Verification strategy

Use synthetic contract fixtures and frontend fetch responses. Run Node regressions and
synthetic browser checks, then Python checkout tests, scoped Ruff, actionlint, architecture,
notebook publication, source/wheel tests, task/link/whitespace and preservation checks.
Keep temporary caches/evidence outside the checkout. No training, scraping, private-data
migration, protected labels, history rewrites, policy activation, promotion, deployment,
commit or push. Remote CI and protected/runtime acceptance are separate from local checks.

## Evidence and current recovery

The A18 regressions reproduced the original gaps before repair: **14 failed, two passed**
in the focused selection. An initial Ruff format check failed and was corrected. The
first aggregate run then caught a new test expecting `ValueError` for a missing dataclass
InitVar; this Python raises `TypeError`. The assertion now checks rejection using the
supported exception variants. That run had 352 passes/one failure; its source-archive
run had 160 passes/one failure, and the wheel test did not start. The final runs below
supersede those failures. No product validation was loosened to make the test pass.

### Final verification

Executed on CPython **3.13.16**, Node **24.21.0**, macOS ARM64 after the last source/test
edit. `PYTHONDONTWRITEBYTECODE=1` was set; temporary Matplotlib and Numba caches used
`/private/tmp/pret-drept-audit-final-w6tw2k5l/{matplotlib,numba}`.

| Check / exact command | Final result |
| --- | --- |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra` | **353 passed, 0 failed, 0 skipped**, 5.61 s; includes all 84 contract tests and existing model-backed inference regressions. One existing Starlette/httpx deprecation warning. |
| `node --test tests/frontend/*.test.cjs` | **38 passed, 0 failed/skipped**. Final logged run names the sole `app.test.cjs` file explicitly. No network/model access. |
| `.venv/bin/python scripts/check_distribution.py` | Source archive **161 passed**; wheel **161 passed**, zero failures/skips. Built from current source; no inference certification. |
| `.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed. |
| `.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed, 34 files already formatted. |
| `.venv/bin/rent-check-architecture --root .` | Passed; runtime isolation is not assessed. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | Passed with existing pinned actionlint 1.7.12; no CI privileges changed. |
| `.venv/bin/python scripts/check_notebooks.py` | Passed for two tracked notebooks; neither executed. |
| `UV_CACHE_DIR=/private/tmp/pret-drept-audit-final-w6tw2k5l/uv-cache uv pip check --python .venv/bin/python --offline` | Passed; all 58 installed packages compatible. |
| Synthetic Chrome browser | Passed; observations below. |
| `.venv/bin/python /private/tmp/pret-drept-audit-final-w6tw2k5l/check_audit.py` | Passed after evidence edits: 56 changed files including prior work, 30 Markdown files, 128 local links/anchors, 20 task records, 18 historical pointers, baseline tree and five starting digests. |
| `.venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py` and `git diff --check` | Passed after evidence edits: one task-record test; whitespace clean. |
| Remaining failed checks | **None** after correction and final reruns. |
| Full inference-container / protected runtime tests | **Skipped**; outside this source increment. Static checks do not certify isolation. |
| New-revision remote CI | **Unavailable** for the uncommitted tree; commit/push are not authorized. Historical CI links were retained, not re-certified for this diff. |
| A10 exact-artifact closure / A14 official benchmarks | **Unavailable** pending the prerequisites below; no rebuild or evaluation was attempted. |

The optional `python -m pip check` command was unavailable because this existing environment
has no pip module. The first offline uv alternative could not write its default cache;
the exact writable-cache command above passed. No dependency was installed or changed.

Logs and machine-readable command results are retained in the evidence directory as
`checkout-0.log`, `distributions-0.log`, `frontend-0.log`, `static-0.log` through
`static-5.log` and corresponding `*-results.json`. `static-5.log` retains the unavailable
pip invocation. `run_check.py` repeats those groups; use the successful uv alternative
above for dependency compatibility. These temporary files are convenience evidence;
the source commands and outcomes here are the durable recovery record.

### Synthetic browser evidence

Used the actual unchanged page through the existing loopback-only fixture:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a16.c8f48w/browser_server.py
```

The initial bind was denied. Automatic review approved this same loopback fixture; it
served only invented replies at `127.0.0.1:59037`. The server was stopped and tab closed.
The fixture never loads a model/dataset or production service. Scenarios and observations:

- Floor 12/building 9 returned useful 422 text, `aria-invalid=true` and
  `aria-describedby=error-floor`; border was `rgb(216, 69, 62)`. Raw synthetic input was absent.
- Correction to floor 3 cleared both associations, restored border `rgb(227, 232, 240)`
  and yielded a 600 EUR estimate/verdict with an enabled submission button.
- `<b>Synthetic driver</b>` displayed literally; zero `b`/`img` elements were created
  under the result. Both driver directions rendered. Blank asking rent omitted the verdict.
- Area 42 returned malformed success; rooms 6 returned 503. Each showed its distinct
  error message and restored submission.
- `/options-failure` left all dropdowns empty, disabled submission and instructed a
  refresh; loading `/` again restored valid options and successful submission.

Screenshots `browser-success.png`, `browser-options-failure.png` and `browser-final.png`
are in the evidence directory. These are synthetic browser observations, not model-quality,
cross-browser accessibility or general security certification. If the temporary fixture
is absent on recovery, use the existing offline frontend fixtures to recreate these
invented scenarios; do not substitute the live service or private data.

### Git, preservation and remaining prerequisites

The baseline tree independently confirms 25 files and the five named root Python modules.
The scope probe checks **56 changed files including prior work**, all **20 task records**,
and **18 reconciled historical recovery pointers**. Old task histories, verification
references, plan text and prior recovery actions are retained. The pre-existing A16 page,
frontend tests and CI addition match their starting SHA-256 bytes, as do both unrelated
report-consistency files. The legacy model matches its previously recorded digest.
Legacy ML/API/acquisition code, dependencies, schemas and the frozen specification are
unchanged; no raw-data rows or protected labels were inspected for this work.

- **A10 incomplete:** future exports save fitted medians, but the current artifact has
  none. Preserve it/fallback; obtain independently recoverable fitted state with provenance
  or separately authorize an isolated reviewed-source rebuild on an immutable data release.
  Verify fitted state and fresh reload/input/prediction parity before exact-artifact approval.
  See [artifact prerequisites](../../reports/a10-xgboost-preprocessing.md#incomplete-artifact-prerequisites).
- **A14 incomplete:** target-dependent validation filtering and random splitting remain;
  temporal/unseen-property benchmarks are absent. Next propose/version eligibility and
  split/cohort contracts with synthetic leakage/population tests, then establish authorized
  observation history, reviewed property identities, immutable releases and isolated runs.
  See [benchmark prerequisites](../../reports/a14-evaluation-handoff.md#incomplete-benchmark-prerequisites).

No retraining, scraping, private-data migration, protected-label access, history rewrite,
effective-policy activation, promotion, deployment, commit or push was performed.

**Exact next recovery action:** inspect branch/HEAD/status/diff against `36e67b7`, read the
[current audit checkpoint](../../reports/README.md#current-checkpoint-and-recovery) and this
task, preserve every uncommitted file, and review the tested A16/A18 diff. After further
edits run the applicable commands above and the documentation/task/preservation checks.
Commit/push and real artifact/benchmark work require separate authorization; there is
no remaining authorized implementation action hidden behind that publication boundary.
