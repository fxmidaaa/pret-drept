# A07 — Concurrent prediction initialization

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [95b019e](https://github.com/fxmidaaa/pret-drept/commit/95b019e74e79e8b8a268acd32ff3e94928b77e36). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41731227832) rechecked against that exact source revision on 2026-11-05.

## Change

The prediction loader builds the complete model bundle and SHAP explainer locally while holding a process-local initialization lock. It publishes the bundle only after initialization succeeds. A failed initialization leaves the cache empty so a later call can retry.

## Recorded verification

| Check | Result |
| --- | --- |
| Initialization regressions | Both deterministic tests passed after failing against the previous implementation. |
| Full local suite | 235 passed, zero failed or skipped. |
| Published-commit CI | 223 passed and 12 private-model checks skipped. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-prediction-initialization/plan.md#verification) and [task record](../tasks/2026-11-04-prediction-initialization/task.json).

## Limits and follow-up

The lock coordinates callers within one process. Each serving process owns its own cache. Startup readiness and lifecycle changes are separate operational work.
