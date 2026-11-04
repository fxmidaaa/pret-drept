# RP-20261104-A13 public notebook outputs

The user approved audit A13 option 1 on `fix/repository-audit` at `d5583a5`. This L1 task keeps the analysis notebooks available as source and adds an unprivileged publication check.

1. Add a read-only checker for Git-tracked v4 notebooks and wire it into validation CI. Diagnostics identify the file and location without including notebook content.
2. Clear saved outputs and execution counts in the two tracked notebooks. Compare the remaining JSON against the prior revision to verify that cell source and notebook metadata are preserved.
3. Explain the source-only notebooks and the local publication check. Test the checker with synthetic unsafe content and verify the checkout and distributions.
4. Present the verified patch for separate push approval. Historical notebook versions remain a separate review decision.

## Acceptance criteria

- The two public notebooks retain their code and Markdown cells and contain no saved outputs or attachments.
- The checker fails on saved outputs, execution counts, attachments, widget state, and malformed notebook structure. It reads Git-tracked notebook paths and reports diagnostics without content.
- The check runs in existing unprivileged CI. Verification preserves prior evidence and uses synthetic failure fixtures.

## Verification

The checker rejected both original notebooks without printing their contents. It passed after
clearing 16 saved outputs in the EDA notebook and 10 in the model-selection notebook. Parsed
notebook objects matched the baseline after applying only the output and execution-count reset.
All 24 Python cells parsed successfully. Verification read notebook JSON and did not execute cells
or open the private CSV.

| Check | Result |
| --- | --- |
| Notebook gate | Both tracked notebooks passed. All 10 synthetic checker tests passed, including saved outputs, attachments, widget state, malformed JSON, and diagnostics. |
| Source preservation | Notebook source, Markdown, and metadata matched the baseline. |
| Full checkout | 295 passed, zero failed or skipped, one existing Starlette warning. |
| Extracted source archive and wheel | 142 passed in each, zero failed or skipped. |
| Source checks | Ruff lint and format, pinned actionlint, architecture checks, and whitespace checks passed. |
| Prior evidence | All 20 pre-existing local documentation edits match their starting digests. |
| Remote CI | Pending separate push approval. |

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_notebooks.py` for the publication check
and `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_notebook_publication.py`
for the focused suite. For the checkout, run
`PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/rent-a13-mpl NUMBA_CACHE_DIR=/private/tmp/rent-a13-numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short`.
Use the development guide's source checks and `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_distribution.py`
for the distributions. The logs and source-preservation probe are in
`/private/tmp/pret-drept-a13-verification.t957pe`. Re-run the probe with
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a13-verification.t957pe/check_notebook_delta.py`.

On recovery, confirm `fix/repository-audit` at `d5583a5` and review the A13 files separately
from the pre-existing edits. After push approval, commit the reviewed A13 files, publish to the
fix branch, and verify GitHub CI on that revision. The original notebook outputs are present in
historical revisions. A review of past exposure requires its own decision.
