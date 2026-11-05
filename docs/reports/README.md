# Repository audit reports

Each handled audit finding has an `aNN-...` report summarizing the approved change or decision,
published source, recorded verification, and remaining work. Detailed plans, lifecycle state,
and recovery commands live in the linked `docs/tasks/` folder.

This index was reconciled on 2026-11-05 against `fix/repository-audit`. Every original CI run
linked for A01–A15 was rechecked for a successful conclusion and the exact published source
revision. Test counts in the summaries describe the checks recorded for those revisions.

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
| A10 | [XGBoost preprocessing](a10-xgboost-preprocessing.md) | Published legacy fix | `bcc143b` |
| A11 | [Foundations distribution](a11-foundations-distribution.md) | Published | `ee6549a` |
| A12 | [Identifier formats](a12-identifier-formats.md) | Published | `d5583a5` |
| A13 | [Notebook publication](a13-notebook-publication.md) | Published current-file fix. Historical exposure review is separate. | `086ef83` |
| A14 | [Evaluation handoff](a14-evaluation-handoff.md) | Documentation published. Benchmark implementation deferred to M2. | `a78f927` |
| A15 | [Normalization](a15-normalization.md) | Published | `ad34828` |
| A16 | Frontend errors and rendering | Pending decision | — |
| A17 | [Privacy claims and artifact review](a17-privacy-claims.md) | Published option 1; stronger controls deferred to M2/M4 | `ee4b555` |
| A18 | Public types and documentation | Pending decision | — |

Publication refers to the approved increment described in each report. The reports retain
specific follow-up work, such as A14's M2 benchmark and A15's versioned conversion provenance.
Private-model skips in CI are distinguished from local tests that used the available artifact.

## Reporting convention

For each approved audit increment, keep a report in this directory and link its task plan and
task record. Record the published commit and its exact CI run when available, with explicit
verification limits and deferred work. Update this index as the outcome changes.

Keep older checkpoints as dated history and add a current status pointer when publication
supersedes a pre-publication checkpoint. Use counts and reviewed aggregate evidence in reports.
