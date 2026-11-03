# RP-20261103-A03 — retry unsuccessful acquisition

Risk: **L1 engineering**. Approval: [request](request.md). Branch: `fix/repository-audit`; clean baseline: `48ddb57`. The A01/A02 commits are present; their older task records predate publication and must not be used to repeat those actions.

## Scope and architecture

Correct A03 option 2 in `scrape.py`, its existing offline test module, README/development instructions and this task's evidence. Specification §§4.3, 6, 8.3 and 18.1 apply: acquisition remains independent of ML/harness code; raw input remains recoverable; failure diagnostics must not disclose source payloads or private rows. A mutable checkpoint is not a dataset release or proof of market coverage. Preserve A02 validation/atomic storage and legacy successful collection behavior. No new dependency or retry infrastructure.

## Acceptance criteria

1. Failed, unavailable or malformed detail retrievals create no completed/rejected row. A subsequent run retries the listing when encountered again and can persist a successful result. Other successful rows on an incomplete page survive.
2. Successfully retrieved, ineligible listings still receive rejection markers; existing accepted/rejected checkpoint rows retain resume behavior. Ambiguous historical markers are not reinterpreted.
3. Transport, HTTP, JSON/GraphQL and search-response failures cannot look like normal exhaustion. Search failure stops pagination; incomplete collection returns a nonzero CLI exit and safe diagnostics, while ordinary exhaustion succeeds. Detail failures are counted and reported after saving valid page progress.
4. Existing request retry attempts remain bounded. Tests use synthetic responses, block live requests, and check that source payloads/exceptions are not echoed. No live acquisition, migration, training, dependency/policy change or private-row output occurs.
5. Focused regressions and the full suite, scoped Ruff/format, workflow semantics, architecture, task reload, documentation links, preservation and diff checks pass after final edits. Report failed/skipped/unavailable checks explicitly and persist the next recovery action.

## Implementation and verification

1. Persist approval/plan/task context and preservation identities for private inputs and prior task records.
2. Add synthetic failure-then-success and search-failure regression tests; reproduce against unchanged code.
3. Separate retrieval failure from completed state, propagate search failures, preserve valid progress, and return a nonzero exit for incomplete collection. Keep error output bounded and free of response/exception contents.
4. Document retry/completeness behavior and limits. Run targeted tests, then full local and source checks.
5. Review the final diff against scope, record exact evidence and recovery, and give a brief completion report. No commit/push is part of this approval.

## Recovery and limits

Recovery: read `task.json`, reconcile Git state, run the documented focused/full checks, and inspect the final diff. Temporary verification outputs and preservation identities are under `/private/tmp/pret-drept-a03-20261103`. Failed IDs have no persistent queue: they are retried only if encountered in a later search. Unavailable listings remain unresolved. Existing rejection markers are ambiguous. A04 field policy, observation history, immutable releases and concurrent checkpoint access remain outside scope.

## Final checkpoint

Approved option 2 is implemented and locally verified. **63 scraper tests and all 205 local tests passed**, with zero final failures/skips and one existing deprecation warning. Source/workflow/architecture, preservation and context checks passed. See [verification and review](../../reports/a03-scraper-retry.md). No commit/push, live collection, migration or training occurred. Next action: review this local patch; publication and subsequent audit fixes need separate user approval.

Publication update: the user approved the presented branch/message with "push". Commit the reviewed A03 patch as `fix(scraper): keep failed fetches retryable and flag incomplete runs`, push `fix/repository-audit` without force, and inspect exact-commit CI. Persist the resulting evidence locally without publishing another commit under this approval.
