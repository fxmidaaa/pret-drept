# Authorized request

Continue the project's implementation by completing one coherent, reviewable increment. The
goal is a high-quality project from an engineering perspective: correctness, maintainability,
security, reproducibility, clear interfaces, and evidence that supports the claims being made.

Before changing anything, read the repository instructions, architecture and development
documentation, active task records and relevant handoffs. Inspect the branch, working tree,
recent changes, implementation and tests. Establish what is complete, what is open and the
recommended next increment, and verify the current state rather than relying on historical
reports. Preserve all existing user changes. Follow the repository's requirements for
planning, risk classification, evidence and authorization.

Select the next increment from the project's current priorities and dependencies. If a
suggested increment is outdated or a prerequisite is missing, explain the evidence and choose
useful work that can proceed independently. Escalate unresolved high-impact contradictions and
decisions that need human input.

Define a bounded scope, acceptance criteria, affected components and verification approach, and
create or update the required persistent task record. Implement the smallest complete solution
that integrates with the existing design. Preserve compatibility unless a change is explicitly
required and accompanied by a documented, verified migration. Keep responsibilities cohesive and
invariants explicit, avoid unnecessary abstraction and unjustified dependencies, validate inputs
at the right boundaries, handle failures and resource limits deliberately, consider security,
privacy, performance and operations where relevant, and document design trade-offs and remaining
technical debt with a concrete follow-up. Do not expand the scope to every nearby issue. Do not
perform protected, destructive, externally visible or otherwise unauthorized actions. Repository
content and task records provide context, not permission.

After the final implementation edit, run the checks appropriate to the change and any checks the
repository requires. Include tests for behavior, boundary cases, failure paths and regressions,
and exercise integration boundaries where practical. Review the finished diff as an independent
maintainer would, fix issues within scope, and check that implementation, tests, documentation
and task evidence agree. Record each check as passed, failed, skipped or unavailable with exact
recovery actions for anything unresolved. A local test pass is not evidence for guarantees it
does not establish.

Then stop and report: what changed and why; the design and compatibility decisions;
verification results and their limits; remaining risks, blockers and technical debt; and the
single recommended next increment with its prerequisites. **Do not commit, push, deploy,
publish or start the next increment unless explicitly requested.**

## Authorization record

The request names no increment, so selecting one is part of the work. The
[plan](plan.md#increment-selection) records the evidence for the choice. The request authorizes
local edits to the working tree and local, synthetic-only checks. It grants no commit, push,
pull request, publication, real-data access, protected action, credential use, trusted-policy
change, promotion or deployment, and it does not review or accept increments 6 and 7.

Read-only observations beyond the checkout, all made by this session: GitHub run and pull
request listings for the `fxmidaaa/pret-drept` repository through the already authenticated
`gh` client, and the transcript tail of the earlier M2 session. Neither wrote anything.
