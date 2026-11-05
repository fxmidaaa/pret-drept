# RP-20261104-A09 apartment relationship validation

The user approved option 1 and asked to keep dependencies stable. Work on `fix/repository-audit` at `a8b6a1c`. This L1 change covers shared domain checks, the legacy prediction entry points, the canonical apartment contract and the minimal Docker source allowlist. Architecture v1 §5.2 assigns cross-field checks to the domain. Preserve prior A03–A08 evidence.

1. Define one standard-library-only rule set. Reject floors above the building, kitchens larger than the apartment, and incomplete coordinate pairs. Allow equality, omitted optional kitchen area, and absent or null coordinate pairs. Compare geometry where both values are available.
2. Validate direct prediction before loading the model. Translate the shared domain error into field-specific HTTP 422 details without echoing submitted values. Keep the existing sector estimate for absent coordinates and existing legacy request parsing.
3. Apply the same rules after structural apartment validation so batch prediction correspondence also rejects inconsistent records. Keep the same schema version and dependency lists. Classify the shared package as public domain contract code. Use the source path for the legacy application and the installed package path for the wheel.
4. Verify both entry points, canonical validation, packaging, and the isolated legacy source layout. Run the full suite and source checks. Record recovery and present the patch for review.

## Verification

Before the fix, all twelve invalid-input cases failed their new checks across HTTP, direct prediction and canonical validation. The three valid controls passed. The corrected HTTP path returns field-specific 422 details without echoing request values. The direct entry point rejects invalid relationships before model loading. The canonical Python validator applies the same rules after JSON Schema validation.

| Check | Result |
| --- | --- |
| Relationship regressions | All 15 passed in the full run |
| Full local suite | 256 passed, zero failures or skips, one existing Starlette warning |
| Source checks | Scoped Ruff lint and format, actionlint, architecture CLI and whitespace checks passed |
| Package build | Built the sdist and wheel from temporary source. Imported the domain package from the wheel and verified the existing dependency metadata and the incomplete-coordinate rejection. |
| Docker source packaging | Network-disabled scratch build exercised the legacy Dockerfile COPY instructions and the actual ignore file with synthetic fixtures. It exported both domain files and excluded contract, raw data, test and extra domain canaries. |
| Legacy import | Imported the exported domain package with site packages disabled. Imported the exported API in the existing development environment and verified HTTP 422 with a stubbed model boundary. |
| Full inference container runtime | Skipped. Verification used a source-copy smoke build and the exported source. |
| Preservation | All twelve earlier evidence files match their pre-edit digests. Requirements, lock and package dependency declarations match Git. |
| Remote CI | Passed for c4b91ea. 244 passed, 12 skipped because the private model is absent, one test warning. [Run 41809961842](https://github.com/fxmidaaa/pret-drept/actions/runs/41809961842) |

Run `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a07-probe-mpl NUMBA_CACHE_DIR=/private/tmp/pret-drept-a09-20261104/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short` for the full suite. Add `tests/foundations/test_apartment_relationships.py` for the focused checks. Build and Docker smoke artifacts are under `/private/tmp/pret-drept-a09-20261104`. The wheel uses the existing discovery under `src`. The legacy app imports the same source via the checkout's `src` namespace.

Recovery: Confirm `fix/repository-audit` at `c4b91eac786e9d1cf21058ee956b310e41bd4c43`. Preserve local A03–A09 evidence. Publication of evidence updates requires separate approval.

The user approved publication with message `fix(validation): enforce apartment field relationships` on `fix/repository-audit`. Verify CI for the published commit.

GitHub confirmed `c4b91ea` on `fix/repository-audit`. Workflow validation, static checks, dependency checks, tests and the distribution build passed. The test log reported 244 passes and 12 private-model skips in 2.70 seconds. [Run 41809961842](https://github.com/fxmidaaa/pret-drept/actions/runs/41809961842)
