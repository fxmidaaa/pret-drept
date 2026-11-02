# RP-20261102-A01 — executable unprivileged validation

Risk: **L1 engineering**, because this adds development tooling and regression coverage. It does not change CI privileges, protected policies, model contracts, or data access. Original approval: [request](request.md). Baseline: `0427a092426c11efe7f30110c3d26e94c9bfb969`, clean working tree. The preceding [M1 record](../2026-11-02-foundations/task.json) is historical context.

## Objective and scope

Correct audit A01 using option 1 and make workflow-semantic validation reproducible before publication. Affected files: `.github/workflows/validate.yml`, a standalone development-tool installer, CI regression tests, development/operations documentation, and this task's records/evidence. Other audit findings remain open.

## Architectural constraints and risk assessment

Specification §§1.2, 4.3, 5.4, 6, and 15 apply. Keep the job at Level 1: read-only contents permission, pinned actions, no persisted checkout credentials, bounded execution, and no protected inputs. Keep tooling separate from ML/runtime dependencies. Source validation cannot activate trusted policies or certify model quality, isolation, or production readiness.

The external validator is executable development tooling: pin actionlint 1.7.12 and platform archive SHA-256 digests from the maintainer release, verify bytes before extracting the single executable, and fail on unsupported platforms or missing/wrong tool versions. Installation is explicit; deterministic tests must not download tools or silently skip semantic validation. Disable optional unpinned shellcheck/pyflakes integrations so local and CI semantic checks use the same tool set. Retain an independent local command because an invalid workflow cannot validate itself remotely.

## Acceptance criteria

1. Runner-dependent cache directories are configured on the test step; the job-level environment uses no runner context.
2. Pinned actionlint accepts every current workflow and rejects regression fixtures restoring each original invalid job-level reference.
3. A corrupt tool download cannot replace an existing executable; unsupported platforms fail before download.
4. Existing CI restrictions, legacy application source, dependency pins, and private inputs remain unchanged.
5. Relevant regression tests, the complete existing local suite, scoped lint/format checks, architecture checks, task-record validation, and whitespace checks pass after the final edits. Skips/warnings/unavailable checks are reported explicitly.
6. Instructions reproduce installation and local validation independently of GitHub. Evidence includes actual commands, outcomes, limits, and the next recovery action.

## Implementation and verification plan

1. Persist approval, risk, scope, acceptance criteria, and the active task record before implementation.
2. Reproduce A01 with the existing pinned validator; obtain maintainer checksums and prepare a Python 3.13 verification environment.
3. Move the two settings to the test step, install/check pinned actionlint in CI, and add semantic and tool-integrity regression tests.
4. Update development/operations instructions; run targeted checks, then the relevant complete local suite and final source checks.
5. Review the diff against architectural constraints and record evidence, limitations, and recovery in `task.json` and `../../reports/a01-ci-workflow.md`.

## Initial evidence and recovery

The cached maintainer actionlint 1.7.12 reproduces exactly two forbidden `runner` context errors in the unchanged workflow (lines 20 and 21). The maintainer's release checksum list was retrieved read-only. The initial restricted-network request failed DNS resolution; the authorized request succeeded. No repository dependencies or active policies have changed at this checkpoint.

Recovery: read `task.json`, reconcile Git state, complete the bounded implementation, and run the documented checks. A real GitHub run remains **unavailable until separately approved publication**; record its URL/conclusion after publication. Protected host configuration and all other audit findings require their own decisions.

## Final local checkpoint

Option 1 is implemented and locally verified. The full suite passed **142 tests, zero failures/skips**; the six focused CI/tool checks, pinned semantic validation, scoped lint/format, architecture command, dependency compatibility, build, and input/source-preservation checks passed. One existing deprecation warning remains. See [A01 evidence and engineering review](../../reports/a01-ci-workflow.md) for commands, reasoning, limitations and setup recovery. Current lifecycle/evidence is in `task.json`; publication and actual GitHub execution remain pending separately approved action.

Publication update: the user subsequently approved committing/pushing the reviewed A01 patch to `fix/repository-audit` with message `fix(ci): correct runner context scope and validate workflows`. Publish that patch and inspect its exact-commit GitHub run; no other audit fix is authorized by this publication approval.
