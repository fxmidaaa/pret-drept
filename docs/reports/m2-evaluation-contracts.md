# M2 first increment — development evaluation contracts

Initial implementation checkpoint, 2026-11-05; `fix/repository-audit` at
`36e67b75ad562cec6dd98dc5bff7f411f383db4d`, uncommitted. Risk: **L2 source proposal**
under frozen specification §§6.2, 8–9, 12.7 and 13.4. Existing audit work is preserved.
The [plan](../tasks/2026-11-05-m2-evaluation-contracts/plan.md) and
[task record](../tasks/2026-11-05-m2-evaluation-contracts/task.json) preserve scope,
authorization, acceptance criteria, risk assessment, evidence and recovery.

## Implementation and design

- Three additive public schemas: observation references, proposed eligibility policy,
  and a development-only split envelope; bundled through the existing local registry.
- Separate listing/observation/property references and dataset/policy/split/inventory
  digests, with versioned domain/matching references and creation provenance.
- Explicit unknown times/identities, temporal cutoffs/windows, complete eligibility
  exclusions and future-market/unseen-property assignments. No target-based selectors
  or restricted final-holdout fields. Legacy training/API/artifacts remain intact.
- Semantic validators check supplied population completeness, observation collisions,
  time availability, declared property representation, digest correspondence and
  each candidate's exact fixed evaluation population. No silent record dropping.
- Self-contained synthetic tests ship with source/wheel verification. No new
  dependency, data reader, publisher, split generator, model or experiment is added.

The [policy proposal](../architecture/evaluation-contracts-v1.md) explains the exact
rules and decisions for review. Captured input availability follows publication ≤
collection ≤ whole-snapshot feature availability ≤ prediction cutoff. Training is
strictly before its cutoff; validation is start-inclusive/end-exclusive. Repeated
properties remain in future-market evaluation. Confirmed absence is required for
the secondary view; probable/unresolved evaluation identity or any uncertain training
identity prevents an automatic unseen claim. Both views may overlap.

## Verification

After the last source/test edit on CPython 3.13.16 / Node 24.21.0:

| Check | Result |
| --- | --- |
| New synthetic contracts | **114 passed**, zero failed/skipped. |
| Full checkout | **467 passed**, zero failed/skipped; one existing Starlette/httpx warning. |
| Extracted source / wheel imports | **275 passed each**, zero failed/skipped; all ten schema resources exercised. |
| Frontend | **38 passed**, zero failed/skipped; page/tests unchanged. |
| Ruff lint/format, architecture, actionlint, notebooks, whitespace | Passed. Static boundaries do not certify runtime isolation. |
| Final documentation/task/preservation check | Passed: all 146 starting files preserved (141 byte-identical; five verified additive edits), 15-file M2 scope, all 21 task records and 43 local links/anchors; branch/HEAD/index/whitespace unchanged/clean. |
| Failed | Initial impossible-date regression and format check were corrected; no unresolved source/test failures. |
| Skipped | Real-data application, DVC restoration/publication, acquisition, training/evaluation, feature-lineage/runtime/protected tests; outside this increment. |
| Unavailable | New-revision Linux CI and independent protected review/access/isolation evidence; no commit/push or protected action. |

Exact commands, initial failure/correction, local logs and recovery actions are in
the [verification record](../tasks/2026-11-05-m2-evaluation-contracts/plan.md#final-verification).
The initial calendar-date failure demonstrated that optional schema-format support
cannot be assumed; the new semantic helpers use explicit calendar parsing instead.

This increment is **READY_FOR_REVIEW**. Final task/evidence edits receive the
documentation/preservation check and repository task test again before delivery.

## Limits and single recommended next increment

These checks validate declared metadata and populations. They do not prove data
completeness, timestamp truth, matching quality, feature/aggregate lineage, label
availability or leakage-free evaluation. No real split/release or benchmark exists
from this work. A14 and **M2's reproducible-run/development-evaluation exit gate
remain open**. No protected labels or private rows were inspected; existing model
inference ran only through the established regression suite.

**Next: observation provenance and release-candidate validation**, initially against
synthetic inputs: a non-publishing projector/validator that preserves unknown facts
and produces an aggregate quality report. Before real-data application, review this
policy proposal, authorize the private input/field projection and identity evidence
handling, and settle non-target domain/currency provenance and quarantine rules.
The historical CSV's missing times may only be reported as unknown; defensible
history or approved remediation is required for temporal eligibility. Reviewed
property pairs/matching policy precede confirmed/unseen claims. No timestamps or
matching thresholds are chosen here. Acquisition/enrichment, DVC storage/access/
retention and publication require their own decisions and authorization.

## Pull request follow-up

The user subsequently requested publication as a PR into `main`, authorizing the
necessary source commits and push. The earlier uncommitted/no-push checkpoint is
retained as history. The PR includes the accumulated audit branch and locally
verified A16/A18/M2 work; two unrelated report-consistency edits remain local.
The task's follow-up records the publication plan and actual PR/CI evidence.
No merge, real-data application or protected operation is authorized by this step.

Source published at `fa0f28c879d5180cb04fb783c22866f911ddadc1` in
[PR #1](https://github.com/fxmidaaa/pret-drept/pull/1), targeting `main` and unmerged.
Exact-source [Linux CI](https://github.com/fxmidaaa/pret-drept/actions/runs/42116621974)
passed: **455 checkout tests passed, 12 private-model skips**, **275 tests per
distribution**, **38 frontend tests**. Earlier unavailable-CI/uncommitted statements
describe the initial checkpoint. Independent protected review/runtime evidence
remains unavailable; A10/A14 and M2's exit gate remain open. The task's publication
section records the 65-file source commit, 126-file full branch diff, preservation,
connector/CLI outcome and current recovery. This follow-up changes evidence only.
