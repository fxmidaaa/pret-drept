# A12 — Identifier and digest formats

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [d5583a5](https://github.com/fxmidaaa/pret-drept/commit/d5583a537eaf6b9e637fcd2bfb8149657eec539a). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41821705819) rechecked against that exact source revision on 2026-11-05.

## Change

All seven public schemas now validate the complete value in 28 identifier and digest fields. Independent character and length constraints reject trailing newlines and other out-of-format values while preserving valid identifiers, lowercase SHA-256 references, supported Git commit lengths, and nullable alternatives.

## Recorded verification

| Check | Result |
| --- | --- |
| Identifier regressions | All 28 failed before the change and passed afterward. |
| Standalone schema comparisons | 16,240 comparisons matched the original intended whole-string grammars. |
| Full local suite | 285 passed, zero failed or skipped. |
| Published-commit CI | 273 passed and 12 private-model checks skipped. The source archive and wheel each passed 142 tests. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-identifier-formats/plan.md#verification) and [task record](../tasks/2026-11-04-identifier-formats/task.json).

## Limits and follow-up

The schemas validate reference syntax. Trusted admission must independently resolve and authorize the referenced artifact or dataset.
