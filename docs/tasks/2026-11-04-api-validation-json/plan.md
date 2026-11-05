# RP-20261104-A08 JSON-safe validation errors

The user approved option 2 on `fix/repository-audit` at `95b019e` and asked for a brief implementation summary and proposed commit message before deciding on publication. This L1 fix covers the legacy HTTP validation response and focused tests. Preserve existing local A03–A07 evidence and the architecture v1 interfaces.

1. Reproduce HTTP 500 for rejected nonfinite values with synthetic requests and no private model dependency.
2. Return HTTP 422 using FastAPI's existing validation detail structure. Encode nonfinite floats as JSON null, including within nested error input. Preserve finite values, field errors and request parsing behavior.
3. Verify NaN, both infinities, exponent overflow, nested invalid input and ordinary validation details. Run the full local suite and source checks. Present the patch and commit message for approval.

This change affects rejected requests. The legacy parser still accepts nonstandard numeric tokens in fields that validation ignores.

## Verification

The five nonfinite raw request cases returned HTTP 500 before the change. They now return HTTP 422 with the same field location and JSON null for the nonfinite numbers. The nested case also verifies that finite numbers and the string "NaN" survive encoding. The ordinary finite validation response matches its pre-fix detail exactly. Tests stub category validation and fail if an invalid request reaches prediction.

| Check | Result |
| --- | --- |
| Raw HTTP regressions | 6 passed |
| Full local suite | 241 passed, zero failures or skips, one existing Starlette warning |
| Source checks | Scoped Ruff lint and format, Ruff lint for api.py, pinned actionlint, architecture CLI and whitespace checks passed |
| Preservation | All ten pre-existing evidence files match their pre-edit digests |
| Remote CI | Passed for a8b6a1c. 229 passed, 12 skipped because the private model is absent, one test warning. [Run 41804561617](https://github.com/fxmidaaa/pret-drept/actions/runs/41804561617) |

Run `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a07-probe-mpl NUMBA_CACHE_DIR=/private/tmp/pret-drept-a08-20261104/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short` for the full suite. Add `tests/foundations/test_api_validation.py` for the focused tests. Follow the development guide for source checks, plus `.venv/bin/ruff check api.py` and `git diff --check`.

Recovery: Confirm `fix/repository-audit` at `a8b6a1cf89de3b55b178032e282aebddb7fb128c`. Preserve local A03–A08 evidence. Publication of evidence updates requires separate approval.

The user approved publication with message `fix(api): serialize nonfinite validation inputs safely` on `fix/repository-audit`. Verify CI for the published commit.

GitHub confirmed `a8b6a1c` on `fix/repository-audit`. Workflow validation, static checks, dependency checks, tests and the distribution build passed. The test log reported 229 passes and 12 private-model skips in 4.20 seconds. [Run 41804561617](https://github.com/fxmidaaa/pret-drept/actions/runs/41804561617)
