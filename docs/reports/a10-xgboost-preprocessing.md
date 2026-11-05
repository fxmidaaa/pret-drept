# A10 — Fitted XGBoost preprocessing

Summary added 2026-11-05. Branch `fix/repository-audit`. Source export fix published;
**A10 remains incomplete for the existing artifact**.

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

## Incomplete artifact prerequisites

The [A17 artifact inventory](a17-privacy-claims.md#reviewed-local-artifact) established
that the existing `model.joblib` (SHA-256
`057f6a297cc3606e1084cbd3b7b3f9c4e7fe4820bf2600dd32c53df9516e6b25`)
predates the exporter change and has no `imputation_medians` field. The loader falls
back to its stored `numeric_defaults`. Compatibility tests cannot show these are the
original training-fitted medians. Neither those medians nor their provenance can be
recovered merely by renaming defaults or documenting the new exporter.

Next actions, outside this request:

1. Preserve the current artifact/fallback. Identify an authorized immutable training
   release, split/recipe and reviewed source, plus an isolated rebuild environment.
   If original fitted state cannot be independently recovered with provenance, a
   separately authorized rebuild is required; do not patch invented medians into it.
2. Export a new candidate with the exact fitted medians, feature order/vectorizer and
   serving defaults. Independently verify saved state and fresh reload/input/prediction
   parity, including missing values. Complete native bundle/runtime work in M4.
3. Require reviewed-source rebuild, independent verification and exact-artifact human
   approval for acceptance; deployment remains separate. No rebuild, replacement,
   acceptance or deployment was performed for this documentation correction.

Use the [current recovery pointer](README.md#current-checkpoint-and-recovery), retaining
`bcc143b` and its CI as historical source evidence rather than current branch state.
