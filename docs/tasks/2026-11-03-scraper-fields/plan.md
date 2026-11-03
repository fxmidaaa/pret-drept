# RP-20261103-A04 — enforce approved checkpoint columns

Risk: **L1 engineering**. Approval: [request](request.md). Branch: `fix/repository-audit`; source baseline `7e12d691575b3a1e06277c1900c6f9637314bd4a`. The existing local changes to the A03 report and task record must remain byte-identical.

## Scope and architecture

Fix A04 in the existing scraper, its offline tests, README/development instructions and this task's evidence. Specification §§4.3, 6 and 8.3 apply: acquisition remains independent of ML/harness code; source observations remain recoverable; a mutable checkpoint is not a dataset release. This is validation of unprivileged scraper storage, not activation of a trusted policy or a protected-data boundary change. No new dependency or migration infrastructure.

## Acceptance criteria

1. One storage allowlist includes only the existing reviewed feature/filter names and the five generated fields: `listing_key`, `price_value`, `price_unit`, `first_seen`, `last_seen`.
2. Unexpected columns in any checkpoint, including header-only files, fail before row loading/collection. Files remain byte-identical and errors disclose neither unexpected names nor cell values. Column matching is exact; no silent dropping, trimming or renaming.
3. Direct saves reject unexpected row keys before creating directories or temporary output. Existing contaminated destinations are also rejected before replacement. Existing mapping/identity, full-population, CSV and atomic-save checks remain in force.
4. Approved columns and optional subsets round-trip unchanged; newly fetched unapproved controls remain excluded. Existing A02 preservation/failure tests and A03 retry/completeness behavior continue to pass. Tests use synthetic fixtures and block live network requests.
5. Focused regressions, the full local suite, scoped Ruff/format, workflow semantics, architecture, task reload, changed-document links, preservation and diff checks pass after final edits. Distinguish failed/skipped/unavailable checks and persist recovery.

## Implementation and verification

1. Persist approval, plan, active task context and preservation identities for private files and the two local A03 updates.
2. Add offline counterexamples for unknown checkpoint headers and direct-save row keys, and reproduce their failures before changing the scraper.
3. Add the storage allowlist and one shared column validator at header/row boundaries. Preserve successful acquisition and atomic storage behavior.
4. Add approved-column round-trip, contaminated-destination, serialization and fetched-control regressions; document the compatibility restriction and separate migration requirement.
5. Execute final checks, review scope and engineering tradeoffs, record evidence/recovery, and explain the completed correction. No commit/push.

## Recovery and limits

Read `task.json`, reconcile Git against baseline and preserve the two A03 updates. Verification outputs and preservation identities are under `/private/tmp/pret-drept-a04-20261103`. Files with extra columns require a separately reviewed, versioned migration to a different destination, retaining the original; this increment does not perform one. Column validation does not inspect permitted free text for personal information, certify anonymity, add concurrent-writer coordination, or implement immutable observation history. Other audit findings remain separate decisions.

## Final checkpoint

Approved option 2 is implemented and locally verified. **75 scraper tests and all 217 local tests passed**, with zero final failures/skips and one existing deprecation warning. Scoped lint/format, workflow semantics, architecture, preservation and context checks passed. See [verification and engineering rationale](../../reports/a04-scraper-fields.md). The source correction adds 14 lines; no dependency or migration infrastructure was introduced. No commit/push, live collection, data migration or training occurred. Next action: review the local A04 patch; publication requires separate branch/message approval.

Publication update: the user approved the presented branch and message. Commit the eight reviewed A04 files as `fix(scraper): reject unapproved checkpoint columns`, push `fix/repository-audit` without force, and inspect exact-commit CI. Preserve the two local A03 evidence updates. Record post-publication results locally; further publication needs separate approval.
