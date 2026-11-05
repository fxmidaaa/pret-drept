# RP-20261104-A12 public identifier formats

The user approved audit A12 option 1 on `fix/repository-audit` at `ee6549a`. This L1 task corrects format validation for the 28 fields that use identifier, SHA-256 digest, or reviewed Git commit patterns across the seven public v1 schemas.

1. Reproduce acceptance of a trailing newline with complete synthetic documents. Add regressions for every affected field, including nested and nullable fields.
2. Use standard JSON Schema length and character constraints to validate the complete value. Keep the schemas independently usable and preserve exact identity comparisons.
3. Document the format rules and verify the source, checkout suite, extracted source distribution, and wheel. Preserve all pre-existing audit evidence.
4. Present the reviewed patch and proposed commit message for separate push approval.

## Acceptance criteria

- All 28 affected fields reject a trailing newline and other disallowed characters. Invalid identifier and digest lengths are rejected.
- Valid identifiers, lowercase digests, both supported Git commit lengths, and the existing nullable alternatives remain accepted.
- The packaged tests exercise the same rules as checkout tests, and the repository task records remain readable.

## Verification

The regression tests use complete synthetic documents for all seven schemas. They exercise all
28 fields with valid boundary values, trailing whitespace and control characters, and other
out-of-format values. The existing tests cover the nullable checkpoint and reviewed-commit values.

| Check | Result |
| --- | --- |
| Identifier regressions | All 28 failed before the schema fix and passed afterward. |
| Standalone schema validation | All 28 changed fields matched the original grammar with full-string matching in 16,240 comparisons. The rest of each schema matched the baseline. |
| Full local checkout | 285 passed, zero failed or skipped, one existing Starlette warning. |
| Extracted source archive and wheel | 142 passed in each, zero failed or skipped. |
| Source checks | Scoped Ruff lint and format, pinned actionlint, architecture checks, and whitespace checks passed. |
| Prior evidence | All 18 pre-existing local documentation edits match their starting digests. |
| Remote CI | Passed on `d5583a5`. Checkout tests reported 273 passed and 12 private-model skips. The extracted source and wheel each passed 142 tests. [Run 41821705819](https://github.com/fxmidaaa/pret-drept/actions/runs/41821705819) |

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_contracts.py -k test_identifier_formats`
for the focused regressions. For the full checkout run
`PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/rent-a12-mpl NUMBA_CACHE_DIR=/private/tmp/rent-a12-numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`.
Use the development guide's source checks and `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_distribution.py`
for the source and wheel. The standalone probe and logs are in
`/private/tmp/pret-drept-a12-verification.mASAPI`. Run the probe with
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a12-verification.mASAPI/check_schema_grammar.py`.

The user approved pushing the reviewed A12 patch. GitHub confirmed
`d5583a537eaf6b9e637fcd2bfb8149657eec539a` on `fix/repository-audit`. Foundations
job `126546185591` passed. GitHub reported the existing Node.js 20 deprecation warning
for the pinned checkout and Python setup actions.

On recovery, confirm the revision with `git ls-remote origin refs/heads/fix/repository-audit`
and the run with `gh run view 41821705819 --repo fxmidaaa/pret-drept --json headSha,conclusion,jobs`.
Preserve the local CI evidence and the 18 earlier documentation edits.
