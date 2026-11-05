# RP-20261105-A17 privacy claims and artifact review

Current status: A17 source is published at `ee4b555` on `fix/repository-audit` and its
exact-revision CI passed. See [publication evidence](#publication-evidence) for the
verified source/run and current recovery action. The original plan/checkpoints below
are retained as history.

The user approved A17 option 1 on 2026-11-05: accurate privacy claims, an explicit
local review of the existing legacy bundle, and an M2/M4 handoff for stronger
publication controls. Commit and push approval remain separate.

Risk: **L0**. This increment changes documentation and Python comments only. It
introduces no redaction, hash migration, aggregation threshold, model behavior,
authorization policy or publication mechanism. Any such change needs a separate decision.

Start from `fix/repository-audit` at `d9ac405`. A16 is implemented locally and
awaits publication approval. Preserve its code, reports and task records, plus the
earlier report-consistency evidence. The audit index is shared: only its A17 row
may change in this increment.

## Plan and affected modules

1. Inventory the known local `model.joblib` only after verifying its identity against
   the earlier audit. Report approved field names, object classes, shapes/counts and
   limitations; omit coordinate/rent values, category labels and arbitrary contents.
2. Reconcile `README.md`, `data/sample/README.md`, and comments in `scrape.py`,
   `features.py`, `train.py` and `tests/test_api.py`. Preserve every executable AST,
   the test name/assertions, checkpoint identity format and all existing model bytes.
3. Document an exact-artifact publication review procedure in
   `docs/operations/artifact-publication-review.md`. Distinguish Git/build exclusions,
   field minimization, pseudonyms, fitted state, disclosure-risk review and authorization.
   This procedure is guidance, not an activated trusted policy or approval to publish.
4. Add an A17 report and a bounded M2/M4 handoff with unresolved decisions and exit
   evidence. Preserve recoverable raw observations under architecture §§8.3/8.5.
   Account for model-specific state, including TabPFN (§10.6), instead of promising
   that every model contains only aggregates.
5. Verify source semantics/preservation, synthetic counterexamples, relevant existing
   checks, local links and task records; present the change and proposed commit message.

## Acceptance criteria

- Current documentation distinguishes field minimization and pseudonymization from
  proven anonymity; permitted text can contain personal information.
- The 15-row guard is described only for grid/sector rent maps. Global fallbacks,
  coordinate/default statistics and fitted model state receive explicit treatment.
- Existing tests are described by their actual assertions and are not presented as
  exhaustive payload inspection or a privacy certification.
- The local artifact review is bound to its SHA-256 and uses counts/types only. It
  identifies what can and cannot be established without data/source provenance.
- M2/M4 decisions, destinations, field/cohort rules, model-specific review and
  independent approval remain explicit prerequisites for stronger publication claims.
- No executable Python changes, private-value disclosures, new dependencies, model
  writes, data access beyond the approved bundle, scraping, training or publication.
- All prior work remains byte-identical except the intentional A17 audit-index row.

## Verification and recovery

Baseline source copies and digests are under `/private/tmp/pret-drept-a17.ySS4Q6`.
The known legacy artifact is 1,784,346 bytes with SHA-256
`057f6a297cc3606e1084cbd3b7b3f9c4e7fe4820bf2600dd32c53df9516e6b25`;
its identity matched before deserialization. Do not load an unknown replacement
under this prior-artifact assumption. No model copy is made.

Use the locked local Python environment with bytecode disabled. Keep all review
scripts/output in the temporary directory, with safe type/count summaries only.
Compare Python ASTs to the captured preimages and prior-work digests to their baseline.
Run relevant existing feature/scraper/bundle checks, task-record validation,
architecture, notebook and whitespace checks. Documentation changes do not require
new tests that merely assert prose. Record exact commands/results here after execution.

## Progress

- Completed the known-artifact review using only type/count summaries and expected
  schema names. The model digest matched before/after inspection; no model copy or
  raw-dataset read was made. The inspected helper maps do not carry memberships or
  support counts, so this review cannot certify minimum cohort sizes.
- Corrected README/sample prose and four Python files' explanatory comments. Added
  the publication review guidance, M2/M4 handoff and A17 report; updated only the
  A17 row in the shared index.
- Initial final-document probing treated a valid directory link as a missing file.
  Corrected the temporary checker to accept directory targets; the final link check
  passed. No repository-link repair was needed for that probe error.

## Verification evidence

| Check / exact command | Result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /private/tmp/pret-drept-a17.ySS4Q6/review_bundle.py` | Passed. Known model: 12 recognized root fields; type/count inventory in `inventory.json`; unchanged model digest. Socket connections blocked. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python /private/tmp/pret-drept-a17.ySS4Q6/probe_boundaries.py` | Four synthetic probes passed; zero network calls or private dataset reads. Safe summary in `synthetic.json`. |
| `PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a17.ySS4Q6/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a17.ySS4Q6/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/test_features.py tests/test_scrape.py tests/test_api.py::test_bundle_ships_no_row_level_data tests/foundations/test_repository_tasks.py` | 139 passed, 0 skipped, 18.66 s; one existing Starlette/httpx deprecation warning. |
| `.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed. |
| `.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | Passed; 34 files already formatted. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/rent-check-architecture --root .` | Passed; runtime isolation not assessed. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_notebooks.py` | Passed for both tracked notebooks; cells not executed. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python /private/tmp/pret-drept-a17.ySS4Q6/check_a17.py` | Passed: 11 A17 files, four identical Python ASTs, nine byte-identical prior files, A17-only shared-index change, 40 local links/anchors, model digest, task record and whitespace. |
| Unsupported-claim scan | No remaining matches for the reviewed unconditional phrases in current A17 documentation/comments; historical reports remain intact. |
| Full application/frontend/browser/distribution reruns | Skipped: documentation/comments only; executable ASTs and A16 files preserved. |
| New remote CI | Pending separate publication approval; no commit or push made. |

Final task-record checks are repeated after the evidence update. No new runtime
tests were added to assert prose. The relevant existing tests exercise the stated
mechanisms and are not treated as a privacy certification.

## Exact recovery action

Read the A17 report, procedure and task record, confirm `fix/repository-audit` at
`d9ac405`, and inspect the local changes against the captured preimages. Preserve
all A16 work and older evidence. Repeat the checker and persisted-record test with:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python /private/tmp/pret-drept-a17.ySS4Q6/check_a17.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_repository_tasks.py
```

Present `docs(privacy): reconcile claims and record artifact review` as the proposed
commit message for the eleven-file A17 increment. Commit/push and any inclusion of
earlier A16/evidence changes require the user's separate decision. After an approved
push, verify CI against that exact revision. Stronger publication controls remain
an M2/M4 handoff with separate approved requirements.

## Source publication approval — 2026-11-05

The user approved the reviewed A17 increment with "push please". Publication is
scoped to the eleven A17 files; A16 and the two earlier report-consistency evidence
updates remain local. Stage only the A17 index-row change in the shared audit index.
The remote branch was independently checked at `d9ac405` before preparing the commit.
Publish the reviewed source without force and follow CI for the exact new revision.
Older pending-approval statements above are pre-publication checkpoints.

## Publication evidence

- Published source: [`ee4b5552885e6ec0ebef3a73cdc295a7f6b16e45`](https://github.com/fxmidaaa/pret-drept/commit/ee4b5552885e6ec0ebef3a73cdc295a7f6b16e45).
  Its committed tree matched the prepared eleven-file A17 tree exactly. The shared
  index contains only the A17 row change; no A16 source or prior evidence was staged.
- The existing GitHub account was verified as `fxmidaaa`. A normal push advanced
  `fix/repository-audit` from `d9ac405` to `ee4b555`; GitHub independently confirmed the SHA.
- [CI run 42074089595](https://github.com/fxmidaaa/pret-drept/actions/runs/42074089595)
  completed successfully for the exact source SHA. Foundations job `127409503574`
  passed all steps. Checkout tests: **322 passed, 12 skipped**, one existing warning.
  Source archive and wheel: **142 passed each**. The skips require the absent private model.
- All nine prior A16/evidence files remained byte-identical after the push. The A16
  row remains a local change. The model file is unchanged and was not published.
- This documentation follow-up records the completed source publication and exact-source
  CI. It does not activate privacy policy, approve a model/data export or deploy anything.
- Follow-up documentation checks passed after the evidence edits: 41 local links/anchors,
  unchanged Python ASTs/model identity, preserved prior files and valid task records.
  `tests/foundations/test_repository_tasks.py` passed again. The follow-up contains
  only the four A17 report/index/task evidence files.

Current recovery: confirm the published source and run with
`gh run view 42074089595 --repo fxmidaaa/pret-drept --json headSha,conclusion,jobs`.
The source SHA must be `ee4b5552885e6ec0ebef3a73cdc295a7f6b16e45` and conclusion `success`.
Use the A17 report/index for current status; retain the original local checks as historical
evidence. A16 publication still requires its separate decision. A18 remains pending review.

## Current recovery pointer — 2026-11-05

Earlier checkpoints above are historical evidence, including their source/CI identities.
Current branch state and next actions are in the [audit index](../../reports/README.md#current-checkpoint-and-recovery)
and [completion plan](../2026-11-05-audit-completion/plan.md): `fix/repository-audit` at
`36e67b7` plus uncommitted audit work. Inspect actual status/diff and preserve all local
changes; do not restore an older branch tip or infer publication authorization.
