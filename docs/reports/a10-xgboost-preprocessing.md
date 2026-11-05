# A10 — Fitted XGBoost preprocessing

Summary added 2026-11-05. Branch `fix/repository-audit`. Approved fix published.

Published source [bcc143b](https://github.com/fxmidaaa/pret-drept/commit/bcc143b0869f3ad232632b7b07d7e20e167ae4f9). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/41812320589) rechecked against that exact source revision on 2026-11-05.

## Change

The XGBoost preprocessing component owns the fitted vectorizer, ordered feature names, and imputation medians. The legacy exporter saves those exact fitted medians and keeps serving defaults separate. Prediction restores the state, with existing numeric defaults providing compatibility for older bundles.

## Recorded verification

| Check | Result |
| --- | --- |
| Synthetic export and reload | The fitted median of 20 survives later filtering that would otherwise recompute it as 25. Encoded inputs match after reload. |
| Full local suite | 257 passed, zero failed or skipped. |
| Published-commit CI | 245 passed and 12 private-model checks skipped. |
| Packaging | Wheel imports and Docker source-copy and import probes passed. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-04-xgboost-preprocessing/plan.md#verification) and [task record](../tasks/2026-11-04-xgboost-preprocessing/task.json).

## Limits and follow-up

Native adapter payloads and the broader model-bundle migration remain M2/M4 work. Full inference-container runtime verification was skipped.
