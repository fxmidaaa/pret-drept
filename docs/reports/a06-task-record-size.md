# A06 — Task record storage limit

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [894a016](https://github.com/fxmidaaa/pret-drept/commit/894a01675425bcf1e8cf05bab28dd42a47b419af). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41728652619) rechecked against that exact source revision on 2026-11-05.

## Change

Task saving now serializes indented UTF-8 JSON once and checks the exact stored byte count, including the final newline, against the shared 1 MiB limit before creating output. Oversized records fail before replacing an existing file.

## Recorded verification

| Check | Result |
| --- | --- |
| Task record regressions | 23 passed. Multibyte text at the limit round-trips, and one byte over preserves the previous file. |
| Full local suite | 233 passed, zero failed or skipped. |
| Published-commit CI | 221 passed and 12 private-model checks skipped. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-task-record-size/plan.md#verification) and [task record](../tasks/2026-11-04-task-record-size/task.json).

## Limits and follow-up

The bounded writer and atomic replacement protect the tested local save path. Concurrent-writer coordination remains a separate concern.
