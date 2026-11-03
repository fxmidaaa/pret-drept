# A03 option 2 — retry unsuccessful collection

Date: **2026-11-03**. Task: [RP-20261103-A03](../tasks/2026-11-03-scraper-retry/task.json). Branch: `fix/repository-audit`; baseline `48ddb57`. Approved implementation is locally verified. No commit/push, live acquisition, data migration or training occurred.

## Result and review

Failed detail requests previously produced permanent rejection markers; failed search requests looked like the end of results. Both counterexamples were reproduced against unchanged code with synthetic inputs: **two expected test failures**.

The scraper now leaves failed, unavailable or malformed details outside completed state. Other successful rows and verified ineligible markers still save through the unchanged A02 atomic checkpoint path. A later run can retry unresolved listings if search returns them again. Existing accepted/rejected records retain their resume behavior; old rejection reasons cannot be reconstructed and are not reinterpreted.

HTTP errors, exhausted transport/JSON retries, GraphQL errors and malformed search responses cannot produce normal exhaustion. Search failure stops pagination; detail failure permits other page progress to be saved before `AcquisitionError` reports incomplete collection. The CLI exits **1** for incomplete runs. Valid empty search results remain a successful end condition. Request attempts remain bounded at three, with waits only between attempts. No durable queue, additional retry policy or dependency was introduced.

Response shape and listing identity checks prevent incomplete or mismatched details from becoming completed rows. Missing/invalid eligibility fields remain unresolved instead of being treated as proof of ineligibility. Diagnostics contain static messages and counts; raw response bodies, exception text and listing identifiers are not echoed. Unexpected programming errors propagate rather than being silently converted to rejection.

The change stays within specification §§4.3, 6, 8.3 and 18.1: acquisition is independent of ML/harness code, historical observations remain recoverable and failures are explicit. Six existing storage/key/value-normalization functions are AST-identical to the baseline. ML/API/training, dependency pins, CI configuration, private files and prior A01/A02 task records are unchanged. README and development instructions explain the changed exit/retry behavior. No effective trusted policy changed.

## Executed verification

Environment: existing CPython **3.13.16**, macOS ARM64, existing locked dependencies and local legacy model. All acquisition tests use synthetic files/responses and block live requests. CLI checks execute the real entry point in-process under the same interception.

| Check | Final result |
|---|---|
| Focused scraper suite | **63 passed**, 0 failed/skipped, 0.39 s; includes 32 new acquisition regression cases |
| Full local suite after final source/test edit | **205 passed**, 0 failed/skipped, 4.03 s; one existing Starlette/httpx deprecation warning |
| Scoped Ruff check and format | **Passed**; 23 files already formatted |
| Pinned actionlint workflow semantics | **Passed** |
| Architecture dependency command | **Passed**; existing A05 limitations remain |
| Preservation | **Passed**; four private/prior-record digests, six unchanged functions and seven ML/API/dependency/CI files |
| Task-record reload, changed-document links, final scope/whitespace checks | **Passed** |
| Exact-commit remote CI | **Unavailable** for this local patch; no publication requested |

Regression coverage includes the real request/helper/collection path across failed-then-successful runs; mixed unresolved/successful/ineligible pages; reuse of existing rejection markers; malformed/mismatched details; missing eligibility; bounded HTTP/transport/JSON failure handling; GraphQL error redaction; malformed/prematurely empty/inconsistent search results; ordinary empty results; progress preservation after later search failure; and nonzero CLI exit for search and detail failures.

Commands (run from the repository root):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short tests/test_scrape.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a03-20261103/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a03-20261103/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/actionlint -shellcheck= -pyflakes=
PYTHONDONTWRITEBYTECODE=1 .venv/bin/rent-check-architecture --root .
git diff --check
```

Synthetic probe logs and preservation digests are under `/private/tmp/pret-drept-a03-20261103`; no row-level private data or large logs were committed. The final suite supersedes the earlier 202-test pass before the last review cases were added. Only the two intentional pre-fix reproductions failed; no unresolved final failure or skip remains.

## Limits and exact next recovery action

Failed IDs are not queued durably. Unavailable listings remain unresolved; retry depends on encountering them again. Existing rejection markers may include historical failures. Search contents can change between requests, and success does not certify market coverage, observation chronology or a dataset release. A04 field policy and later ingestion architecture remain separate decisions. No live provider behavior, runtime isolation, model quality or production readiness is certified. This is an implementing-agent review, not independent protected verification.

Recovery: read the [task record](../tasks/2026-11-03-scraper-retry/task.json), confirm `fix/repository-audit` still has baseline `48ddb57` plus this bounded local patch, inspect the diff and reproduce the commands above. The approved implementation is complete locally. Obtain user approval of the branch and proposed commit message before publication; inspect exact-commit CI only after authorized publication. Other audit fixes and any real acquisition/migration require separate approval.
