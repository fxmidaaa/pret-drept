# A13 — Notebook publication

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [086ef83](https://github.com/fxmidaaa/pret-drept/commit/086ef83d3d4043d89515ec2f83720d2474dc708a). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41847049502) rechecked against that exact source revision on 2026-11-05.

## Change

The two public notebooks have cleared outputs and execution counts. A read-only CI checker rejects saved outputs, execution counts, attachments, widget state, and malformed notebook structure across tracked notebooks. Diagnostics identify locations using fixed descriptions.

## Recorded verification

| Check | Result |
| --- | --- |
| Notebook preservation | 26 outputs were cleared. All 24 executable cells, Markdown, and notebook metadata matched the baseline outside saved state. |
| Checker tests | 10 synthetic tests passed, and both original notebooks failed the checker before clearing. |
| Full local suite | 295 passed, zero failed or skipped. |
| Published-commit CI | 283 passed and 12 private-model checks skipped. Both notebooks passed, and each package artifact passed 142 tests. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-notebook-publication/plan.md#verification) and [task record](../tasks/2026-11-04-notebook-publication/task.json).

## Limits and follow-up

Older Git revisions retain the original saved preview. A review of historical exposure remains a separate decision. The publication checker covers saved notebook state.
