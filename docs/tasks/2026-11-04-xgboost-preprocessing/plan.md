# RP-20261104-A10 fitted XGBoost preprocessing

The user approved the bounded first increment of option 2 on `fix/repository-audit` at `c4b91ea`. This L1 task makes the current XGBoost pipeline's fitted preprocessing explicit under architecture v1 §10.2. Future model adapters can reuse the component. Preserve the prior A03–A09 evidence.

1. Reproduce the median drift through the real legacy export path with synthetic rows and stub estimators.
2. Give a model-specific component ownership of the fitted vectorizer, ordered feature names and imputation medians. Export these through the legacy bundle with the effective numeric defaults expected by legacy callers. Keep serving-only defaults separate from fitted imputation.
3. Reuse the saved vectorizer and exact medians in prediction. A legacy bundle without explicit imputation medians uses its stored numeric defaults. Keep sector-based coordinate estimates as a serving rule.
4. Verify the exact median and transformed input across export and reload. Run relevant tests and source checks. Verify the package and legacy Docker source allowlist. Present the local patch for publication approval.

The increment uses synthetic regression fixtures and the existing test artifact for inference checks. Native adapter payloads, additional model families and actual retraining belong to separate work.

## Verification

The synthetic legacy export failed its regression before the fix. It saved 25 floors after filtering although imputation had fitted 20. The updated export records 20 and keeps the serving-only photo-count default at 7. After reloading the temporary bundle, direct prediction supplies identical encoded rows to the stub model. A legacy-shaped bundle continues to use its stored numeric defaults.

| Check | Result |
| --- | --- |
| Synthetic preprocessing round-trip | Passed using real imputation, market-rate filtering, vectorization and bundle serialization with stub estimators |
| Full local suite | 257 passed, zero failed or skipped, one existing Starlette warning |
| Source checks | Scoped Ruff lint and format, legacy train/predict lint, actionlint, architecture CLI and whitespace checks passed |
| Package build | Built sdist and wheel from temporary source. Imported the fitted component from the wheel with site packages disabled. Dependency metadata matches baseline. |
| Docker source packaging | Network-disabled scratch build exercised the actual ignore file and Dockerfile COPY instructions. The exported legacy API imported the component and all exclusion canaries stayed out. |
| Full inference container runtime | Skipped. Verification used a source-copy build and import probe. |
| Preservation | All fourteen prior evidence digests match. Requirements, lock and package dependency declarations match Git. |
| Remote CI | Unavailable for the local patch |

Run `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a07-probe-mpl NUMBA_CACHE_DIR=/private/tmp/pret-drept-a10-20261104/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short` for the full suite. Add `tests/foundations/test_xgboost_preprocessing.py` for the focused round-trip test. Use the development guide's source checks plus `.venv/bin/ruff check train.py predict.py` and `git diff --check`. The isolated package and Docker smoke artifacts are under `/private/tmp/pret-drept-a10-20261104`.

Recovery: Review the A10 patch at `c4b91ea` on `fix/repository-audit`. Keep the fourteen earlier evidence files separate. Obtain publication approval for `fix(xgboost): preserve fitted preprocessing in legacy bundles` and verify CI for the pushed commit.

The user approved publication by asking to push the proposed commit. Verify CI after publishing `fix(xgboost): preserve fitted preprocessing in legacy bundles` to `fix/repository-audit`.
