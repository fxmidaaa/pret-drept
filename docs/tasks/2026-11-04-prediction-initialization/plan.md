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
| Remote CI | Unavailable for the local patch |

The full suite ran with `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a07-probe-mpl NUMBA_CACHE_DIR=/private/tmp/pret-drept-a07-20261104/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`. To reproduce the synthetic tests alone, add `tests/foundations/test_prediction_initialization.py` to that command. Source checks follow the development guide, plus `.venv/bin/ruff check predict.py` and `git diff --check`.

Recovery: Review A07 on `fix/repository-audit` at `894a016` and preserve the eight local A03–A06 evidence files. Obtain approval of the proposed publication, then verify CI for the pushed commit.
