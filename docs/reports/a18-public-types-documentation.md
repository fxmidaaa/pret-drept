# A18 — Public request construction and documentation

Date: 2026-11-05. Risk: L1. Fixed locally on `fix/repository-audit` at `36e67b7` plus
the uncommitted audit diff. No commit, push or remote CI is claimed.

## Change

Byte input is explicitly decoded as UTF-8 before parsing. UTF-16/32 auto-detection,
UTF-8 BOMs and unsupported wire input types cannot bypass the declared encoding.
Text and byte input share Unicode/BOM rules and the 1 MiB UTF-8 byte limit.

`ExperimentRequest` now requires the adapter schema registry during ordinary payload
construction as well as `from_document`. Both routes validate the request envelope,
adapter registration and configuration before storing normalized immutable JSON.
Dataclass replacement goes through the same checks. Caller dictionaries and registries
are not retained. The factory API and wire schema are preserved; the previously unsafe
one-argument constructor now fails. Validation never grants execution authority.

The M0 baseline inventory is corrected to **25 files and five root Python modules**,
verified against the exact audited Git tree. README and the development guide distinguish
the legacy runtime pins, the installable foundations package and the locked development
environment. Current task recovery points to the reconciled audit checkpoint; earlier
checkpoints are retained as history. Unrelated reporting updates remain unchanged.

## Verification and limits

New regressions reproduced the constructor/encoding gaps before the fix (14 failures,
two passing boundary checks). The focused contract suite subsequently passed **84 tests**,
including canonical/digest parity, caller-state independence, unregistered/invalid
configurations, replacement, Unicode, encoding/BOM rejection and byte-size limits.
An initial formatting check failed and was corrected before final verification.
One subsequent aggregate run caught an incorrect exception expectation in the new
replacement test; it was corrected. Final checks passed: **353 checkout tests**, **38
frontend tests**, and **161 tests each** for the source archive and wheel, plus scoped
lint/format, architecture, actionlint, notebook publication and dependency compatibility.
Zero final test failures/skips; the existing Starlette/httpx warning remains. New remote
CI is unavailable for this uncommitted tree; full inference/protected runtime checks
were skipped. Final documentation/preservation checks passed after evidence edits:
128 local links/anchors, all 20 task records and the five preserved starting digests.

The [completion plan](../tasks/2026-11-05-audit-completion/plan.md) and
[record](../tasks/2026-11-05-audit-completion/task.json) contain final repository checks,
current recovery and preservation evidence. These local syntax/package checks do not
certify trusted admission, runtime isolation or inference readiness. No dependencies,
effective policies, model/data artifacts or frozen architectural decisions were changed.

[A10](a10-xgboost-preprocessing.md#incomplete-artifact-prerequisites) and
[A14](a14-evaluation-handoff.md#incomplete-benchmark-prerequisites) remain incomplete
with concrete artifact and benchmark prerequisites. These documentation corrections
do not close either finding.
