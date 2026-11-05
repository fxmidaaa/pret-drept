# Repository audit reports

Each handled audit finding has an `aNN-...` report summarizing the approved change or decision,
published source, recorded verification, and remaining work. Detailed plans, lifecycle state,
and recovery commands live in the linked `docs/tasks/` folder.

This index was reconciled on 2026-11-05 against `fix/repository-audit`. Every original CI run
linked for A01–A15 was rechecked for a successful conclusion and the exact published source
revision. Test counts in the summaries describe the checks recorded for those revisions.

## Current checkpoint and recovery

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
