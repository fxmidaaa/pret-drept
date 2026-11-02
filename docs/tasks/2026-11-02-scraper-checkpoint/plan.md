# RP-20261102-A02 — preserve scraper checkpoints

Risk: **L1 engineering**. Approval: [request](request.md). Branch: `fix/repository-audit`. Baseline: `2a5beefc74ff51f3c962156a1cf6eaf2f1ae287e`. Two existing local A01 evidence updates are unrelated work and must remain intact.

## Objective, scope and architecture

Fix audit A02 inside `scrape.py`, preserving the script entry point and the ML/API/training paths. Add an optional explicit checkpoint path so a future authorized collection can use separate working state. Use only existing dependencies and the standard library. Affected files: scraper, new checkpoint tests, README/development instructions, the CI static-check file selection, and this task's records/evidence.

Specification §§4.3, 6, 8.3 and 8.5 apply: keep acquisition independent of the harness; preserve raw observations; do not present a mutable resume checkpoint as a sealed dataset release. This is a bounded legacy storage correction, not M2 data publication or a migration. No real acquisition, dataset rewriting, training, protected-label access or publication is part of verification. A03 and A04 remain open; unknown optional columns are preserved rather than silently redacted or assigned a new policy.

## Acceptance criteria

1. An incompatible, ambiguous or malformed existing CSV fails before any fetch and remains byte-identical. No row with an invalid/missing/duplicate listing key is silently dropped. Existing valid 16-character lowercase hexadecimal keys, including leading zeros, retain their identity.
2. Valid CSV checkpoints round-trip all records and optional cell text; missing files initialize empty state without creating files. Empty existing files fail; a valid header-only checkpoint represents empty state.
3. Saves validate input and the existing destination, refuse to drop existing identities, write a private temporary file in the destination directory, flush/fsync it, validate its readable population, and replace the destination atomically. Simulated write/fsync/replace and incomplete-output failures preserve the old file and clean temporary files. Symlink checkpoints fail explicitly.
4. Existing compatible collection/resume behavior is exercised with synthetic listings and blocked network access. Preserve the default path and add a documented optional path; no automatic conversion, timestamp fabrication, or inference/training change.
5. New regression checks, the full local suite, scoped lint/format, semantic workflow validation, architecture inspection, task reload, documentation links and diff checks pass after relevant edits. Separate skipped/unavailable checks and preserve exact recovery steps.

## Plan and verification

1. Persist approval/plan/task context and digest the pre-existing A01 evidence/private inputs without reporting row values.
2. Add offline regression fixtures and reproduce the legacy-schema rejection failure against unchanged code.
3. Implement strict record-preserving CSV loading and atomic validated saving in the existing script; wire the optional checkpoint path and safe CLI error.
4. Update collection instructions and CI/development static-check selections for the changed scraper/tests.
5. Run targeted failure/round-trip tests, then the complete local suite and final checks. Review scope/architecture, preserve input/A01 hashes, and record evidence in `../../reports/a02-scraper-checkpoint.md`.

## Failure and recovery boundaries

Use temporary synthetic CSVs; block all requests in scraper tests. Validate before replacing a checkpoint and avoid echoing cell values in errors. Atomic replacement assumes a local filesystem supporting same-directory `os.replace`; do not claim concurrent-writer coordination, power-loss durability, DVC restoration, field privacy, or temporal-history certification. A hard kill may leave a private temporary file; the old checkpoint remains the recovery source before replacement. Do not replace published releases through this legacy checkpoint API.

Recovery: read `task.json`, reconcile the diff with this scope and preserve the two prior A01 evidence updates. Implement and verify locally; present the branch and commit message before publication. Any real-data migration, A03/A04 policy decision, or live collection requires separate approval.

## Final local checkpoint

The approved storage repair is implemented in the existing script. **31 checkpoint regressions and all 173 local tests passed**, with zero failures/skips and one existing deprecation warning. Scoped static/formatting, workflow semantics, architecture, preservation and context checks passed. Review caught and corrected long-field parsing compatibility and strengthened CLI test isolation. See [verification and engineering review](../../reports/a02-scraper-checkpoint.md). Publication remains pending user approval of the branch and proposed commit message; no A02 remote run is claimed.

Publication update: the user subsequently approved the presented branch/message with "push". Commit/push the reviewed A02 files with `fix(scraper): preserve checkpoints with validated atomic saves`, then inspect the exact-commit GitHub run. Preserve the unrelated local A01 evidence updates.
