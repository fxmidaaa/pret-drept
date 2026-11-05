# RP-20261105-A14 historical evaluation and M2 handoff

The user approved a documentation patch on `fix/repository-audit` at `086ef83` and deferred the A14 benchmark implementation to M2. This L0 increment qualifies the legacy scores and records the prerequisites for the frozen temporal and unseen-property evaluation.

1. Describe the reported README and notebook scores as historical results from filtered random splits.
2. Record the M2 data and evaluation gates below, with references to the frozen architecture and observed repository limitations.
3. Verify the documentation links, notebook source preservation and output check, task records, and whitespace. Present the patch for separate push approval.

## Acceptance criteria

- Public descriptions explain that legacy validation uses asking-price filters and price-dependent deduplication.
- Historical scores are identified as reports about the retained validation population.
- A14 benchmark implementation is explicitly deferred to M2 with actionable prerequisites.
- Notebook code cells and metadata match the reviewed baseline.

## M2 handoff

A14 remains open for implementation in M2. The approved direction is to retain justified training cleaning rules and compare candidates on one declared eligible evaluation cohort, including difficult asking-price cases with separate subgroup reporting. Evaluation eligibility and exclusions require a versioned policy.

1. Obtain approval for scheduled acquisition under [U-09](../../architecture/specification-v1.md#u-09--data-acquisition-permissions). Preserve each observed version and its acquisition provenance. Distinguish publication, collection, feature availability, and prediction cutoff times under [§9.3](../../architecture/specification-v1.md#93-temporal-semantics). The current scraper updates `last_seen` and skips detail refresh for known keys. The [historical CSV lacks observation timestamps](../../reports/m0-alignment.md#8-user-provided-private-data-and-executable-baseline-update).
2. Publish and verify restorable, immutable dataset releases under [§§8.2–8.3](../../architecture/specification-v1.md#82-dataset-release-identity), recording acquisition periods, transformation revisions, and quality reports.
3. Version the property identity policy and evaluate it using reviewed property pairs under [§9.2](../../architecture/specification-v1.md#92-property-identity-resolution). Record unresolved cases explicitly. The existing `features.py` deduplication key includes asking price.
4. Fix evaluation membership, eligibility, exclusion reasons, cutoffs, and identity-policy version in a split manifest under [§9.4](../../architecture/specification-v1.md#94-split-manifest-fields). Compare all candidates on the same records and target semantics under [§13.4](../../architecture/specification-v1.md#134-model-comparison-policy). Fit preprocessing and target-derived features using only training information available at the cutoff. Verify partition overlap, property contamination, and target-derived feature leakage under [§9.6](../../architecture/specification-v1.md#96-leakage-invariants).
5. Report primary future-market and secondary unseen-property development results under [§9.5](../../architecture/specification-v1.md#95-dual-evaluation-protocol), with MAE in euros and the required supporting metrics. Report atypical asking-price cases as a declared subgroup. Keep final-holdout handling within [§9.7](../../architecture/specification-v1.md#97-final-holdout-governance).

The [M2 exit gate](../../architecture/specification-v1.md#m2--data-versioning-and-baseline-ml) requires a reproducible training run and defensible development evaluation. Reliable timing and reviewed property identities are prerequisites for that evidence.

## Verification

| Check | Result |
| --- | --- |
| Documentation review | Historical scores and filtering descriptions agree with the legacy source. Local links and architecture anchors passed. |
| Notebook preservation | All 24 executable cells and all non-Markdown notebook content matched `086ef83`. The publication check passed for both notebooks. |
| Existing focused tests | 11 passed, covering persisted task records and the notebook checker. |
| Prior evidence | All 22 pre-existing local documentation edits match their starting digests. |
| Patch scope and whitespace | The patch contains documentation and notebook Markdown changes. Whitespace checks passed. |
| Local full application and distributions | Skipped for this documentation increment. |
| Remote CI | Passed on `a78f927`. Both tracked notebooks passed. Checkout tests reported 283 passed and 12 private-model skips. The extracted source and wheel each passed 142 tests. [Run 42026575076](https://github.com/fxmidaaa/pret-drept/actions/runs/42026575076) |

Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py tests/foundations/test_notebook_publication.py`
for the existing focused checks, `.venv/bin/python scripts/check_notebooks.py` for publication,
and `git diff --check` for whitespace. The link and notebook preservation probe is at
`/private/tmp/pret-drept-a14-verification.CC4uSU/check_documentation.py` and runs from the repository
with `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a14-verification.CC4uSU/check_documentation.py`.

The user approved publication and requested a GitHub account switch first. Switched the active
GitHub login to `fxmidaaa`, verified it through the GitHub user endpoint, and used that login
for the push. GitHub confirmed `a78f927fc22976c80ea6e2a1c765f78d99d903b1` on
`fix/repository-audit`. Foundations job `127242164657` passed. GitHub reported the existing
Node.js 20 deprecation warning for the pinned checkout and Python setup actions.

On recovery, confirm the revision with `git ls-remote origin refs/heads/fix/repository-audit`
and the run with `gh run view 42026575076 --repo fxmidaaa/pret-drept --json headSha,conclusion,jobs`.
Preserve this local CI evidence and the 22 earlier documentation edits. Resume A14 benchmark
implementation in M2 using the handoff above.

## Current recovery pointer — 2026-11-05

Earlier checkpoints above are historical evidence, including their source/CI identities.
Current branch state and next actions are in the [audit index](../../reports/README.md#current-checkpoint-and-recovery)
and [completion plan](../2026-11-05-audit-completion/plan.md): `fix/repository-audit` at
`36e67b7` plus uncommitted audit work. Inspect actual status/diff and preserve all local
changes; do not restore an older branch tip or infer publication authorization.

A14 remains incomplete: `train.py` still filters validation using observed asking prices and the dual benchmarks are absent. See the [benchmark prerequisites](../../reports/a14-evaluation-handoff.md#incomplete-benchmark-prerequisites). The earlier COMPLETED state refers only to the documentation handoff. Next propose/version evaluation eligibility and split contracts with synthetic leakage/population tests, then resolve the M2 prerequisites above.
