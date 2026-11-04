# RP-20261104-A11 foundations source distribution

The user approved audit A11 option 1 on `fix/repository-audit` at `bcc143b`. This L1 task aligns the source distribution with the existing foundations wheel and gives the shipped tests an independent CI check.

1. Declare the source archive's package files, schema resources, and self-contained foundation tests. Keep checkout-specific checks in the full checkout suite.
2. Build the source archive and its wheel using the existing locked environment. Run the shipped suite from the unpacked source and against the wheel, with editable-install paths disabled.
3. Verify archive scope with synthetic excluded payloads. Run the full checkout suite, workflow validation, static checks, and the architecture checker.
4. Preserve existing audit evidence and present the verified patch and commit message for separate push approval.

## Acceptance criteria

- The unpacked archive's contract, prediction and bundle, task lifecycle, and architecture tests pass using shipped sources and synthetic fixtures.
- The same tests pass using the built wheel, which exposes all seven versioned schemas.
- Both artifacts contain only the foundations release payload. The full legacy and repository tests continue to run in checkout CI.

## Verification

The previous archive failed test collection on missing `predict`, `features`, and `scrape`.
The source manifest now selects four self-contained test modules and their shared fixtures.
The test for actual task records moved to its own checkout test module. The distribution
check imports from the extracted source tree and then from the wheel while bypassing the
checkout's editable install.

| Check | Result |
| --- | --- |
| Extracted source archive | 114 passed, zero failed or skipped |
| Wheel built from the source archive | 114 passed, zero failed or skipped. All seven schemas load through the public validation tests. |
| Archive scope | Exact member checks passed with synthetic exclusion canaries. The direct wheel build also excluded the canaries. Package requirements and the license file stayed the same. |
| Negative schema probe | Removing the bundle manifest schema made both artifact test runs fail as expected. |
| Full local checkout | 257 passed, zero failed or skipped, one existing Starlette warning |
| Source and dependencies | Scoped Ruff lint and format, pinned actionlint, architecture checks, whitespace checks, and `uv pip check` passed. The local virtual environment has no pip module. |
| Prior evidence | All 16 pre-existing local documentation edits match their starting digests. |
| Remote CI | Pending separate push approval. |

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_distribution.py` to rebuild and
test both artifacts. For the checkout suite, run
`PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/rent-a11-mpl NUMBA_CACHE_DIR=/private/tmp/rent-a11-numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`.
Run the development guide's source checks and `UV_NO_CACHE=1 uv pip check --python .venv/bin/python`.
The canary probe and logs are in `/private/tmp/pret-drept-a11-verification.edRuDZ`. To repeat
the probe, copy `check_scope.py` to a new temporary directory and run it with the checkout's
`.venv/bin/python` from the repository root.

Recovery starts at `fix/repository-audit` revision `bcc143b`. Review the A11 files separately
from the existing documentation edits. After push approval, commit only the reviewed A11
files, push to the fix branch, and verify the unprivileged workflow on the published revision.
