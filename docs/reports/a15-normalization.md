# A15 — Legacy normalization

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [ad34828](https://github.com/fxmidaaa/pret-drept/commit/ad34828915a61930b82049fc41343bf05622769b). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/42035675032) rechecked against that exact source revision on 2026-11-05.

## Change

Price normalization now requires a recognized currency and positive finite amount. Numeric extraction preserves signs, and unsupported coordinate representations become a missing pair. The cleaner provides optional aggregate field and exclusion counts, and the trainer prints those diagnostics as JSON.

## Recorded verification

| Check | Result |
| --- | --- |
| Synthetic regressions | The counterexamples produced 30 failures before the helper changes. Updated coverage includes the cleaner and training entry point. |
| Compatibility | The reviewed three-row synthetic sample and existing currency conversions match the prior result. |
| Full local suite | 334 passed, zero failed or skipped. |
| Published-commit CI | 322 passed and 12 private-model checks skipped. Each package artifact passed 142 tests. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-05-normalization/plan.md#verification) and [task record](../tasks/2026-11-05-normalization/task.json).

## Limits and follow-up

Unsupported coordinate types follow the existing imputation path. The fixed legacy exchange-rate constants are documented. Versioned source normalization and dated conversion provenance remain M2 work.
