# Task RP-20261102-M1 — architectural foundations

State: READY_FOR_REVIEW. Risk: L2 source proposal (public contracts and security/CI foundations). This is implementation of the explicitly requested architecture, not activation of a trusted policy or authorization to promote/deploy. Effective protected operations remain gated outside this task.

## Objective and original authorization

The user requested architectural alignment of the existing Chișinău rent project against the full attached specification, followed by incremental implementation, tests, evidence and recovery records. Preserve the original request in `request.md`; the authoritative supplied architecture is `../../architecture/specification-v1.md`. The audit is `../../reports/m0-alignment.md`.

## Scope and affected modules

M0 discovery and M1 source foundations: public contracts, independent ML adapter protocol, task lifecycle and persistence, static dependency checks, package/test configuration, unprivileged CI validation source, architecture and recovery documentation. Existing `train.py`, `predict.py`, `features.py`, `api.py`, scraping behavior, frontend and Docker behavior are preserved. Existing tests may explicitly identify their unavailable private-artifact prerequisite.

Excluded: private/protected data retrieval, scraping, model training experiments, trusted policy activation, CI privilege changes on the host, registry/model acceptance, deployment, cloud resources, destructive cleanup, TabPFN/checkpoint acquisition.

## Protected invariants

Specification §§3–5, 7–16: independent ML operation; no privileged imports into ML or agent interface; trusted platform never imports experimental ML; strict versioned requests with no caller-supplied execution privileges; finite record-associated EUR/month batch results; strict atomic batch semantics; native immutable bundle contract; task records are context, never authority; no fabricated verification or substituted random evaluation.

## Acceptance criteria and verification

1. Public schemas and typed boundaries validate representative valid documents and reject unknown fields/versions, unsupported adapters/configuration, labels in prediction input, nonfinite values and duplicate record identities.
2. Bundle manifest identity excludes only its own digest; unsafe/duplicate payload paths and altered manifests are rejected. Payload loading/certification remains M4 work.
3. Task lifecycle enforces required planning and verification, preserves every §6.4 field, atomically persists records and rejects invalid transitions. No task content authorizes protected execution.
4. Architecture checker inspects actual legacy/new sources without importing them, and negative fixtures prove forbidden dependencies are detected.
5. Existing feature tests pass on Python 3.13 with project pins; private-artifact checks are reported as unavailable, never mocked into success.
6. Formatting/static/package checks pass for added code. CI source has minimal permissions, pinned actions, bounded execution and no protected credentials. Remote settings and execution remain unverified until independently activated.
7. Reports distinguish source implementation, executed checks, blocked prerequisites and exact recovery actions.

## Plan

1. Complete M0 and preserve the full architecture specification and original request.
2. Create an isolated Python 3.13 test environment and establish a baseline.
3. Add public schemas/validation and an ML adapter protocol without changing legacy behavior.
4. Implement task lifecycle/persistence and dependency checks.
5. Add real contract/unit/negative tests and unprivileged CI validation source.
6. Run checks after final changes; document evidence and recovery; prepare a reviewable patch against the audited commit.

## Checkpoint and decisions

M0 complete with explicit unknowns. Clean source at `e08344dfab8ee03ef155e885c83153b5558ee178` copied locally to branch `architecture/m1-foundations`; original checkout is unchanged during implementation. Use `rent_platform` as the future Python namespace to avoid shadowing stdlib `platform`. JSON schemas implement the specification's conceptual fields; adapter configuration is validated through an explicit schema registry, never arbitrary import paths. No new model implementation is claimed by an adapter protocol.

Python 3.13.16 was downloaded into this task's isolated workspace after the restricted-network attempt failed. Initial system-Python baseline invocation could not collect tests because pytest was absent. No successful test result exists yet.

## Evidence, identifiers, approvals and blockers

Evidence: M0 report; forthcoming `../../reports/m1-verification.md`. Runner/MLflow/CI IDs: none; no experiment or remote job executed.

Pending external actions: independent review/release of protected CI/policies; repository-host branch/ruleset settings. These are not enabled by this task record.

Blockers at initial checkpoint: authorized private data and trained artifact absent; temporal/property identity feasibility unknown; Docker daemon unavailable; storage, serving, retention and TabPFN gates unresolved. Update: the user supplied the historical CSV; its 4,528 rows have no timestamps and contain older sensitive columns. Data presence is resolved; defensible chronology, physical-property identity and the trained artifact remain unresolved. See the M0 addendum.

Initial recovery action was to inspect Git state and establish the test baseline; that work is complete. The final recovery action is recorded below and in task.json.

## Threat/risk assessment for this source proposal

| Threat | Source-level response | External prerequisite |
|---|---|---|
| Caller injects commands, host paths or identity | Closed request fields; registry-validated parameters; caller principal absent | M3 authenticates channel and authorizes/mounts resolved inputs |
| Mutable records or model claims treated as authority | Immutable parsed payload; task evidence explicitly context; approval outside bundle | Independent trusted evidence and exact-artifact approval |
| Protected workflow altered in the working tree | PR job has no protected credentials; source tests identify basic unsafe configuration | Reviewed protected revision and host rules enforced by administrator |
| Data or model material leaks into deliverables | Raw CSV retained only in original ignored path; schema/aggregate metadata only | Future dataset release field projection, storage permissions and model privacy verification |

No effective protected policy, holdout access, registry identity or deployed state is changed by the M1 proposal. Source implementation is authorized by the user's request; protected activation/review remains external. Formal independent verification of the deployed trust boundary cannot be claimed from this development session.

## Final checkpoint

M1 source applied to the original checkout at the unchanged audited HEAD; no commit/push, deployment or protected policy activation. **137 combined tests passed, zero failed/skipped** with the real model. Architecture, lint, format, package/schema and input-integrity checks passed; the remaining warning and historical failures are recorded in the M1 report. Raw data/model hashes and legacy ML/application source are unchanged. GraphQL source timestamp fields are verified on public data; historical private-ID checks were rejected before execution and remain unperformed.

M1 is ready for source review; the overall architecture is incomplete. Next recovery action: reconcile Git and final evidence, then scope M2 timestamp-aware ingestion and data lineage without fabricating history or exporting private IDs without explicit authorization. Independent protected CI/runtime review, real container isolation, reviewed property identities and official temporal evidence remain prerequisites for later gates.
