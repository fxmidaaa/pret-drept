# RP-20261104-A07 concurrent prediction initialization

The user approved option 1 on `fix/repository-audit` at `894a016`. This L1 fix covers the legacy prediction loader and focused tests. Keep the API, CLI, model format and architecture v1 interfaces. Preserve the existing local A03–A06 evidence.

1. Reproduce partial publication with a synthetic bundle and two threads. Build and publish the complete bundle under a process-local lock.
2. Verify that concurrent first calls wait for one complete bundle and that a failed explainer initialization leaves the cache empty for a retry. Use synthetic stubs for both regressions.
3. Run focused and full tests, architecture and source checks, and evidence preservation checks. Record results and recovery before review. Publication requires separate approval.

## Verification

Both synthetic tests failed before the patch because the shared bundle already held an incomplete model. After the patch, the waiting caller receives the same complete bundle and an explainer failure leaves the cache empty for a successful retry. Cache hits take the same lock briefly. Predictions execute after the accessor releases it.

| Check | Result |
| --- | --- |
| Synthetic initialization regressions | Both passed in the full run. They use stubbed model loading and SHAP construction. |
| Full local suite | 235 passed, zero failed or skipped, one existing Starlette warning |
| Source checks | Scoped Ruff lint and format, Ruff lint for predict.py, pinned actionlint, architecture CLI and whitespace checks passed |
| Preservation | All eight pre-existing evidence files match their pre-edit digests |
| Remote CI | Passed for 95b019e. 223 passed, 12 skipped because the private model is absent, one test warning. [Run 41731227832](https://github.com/fxmidaaa/pret-drept/actions/runs/41731227832) |

The full suite ran with `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a07-probe-mpl NUMBA_CACHE_DIR=/private/tmp/pret-drept-a07-20261104/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`. To reproduce the synthetic tests alone, add `tests/foundations/test_prediction_initialization.py` to that command. Source checks follow the development guide, plus `.venv/bin/ruff check predict.py` and `git diff --check`.

Recovery: Confirm `fix/repository-audit` at `95b019e74e79e8b8a268acd32ff3e94928b77e36`. Preserve the local A03–A07 evidence. Publication of evidence updates requires separate approval.

The user authorized publication. GitHub confirmed commit `95b019e` with message `fix(predict): serialize lazy model initialization`. Workflow validation, static checks, dependency checks, tests and the distribution build passed. The test log reported 223 passes and 12 private-model skips in 3.89 seconds. [Run 41731227832](https://github.com/fxmidaaa/pret-drept/actions/runs/41731227832)
