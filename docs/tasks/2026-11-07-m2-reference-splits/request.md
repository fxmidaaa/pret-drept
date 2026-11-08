# Authorized request

Continue M2 for Chișinău Rent Prediction with one bounded, reviewable increment. Let
development split materialization consume verified reference-backed (v2) releases, then
stop for review. Use only synthetic fixtures.

Reconcile the starting state first. Verify the branch, HEAD, index and working tree, and
preserve all existing changes. Increment 6 was `READY_FOR_REVIEW`, uncommitted on `main`
at `7f69b17`, with an empty index, and two unrelated report-consistency edits predated it.
If increment 6 still awaits review, stop after reconciling unless the user explicitly
authorizes building on it. Read `AGENTS.md`, the frozen architecture, the development
guide, the increment 6 record and design, the split design and report, the M0 audit and
the A14 handoff before editing.

Connect the verified v2 restore path to split materialization and readback, reusing the
existing verification and evaluation contracts. Preserve supported v1 workflows and ML
independence from the harness. On identical synthetic observations and policy, show v1/v2
parity for partition membership, exclusion reasons and cohorts, keeping release lineage
version-specific and preserving observation identities, declared chronology, property
matching semantics and deterministic ordering. Exercise a v2 inventory above the legacy
1 MiB logical JSON limit and distinguish input inventory limits from split output limits.
Reject a complete split that exceeds its supported output bound before finalization and
document the constraint. Escalate any conflict with the frozen architecture. Test wrong
expected references, missing or tampered inventory or restoration evidence, unsafe paths
and incomplete outputs, including an actual local DVC integration through a disposable
synthetic workspace and an independent fresh cache.

Record risk, acceptance criteria, design decisions, evidence, blockers and exact recovery.
Review the diff as a maintainer. After the final implementation edit run the focused,
checkout, DVC, architecture and source/wheel checks, and record passed, failed, skipped and
unavailable checks separately. Leave the project working tree uncommitted and do not push.
Baseline training, real data, protected labels, scraping, credentials, checkpoint downloads,
dataset publication, trusted policy changes, promotion and deployment are out of scope.

## Authorization record

At the review gate the session reported that increment 6 was still `READY_FOR_REVIEW`
with its review pending, and that building on it would layer this increment on the same
files. The user replied **"Authorize building"**. That authorizes building on the
uncommitted, unreviewed increment 6 working tree and nothing else. It grants no commit,
push, publication or protected action, and it does not review or accept increment 6.
