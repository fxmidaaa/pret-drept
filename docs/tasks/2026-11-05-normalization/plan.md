# RP-20261105-A15 legacy normalization

The user approved audit A15 option 1 on `fix/repository-audit` at `a78f927`. This L1 task tightens the existing normalization boundary and supplies aggregate diagnostics while retaining the legacy DataFrame interface.

1. Add synthetic regressions for unsupported currencies, malformed and nonfinite prices, unsupported coordinate types, and signed numeric fields through the helpers and `clean_data`.
2. Use finite-number conversion, recognize the three existing currency tokens explicitly, and preserve signed numbers. Treat unsupported coordinate values as a missing pair using the existing imputation path.
3. Add optional per-call aggregate diagnostics to `clean_data` and print the report in the legacy trainer. Verify counts, input preservation, valid conversions, and compatibility with the existing export test.
4. Document legacy rate constants and normalization semantics. Verify the checkout, package, source checks, and preservation of prior evidence. Present the patch for separate push approval.

## Acceptance criteria

- Required price values use an explicitly supported currency and a positive finite amount. Unsupported rows are excluded by existing required-field filtering.
- Unsupported or malformed coordinates produce a missing pair without interrupting other rows.
- Numeric extraction preserves signs and finite values. Existing required-field bounds reject negative areas and room counts.
- Aggregate diagnostics contain counts and static reason codes. Existing callers continue to receive the cleaned DataFrame, and source rows remain intact.
- Supported EUR, MDL, and USD conversions use the existing constants. Dated exchange-rate provenance and versioned source representations remain M2 work.

## Verification

The synthetic counterexamples produced 30 regression failures before the helper changes.
The updated tests exercise helper rejection, signed numeric extraction, mixed-row cleaning,
report counts, empty inputs, missing currency columns, input preservation, and report preservation
after failed normalization. The training entry-point test stops before fitting and verifies its
JSON diagnostic report. The reviewed synthetic sample matches the prior cleaned DataFrame.

| Check | Result |
| --- | --- |
| Full local checkout | 334 passed, zero failed or skipped, one existing Starlette warning. |
| Source archive and wheel | 142 passed in each, zero failed or skipped. |
| Compatibility | The three-row reviewed synthetic sample matches `a78f927`. Existing currency conversions and seven downstream feature and evaluation functions match the baseline. |
| Source checks | Scoped Ruff lint and format, explicit legacy feature/training/test lint, pinned actionlint, architecture, notebook publication, and whitespace checks passed. |
| Prior evidence | All 24 pre-existing local documentation edits match their starting digests. |
| Remote CI | Pending separate push approval. |

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_features.py tests/foundations/test_xgboost_preprocessing.py`
for focused normalization and legacy export checks. For the full checkout use
`PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/rent-a15-mpl NUMBA_CACHE_DIR=/private/tmp/rent-a15-numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`.
Use the development guide's source checks plus `.venv/bin/ruff check features.py train.py tests/test_features.py`.
Build and test both distributions with `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_distribution.py`.
Logs and the compatibility probe are under `/private/tmp/pret-drept-a15-verification.kADBpo`.
Run the probe from the checkout with
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a15-verification.kADBpo/check_compatibility.py`.

On recovery, confirm `fix/repository-audit` at `a78f927` and review the seven A15 files separately
from prior documentation edits. After push approval, commit the reviewed patch, publish to the
fix branch, and verify GitHub CI on that revision.
