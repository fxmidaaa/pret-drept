# A05 — Architecture import graph

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [d11304a](https://github.com/fxmidaaa/pret-drept/commit/d11304ad1534f2eae1adb30520b338c9b239839c). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41724876763) rechecked against that exact source revision on 2026-11-05.

## Change

The checker now inventories and classifies project Python sources, resolves ordinary absolute and relative imports, and follows dependency chains through intermediate modules. It reports forbidden indirect imports and rejects source symlinks, ambiguous identities, and unclassified code. The existing architecture command exercises the same checker.

## Recorded verification

| Check | Result |
| --- | --- |
| Architecture regressions | 30 passed, including cycles, package initialization, loader spellings, and supported legacy imports. |
| Full local suite | 231 passed, zero failed or skipped. |
| Published-commit CI | 219 passed and 12 private-model checks skipped. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-03-architecture-graph/plan.md#verification) and [task record](../tasks/2026-11-03-architecture-graph/task.json).

## Limits and follow-up

This is static source analysis. Custom runtime loading, import hooks, and process isolation need their own verification. The detailed plan records the scanned paths and exclusions.
