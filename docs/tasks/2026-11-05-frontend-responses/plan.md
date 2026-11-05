# RP-20261105-A16 frontend responses

The user approved audit A16 option 2 on 2026-11-05: a small response adapter with
runtime validation, separate safe rendering, explicit dropdown loading failures,
and regression checks. Implementation approval does not authorize a push.

Risk: **L1**. Start from `fix/repository-audit` at `d9ac405`. The existing local
report-consistency plan and task record are prior evidence and must stay byte-identical.

## Plan and affected modules

1. Keep the frontend in `app/index.html` so the existing homepage, API routes and
   Docker copy remain compatible. Separate response parsing, request classification,
   rendering and form orchestration into small functions with documented JS types.
2. Validate only response fields consumed by the page. Preserve successful legacy
   predictions with and without asking-price verdicts; tolerate unused extra fields.
   Handle 422 validation, other HTTP failures, malformed JSON/schema and network errors.
3. Render dynamic content through DOM text APIs. Associate recognized field errors
   with controls, clear stale results/errors on submission, prevent overlapping
   submissions, and restore the submission state after every completed request.
4. Load and validate all dropdown lists before enabling prediction. On loading
   failure, explain how to recover instead of leaving an apparently usable empty form.
5. Add offline response/controller/rendering regressions using Node's built-in test
   runner, wire them into unprivileged checkout CI, and perform a real-browser smoke
   check with synthetic responses. Keep test tooling out of inference dependencies.
6. Update the development guide, A16 summary, audit index and task evidence. Present
   the tested implementation and proposed commit message for separate push approval.

## Acceptance criteria

- A valid prediction retains the fair-rent, optional verdict and driver presentation.
- Recognized 422 field errors are useful and rendered as text; raw error objects,
  input/context payloads and server diagnostics are not dumped into the page.
- HTTP failures, network failures and malformed success responses do not reach the
  success renderer or masquerade as field-validation errors.
- Driver labels and validation text cannot create markup, even with hostile strings.
- Dropdown failures are visible; prediction stays disabled until valid options exist.
- Old estimates/field errors are cleared appropriately, duplicate requests are
  prevented, and a later successful submission recovers from a prior error.
- Regression checks run in checkout CI without a private model, live scraping or a
  frontend framework/build dependency. Existing API and packaging behavior is preserved.
- Prior evidence files retain SHA-256 digests `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2`
  (plan) and `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6` (task).

## Verification strategy

Run focused frontend regressions and browser smoke checks using synthetic responses,
then relevant Python checks, Ruff, workflow semantics, architecture, distribution,
documentation links, task-record validation and whitespace checks after the final edits.
Record exact commands/results and practical limits here. Remote CI is pending separate
publication approval; local checks do not certify production readiness or isolation.

## Progress and recovery

- Approved scope recorded before implementation. No A17/A18 work is included.
- Implemented parsing, request classification, text-only rendering and form/loading state
  in the existing page. Added 38 offline regressions and an unprivileged CI test step.
- Verified the setup action's immutable revision against the maintainer repository:
  [setup-node v6.5.0](https://github.com/actions/setup-node/commit/249970729cb0ef3589644e2896645e5dc5ba9c38).
  Read its `action.yml` to confirm Node 24 and `package-manager-cache: false` support.
  [Node 24.21.0 release](https://nodejs.org/en/blog/release/v24.21.0) was checked; it
  matches the installed local runtime. No dependency install was needed locally.
- Browser smoke used the actual page through a loopback-only synthetic fixture under
  `/private/tmp/pret-drept-a16.c8f48w`. The initial server bind was denied by the restricted
  environment; automatic review approved the same loopback fixture, after which the browser
  checks passed. The temporary server was stopped and the browser tab closed afterward.

## Verification evidence

| Check | Result |
| --- | --- |
| `node --test tests/frontend/*.test.cjs` | 38 passed, 0 failed/skipped. Node v24.21.0. |
| `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a16.c8f48w/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a16.c8f48w/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra` | Final rerun: 334 passed, 0 skipped, 5.44 s. One existing Starlette/httpx deprecation warning. |
| `.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed. |
| `.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed; 34 files already formatted. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/rent-check-architecture --root .` | Passed; runtime isolation is not assessed. |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | Passed using existing pinned actionlint 1.7.12. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_notebooks.py` | Passed for both tracked notebooks; cells were not executed. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_distribution.py` | Source archive and wheel each passed 142 tests. |
| Real-browser smoke | Passed against synthetic responses; observations below. |
| Final task records, local links, prior evidence and whitespace | Passed: 8 A16 files, 23 local links/anchors, all persisted task records, whitespace and both byte-identical prior evidence files. The focused task-record test passed. |
| Remote CI | Not run; push requires separate approval. |

The browser observed the floor-specific 422 correction and control associations, then
successful recovery. Valid predictions retained price, verdict and both driver directions.
`<b>Synthetic driver</b>` appeared literally, with zero `b`/`img` elements under the result.
Blank asking rent produced no verdict. Malformed success and 503 replies produced separate
messages and restored submission. Failed dropdown loading showed a refresh instruction with
submission disabled. These use synthetic data and do not establish model quality, every
browser's accessibility behavior or general security certification.

Final screenshot review caught an invalid-control border selector being overridden by the
existing input styles. The selector was corrected. All 38 frontend regressions and 334 Python
tests passed again on the final page. A fresh browser check confirmed the invalid border was
`rgb(216, 69, 62)` and returned to `rgb(227, 232, 240)` after correction, with cleared error
associations, zero injected elements and an enabled submit button. Final screenshots replaced
the earlier validation/success captures. The temporary server and tab were closed again.

Temporary screenshots: `validation.png`, `success.png`, `options-failure.png` and
`without-verdict.png` under `/private/tmp/pret-drept-a16.c8f48w`. The same directory retains
`browser_server.py`; rerun it from the checkout with
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a16.c8f48w/browser_server.py`.
It binds a printed loopback-only URL and serves the current page. Floor above building height
returns 422, area 42 returns malformed success, rooms 6 returns 503, and `/options-failure`
simulates failed dropdown loading. Other valid form values produce a synthetic 600 EUR estimate.
No private dataset, protected labels or production service was used by this fixture.

Repeat final scope, links, task-record and preservation checks with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python /private/tmp/pret-drept-a16.c8f48w/check_a16.py`
and all persisted task records with
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py`.
The final documentation edits were checked after source verification. No commit or push
has been made for A16. The two earlier local report-consistency updates are preserved;
they are outside the eight-file A16 implementation.

On recovery, inspect this task and the working diff on `fix/repository-audit`; preserve the
two prior evidence files. Run the documented checks for any further source changes and the
final documentation check after evidence edits. Present the completed A16 increment and
`fix(frontend): validate responses and render errors safely` as the proposed commit message.
Do not publish until the user separately approves; then verify CI for that exact revision.

## Current recovery pointer — 2026-11-05

Earlier checkpoints above are historical evidence, including their source/CI identities.
Current branch state and next actions are in the [audit index](../../reports/README.md#current-checkpoint-and-recovery)
and [completion plan](../2026-11-05-audit-completion/plan.md): `fix/repository-audit` at
`36e67b7` plus uncommitted audit work. Inspect actual status/diff and preserve all local
changes; do not restore an older branch tip or infer publication authorization.

The existing A16 page, frontend tests and CI additions were reviewed and retained. Fresh browser verification and the final aggregate checks are recorded in the [completion evidence](../2026-11-05-audit-completion/plan.md). The report-consistency plan/task remain byte-identical.
