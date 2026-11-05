# A11 — Foundations source distribution

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [ee6549a](https://github.com/fxmidaaa/pret-drept/commit/ee6549a9b64a8a2a5250613855598b549d766f86). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41815850090) rechecked against that exact source revision on 2026-11-05.

## Change

An explicit source manifest selects foundations code, schema resources, and self-contained tests. The repository-task check runs in the checkout suite. CI builds the wheel from the source archive and tests both artifacts from a temporary extraction with editable-install paths disabled.

## Recorded verification

| Check | Result |
| --- | --- |
| Extracted source archive and wheel | 114 passed in each artifact. |
| Full local suite | 257 passed, zero failed or skipped. |
| Published-commit CI | 245 passed and 12 private-model checks skipped. Each artifact also passed 114 tests. |
| Negative and scope probes | Removing a schema made both artifact checks fail. Synthetic excluded-file canaries stayed out of the artifacts. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-foundations-distribution/plan.md#verification) and [task record](../tasks/2026-11-04-foundations-distribution/task.json).

## Limits and follow-up

The Python distribution covers the engineering foundations. The full application and its checkout-specific tests are available in the repository.
