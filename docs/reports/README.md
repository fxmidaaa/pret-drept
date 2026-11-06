# Repository audit reports

Each handled audit finding has an `aNN-...` report summarizing the approved change or decision,
published source, recorded verification, and remaining work. Detailed plans, lifecycle state,
and recovery commands live in the linked `docs/tasks/` folder.

This index was reconciled on 2026-11-05 against `fix/repository-audit`. Every original CI run
linked for A01–A15 was rechecked for a successful conclusion and the exact published source
revision. Test counts in the summaries describe the checks recorded for those revisions.

## Current checkpoint and recovery

**Source publication follow-up — 2026-11-06:** after reviewing increment 3, the user
requested **"push please"**, authorizing source commit/push on
`feat/m2-local-dvc-releases`, including its uncommitted increment-2 dependency.
Earlier no-commit/no-push and review-wait statements below are historical. The
[publication plan](../tasks/2026-11-06-m2-local-dvc-releases/plan.md#source-publication-follow-up)
records exact scope/recovery; both unrelated report-consistency edits stay local.
No merge, data publication, experiment or deployment is included.

Publication succeeded: increment-2 dependency
[4ad339e](https://github.com/fxmidaaa/pret-drept/commit/4ad339edc5bd7b6cebbfbe766d3ca0dd7b5350e4),
increment-3 source [0c23de6](https://github.com/fxmidaaa/pret-drept/commit/0c23de6ee8aa78043ef44ec6a5ed93c8a51e07d5).
The remote feature ref matched source SHA `0c23de6`. Its
[Linux CI](https://github.com/fxmidaaa/pret-drept/actions/runs/42190500570) passed:
678 checkout passes / 12 private-model skips, 487 per distribution, 38 frontend
passes and the static/workflow/architecture/notebook/DVC checks. This bounded source
task is **COMPLETED**; M2/A10/A14 and protected/real-data gates remain open. The
documentation follow-up records publication evidence; resolve the actual feature
branch HEAD/CI for recovery. Only the two unrelated report-consistency edits remain
local. See [publication verification](../tasks/2026-11-06-m2-local-dvc-releases/plan.md#publication-verification).

**Implementation checkpoint, M2 increment 3 — 2026-11-06:** local branch
`feat/m2-local-dvc-releases` at unchanged `d920ffc`, carrying the prior increment-2
implementation and two unrelated report-consistency edits. The user approved Option A:
immutable development release contracts and actual synthetic local DVC restoration,
with a separate locked tool environment. Work is **READY_FOR_REVIEW**; no repository commit,
push, PR update or real-data application is authorized. Current scope and recovery:
[release plan](../tasks/2026-11-06-m2-local-dvc-releases/plan.md),
[record](../tasks/2026-11-06-m2-local-dvc-releases/task.json),
[design](../architecture/dataset-releases-v1.md) and
[increment report](m2-local-dvc-releases.md). Local checks: 690 checkout tests,
487 tests per distribution and 38 frontend tests passed, plus static/architecture/
workflow/notebook checks. Final task/link/preservation verification follows the
evidence edit with implementation hashes unchanged. Stop after implementation/verification
for the user's review with a proposed commit message. M2's exit gate remains open.

**Prior M2 increment 2 — 2026-11-06:** local branch
`feat/m2-observation-candidates`, based on `d920ffc`. PR #1 is now merged; GitHub's
comparison to `main` shows one merge commit and no file changes. The earlier
open/unmerged and publication checkpoints below are historical. Current scope,
verification and recovery are in the
[candidate plan](../tasks/2026-11-06-m2-observation-candidates/plan.md) and
[record](../tasks/2026-11-06-m2-observation-candidates/task.json).
This increment is locally verified and **READY_FOR_REVIEW**, synthetic-first and
non-publishing; the two pre-existing unrelated
report-consistency edits remain local and untouched. No commit/push or real-data
application is authorized for this session. See the
[candidate contract](../architecture/observation-candidates-v1.md).
The [increment 2 report](m2-observation-candidates.md) summarizes the implementation
and verification; earlier evidence and recovery history remain intact.

Reconciled 2026-11-05: branch `fix/repository-audit`, HEAD **`36e67b7`** (A17 publication
evidence), with the existing A16 candidate and the current A18/audit follow-up uncommitted.
The unrelated report-consistency plan/task updates are preserved byte-for-byte.
Current work and verification live in the [completion plan](../tasks/2026-11-05-audit-completion/plan.md)
and [record](../tasks/2026-11-05-audit-completion/task.json). No new commit, push or CI run
is claimed for this working tree.

**M2 session checkpoint (2026-11-05):** the same branch/HEAD and all earlier audit
work are preserved. The first M2 increment adds a reviewable, development-only
eligibility/observation/split contract proposal and synthetic verification, locally
verified and **READY_FOR_REVIEW**. Current
M2 scope, verification and recovery live in its
[plan](../tasks/2026-11-05-m2-evaluation-contracts/plan.md) and
[record](../tasks/2026-11-05-m2-evaluation-contracts/task.json); the prior completion
record remains audit evidence. No real-data application, experiment, publication,
commit, push or M2 exit-gate success is claimed. The
[contract proposal](../architecture/evaluation-contracts-v1.md) needs independent
review before real-data use. A14 benchmark implementation remains incomplete.
The [M2 increment report](m2-evaluation-contracts.md) summarizes the implementation,
checks, limits and next increment.

**PR follow-up:** the user has now requested a PR into `main`, authorizing source
commit/push for the reviewed audit and M2 work. Earlier no-publication statements
above are historical. Follow the M2 task's publication section for current recovery;
the two unrelated report-consistency edits remain local. Merge and protected actions
are separate from this PR request.

Current publication: [PR #1](https://github.com/fxmidaaa/pret-drept/pull/1),
`fix/repository-audit` → `main`, open and unmerged. Source commit `fa0f28c`
passed [Linux CI](https://github.com/fxmidaaa/pret-drept/actions/runs/42116621974):
455 checkout passes / 12 private-model skips, 275 tests per distribution and 38
frontend passes. A16/A18's earlier local status below is superseded by inclusion
in this PR. An evidence-only follow-up records publication; resolve the PR's latest
head for recovery and preserve the two unrelated local reporting edits.

On recovery, run `git branch --show-current`, `git rev-parse --short HEAD`,
`git status --short` and `git diff --check`; inspect the diff and current plan before
continuing. Preserve all local work. After any further source edit, rerun the relevant
[development checks](../development.md) and update the current evidence. Commit/push and
protected actions require separate authorization under the current user request.

Published revisions below identify historical increments, not branch tips to restore.
Older plan checkpoints and CI evidence are retained as history. Updated task records
point here; the untouched report-consistency files retain their earlier pointer as
preserved evidence. No recovery instruction authorizes publication or model acceptance.

| Finding | Report | Current outcome | Published source |
| --- | --- | --- | --- |
| A01 | [CI workflow](a01-ci-workflow.md) | Published | `2a5beef` |
| A02 | [Scraper checkpoints](a02-scraper-checkpoint.md#publication-reconciliation) | Published | `9341519` |
| A03 | [Retry unsuccessful acquisition](a03-scraper-retry.md) | Published | `7e12d69` |
| A04 | [Checkpoint fields](a04-scraper-fields.md) | Published | `af574c9` |
| A05 | [Architecture graph](a05-architecture-graph.md) | Published | `d11304a` |
| A06 | [Task record size](a06-task-record-size.md) | Published | `894a016` |
| A07 | [Prediction initialization](a07-prediction-initialization.md) | Published | `95b019e` |
| A08 | [API validation JSON](a08-api-validation-json.md) | Published | `a8b6a1c` |
| A09 | [Apartment relationships](a09-apartment-relationships.md) | Published | `c4b91ea` |
| A10 | [XGBoost preprocessing](a10-xgboost-preprocessing.md) | Incomplete: future exports fixed; existing artifact lacks fitted medians | `bcc143b` (source fix) |
| A11 | [Foundations distribution](a11-foundations-distribution.md) | Published | `ee6549a` |
| A12 | [Identifier formats](a12-identifier-formats.md) | Published | `d5583a5` |
| A13 | [Notebook publication](a13-notebook-publication.md) | Published current-file fix. Historical exposure review is separate. | `086ef83` |
| A14 | [Evaluation handoff](a14-evaluation-handoff.md) | Incomplete: target-dependent evaluation retained; dual benchmarks absent (M2) | `a78f927` (documentation) |
| A15 | [Normalization](a15-normalization.md) | Published | `ad34828` |
| A16 | [Frontend responses](a16-frontend-responses.md) | Reviewed and verified locally; uncommitted | — |
| A17 | [Privacy claims and artifact review](a17-privacy-claims.md) | Published option 1; stronger controls deferred to M2/M4 | `ee4b555` |
| A18 | [Public types and documentation](a18-public-types-documentation.md) | Fixed locally; uncommitted | — |

Publication refers to the approved increment described in each report. The reports retain
specific follow-up work, such as A14's M2 benchmark and A15's versioned conversion provenance.
Private-model skips in CI are distinguished from local tests that used the available artifact.

## Reporting convention

For each approved audit increment, keep a report in this directory and link its task plan and
task record. Record the published commit and its exact CI run when available, with explicit
verification limits and deferred work. Update this index as the outcome changes.

Keep older checkpoints as dated history and add a current status pointer when publication
supersedes a pre-publication checkpoint. Use counts and reviewed aggregate evidence in reports.
