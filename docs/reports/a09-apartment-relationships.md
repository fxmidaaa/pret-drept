# A09 — Apartment relationship validation

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [c4b91ea](https://github.com/fxmidaaa/pret-drept/commit/c4b91eac786e9d1cf21058ee956b310e41bd4c43). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41809961842) rechecked against that exact source revision on 2026-11-05.

## Change

A shared domain validator checks floors against building height, kitchen area against total area, and coordinate-pair completeness. The HTTP route, direct prediction entry point, and canonical Python contract validator use the same rules. Invalid direct predictions fail before model loading, and the HTTP route returns field-specific 422 details.

## Recorded verification

| Check | Result |
| --- | --- |
| Relationship regressions | 15 passed across HTTP, direct prediction, and canonical validation. |
| Full local suite | 256 passed, zero failed or skipped. |
| Published-commit CI | 244 passed and 12 private-model checks skipped. |
| Packaging | Wheel imports and the network-disabled Docker source-copy and import probes passed. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-apartment-relationships/plan.md#verification) and [task record](../tasks/2026-11-04-apartment-relationships/task.json).

## Limits and follow-up

The full inference container runtime was skipped. The Docker evidence covers source packaging and import behavior. Canonical cross-field checks run in the Python validator after structural schema validation.
