# A14 — Historical evaluation and M2 handoff

Summary added 2026-11-05. Branch `fix/repository-audit`. Documentation published;
**A14 remains incomplete**, with benchmark implementation deferred to M2.

Published source [a78f927](https://github.com/fxmidaaa/pret-drept/commit/a78f927fc22976c80ea6e2a1c765f78d99d903b1). Original [CI run](https://github.com/fxmidaaa/pret-drept/actions/runs/42026575076) rechecked against that exact source revision on 2026-11-05.

## Change

The README and notebook Markdown now describe the reported scores as historical results from filtered random splits. The task plan records the M2 prerequisites for timestamped observations, immutable releases, reviewed property identity, fixed evaluation membership, leakage checks, and the frozen temporal and unseen-property benchmarks.

## Recorded verification

| Check | Result |
| --- | --- |
| Documentation and notebooks | 25 local links and anchors checked. All 24 executable cells and all non-Markdown notebook content matched the baseline. |
| Focused local tests | 11 existing tests passed. Full local application and distribution tests were skipped for this documentation increment. |
| Published-commit CI | 283 passed and 12 private-model checks skipped. Each package artifact passed 142 tests. |

Detailed evidence and recovery commands are in the [task plan](../tasks/2026-11-05-evaluation-handoff/plan.md#verification) and [task record](../tasks/2026-11-05-evaluation-handoff/task.json).

## Limits and follow-up

A14 benchmark implementation is deferred to M2. The historical CSV lacks observation timestamps, and the current scraper skips detail refresh for known listings. The approved implementation direction and gates are recorded in the linked M2 handoff.

## Incomplete benchmark prerequisites

The current `train.py` still calls `clean_data` before its random split, applies
`trim_ppm_outliers` to validation rows using their observed rent/m², and applies
`trim_knn_outliers` using their asking-price/local-rate ratio. Training-derived bounds
do not make that evaluation membership independent of validation targets. Price-based
deduplication also remains. Neither a fixed eligible cohort/split manifest nor primary
future-market and secondary unseen-property benchmarks are implemented. Qualifying
historical scores and recording a handoff do not repair these behaviors.

The next source step is to propose/version evaluation eligibility, exclusion reasons,
observation/property identities and cutoff/split contracts with synthetic overlap,
leakage and population tests. Review that policy before applying it to real data.
The [M2 handoff](../tasks/2026-11-05-evaluation-handoff/plan.md#m2-handoff) then requires:

- Authorized timestamped observation history or an approved defensible remediation;
  today's source dates cannot establish historical feature availability.
- An immutable, restorable data release and reviewed property pairs/identity policy,
  with ambiguous identities kept out of any automatic "unseen" classification.
- One declared evaluation cohort across candidates, training-only fitted transforms
  and cutoff-aware target aggregates; difficult asking-price cases reported separately.
- Reproducible isolated development runs on later observations and unseen properties,
  plus independent protected verification with final labels outside workload access.

No evaluation code, private data, split policy or protected labels were changed/accessed
here. Current recovery is in the [audit index](README.md#current-checkpoint-and-recovery);
the published documentation revision and its CI remain historical evidence only.
