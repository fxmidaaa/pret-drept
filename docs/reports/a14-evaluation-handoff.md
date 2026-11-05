# A14 — Historical evaluation and M2 handoff

Summary added 2026-11-05. Branch `fix/repository-audit`. Documentation published. Benchmark implementation deferred to M2.

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
