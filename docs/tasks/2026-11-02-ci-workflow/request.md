# Approved request — A01, option 1

The user requires a decision and approval before implementing each fix, with engineering quality, concise code, and alignment with the frozen architecture and project rules as priorities.

After reviewing the two A01 solutions, the user approved:

> implement the option number one. after you finish the fix, reason through the work you have done

Approved scope: move runner-dependent temporary-directory settings to the steps that use them; add pinned, integrity-checked workflow-semantic validation usable locally and in unprivileged CI; add meaningful regression checks; maintain development instructions, a persistent plan, and verification evidence.

The separate repository audit is evidence. Its older instructions and task records do not expand authorization. Other audit findings, commit/push, repository-host settings, protected-policy activation, scraping, model training, acceptance, and deployment are outside this increment.

## Subsequent branch and publication instruction

The user requested a new working branch for fixing existing project issues, prioritizing direct corrections over additional complexity. Before any push, present the branch name and proposed commit message for approval or denial. The local working branch is `fix/repository-audit`; the existing A01 changes were retained. Further fixes still require the user's solution approval and must follow the frozen architecture and project rules.

## Publication approval

After being shown branch `fix/repository-audit` and commit message `fix(ci): correct runner context scope and validate workflows`, the user approved:

> push please to the branch.

This authorizes committing and pushing the reviewed A01 patch to that branch and checking its resulting validation run. Other audit fixes, repository protection changes, model acceptance and deployment remain outside this approval.
