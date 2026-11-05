# A08 — JSON-safe API validation errors

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [a8b6a1c](https://github.com/fxmidaaa/pret-drept/commit/a8b6a1cf89de3b55b178032e282aebddb7fb128c). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41804561617) rechecked against that exact source revision on 2026-11-05.

## Change

The API validation-error handler now represents nonfinite floats as JSON null while retaining HTTP 422, field locations, finite values, and the existing error-detail structure. Rejected NaN, infinities, and overflow values produce a serializable client-error response.

## Recorded verification

| Check | Result |
| --- | --- |
| HTTP regressions | 6 passed, including nested inputs and an ordinary finite validation error. |
| Full local suite | 241 passed, zero failed or skipped. |
| Published-commit CI | 229 passed and 12 private-model checks skipped. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-api-validation-json/plan.md#verification) and [task record](../tasks/2026-11-04-api-validation-json/task.json).

## Limits and follow-up

The fix covers validation responses. The legacy request parser still accepts nonstandard numeric tokens in fields ignored by validation.
