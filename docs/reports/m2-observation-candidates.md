# M2 increment 2 — observation provenance and candidates

2026-11-06; local branch `feat/m2-observation-candidates`, based on
`d920ffc89a2673945142c5eb6442a56069cc27d7`. Risk: **L1 engineering**. PR #1 is
merged; its source tree equals the current base. This increment is uncommitted.
The [plan](../tasks/2026-11-06-m2-observation-candidates/plan.md) and
[task record](../tasks/2026-11-06-m2-observation-candidates/task.json) preserve
authorization, architecture alignment, acceptance criteria, verification and recovery.
Status: **READY_FOR_REVIEW**; only this bounded increment is implemented.

## Implemented

- Three versioned public metadata schemas: observation sources, aggregate quality
  reports and unpublished candidates. Closed fields reuse the existing observation
  contract and strict local schema registry.
- Independent `rent_data` functions build deterministic candidates, revalidate the
  complete artifact against supplied source bytes and project every observation.
  Exact source digests/sizes/counts and stable source-record lineage are bound to
  the recipe, inventory and aggregate report; no record is silently filtered.
- Existing non-window eligibility checks are shared through a public helper without
  changing split rules. Invalid/unresolved facts remain in the candidate/report.
- Canonical JSON preserves its safe size-limit exception instead of relabeling it
  as an encoding failure; rejection thresholds and supported wire fields are intact.
- Source/wheel packaging includes `rent_data` and its synthetic suite. Architecture
  fixtures verify public-contract access and forbidden data/harness/platform edges.

The [contract documentation](../architecture/observation-candidates-v1.md) defines
exact-wire versus canonical identities, inclusive acquisition bounds, uncertainty,
canonical ordering, aggregate count semantics and the bounded JSON transport.
No raw CSV reader, sanitizer, matching algorithm, release publisher, DVC/MLflow
integration or model operation is added.

## Verification

| Check | Final result |
| --- | --- |
| Candidate synthetic suite | **98 passed**, including fresh interpreters with different hash seeds, tampering after resealing, identity/time/policy conflicts and population/uncertainty conservation. |
| Existing evaluation contracts | **114 passed** with unchanged v1 policy semantics. |
| Full checkout | **569 passed**, zero failed/skipped; one existing deprecation warning. |
| Extracted source and wheel | **377 passed each**, zero failed/skipped; 13 schemas and fresh child imports exercised. |
| Offline frontend | **38 passed**, zero failed/skipped. |
| Ruff, architecture, actionlint, notebooks and whitespace | Passed. |
| Final documentation/task/preservation check | Passed: 148 starting files unchanged, eight scoped edits verified, both unrelated reporting files preserved; 19-file increment, all ten verified implementation hashes, 22 task records and 50 local links/anchors. Branch/HEAD/index and whitespace checked. |
| Failed | Intermediate size-error diagnostic regression corrected; no unresolved source/test failures. |
| Skipped | Real-data use, acquisition, DVC releases/restoration, training/evaluation and protected/runtime tests; outside scope. |
| Unavailable | New-revision Linux CI and independent protected/data evidence; no commit/push. |

Exact commands, initial failure/correction, logs and recovery are in the
[verification record](../tasks/2026-11-06-m2-observation-candidates/plan.md#verification-evidence).
Existing notebooks, legacy ML/API/acquisition code and dependencies were not edited.

## Limits and single recommended next increment

Verified bytes are the supplied **metadata envelopes**, not the underlying private
raw snapshots. Raw-source/policy/evidence references are declarations; their truth,
privacy, completeness and authorization remain external. Aggregate counts are not
benchmark or identity-quality results. No actual feature/target-aggregate lineage,
protected holdout isolation or real-data eligibility is certified. The 1 MiB source/
artifact bounds fail without truncation; scalable release transport is still needed.
**A14 and M2's reproducible-run/development-evaluation exit gate remain open.**

**Next:** immutable Git/DVC release envelopes and local restoration verification,
initially synthetic. Decide scalable inventory transport, storage/access/retention
and provenance/quality gates before real publication. Any real input projection still
requires authorized private field handling and reviewed domain/currency policy;
defensible time evidence or approved remediation precedes temporal eligibility,
and reviewed matching evidence precedes confirmed/unseen-property claims. No facts
are reconstructed from the historical CSV's copy dates or current scraper metadata.
