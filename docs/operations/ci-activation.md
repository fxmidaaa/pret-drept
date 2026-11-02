# Protected CI activation prerequisites

Specification §§5.4, 15.1–15.3 and 19 govern activation. This document records prerequisites and does not grant permission or activate a policy.

M1 provides Level 1 validation source only. A repository administrator/reviewer must independently review the workflow and contract/checker changes, configure protected branches/rulesets and required checks, and prevent ordinary task changes from bypassing protected gates. Exact settings, authenticated review evidence and a real CI run must be recorded before claiming enforcement. A local green run is insufficient.

A01 option 1 moves runner-dependent directory settings to the test step, where GitHub permits the runner context. The workflow also installs checksum-pinned actionlint 1.7.12 and validates workflow semantics. Use the independent [local validation command](../development.md) before publishing; the CI step cannot rescue a workflow GitHub rejects before scheduling jobs. The [A01 task](../tasks/2026-11-02-ci-workflow/plan.md) tracks local evidence and the outstanding real GitHub run. This correction preserves Level 1 permissions and does not configure host protection or activate protected CI.

The action references were resolved on 2026-11-02 using GitHub's repository API:

* [checkout v4 commit 11d5960](https://github.com/actions/checkout/commit/11d5960a326750d5838078e36cf38b85af677262)
* [setup-python v5 commit a26af69](https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065)

Follow [GitHub's secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use). Read-only permissions, immutable action references and credential isolation reduce exposure; they do not certify the complete runner or supply chain.

Future protected rebuild/verification must resolve trusted workflow, tests, policies and dependencies from a reviewed revision, execute experimental ML only in restricted workloads, keep labels in the trusted evaluator, and isolate registry credentials. Promotion must bind external authorization to the exact reviewed source, rebuilt bundle, verification and certified runtime. Deployment is a separate approval. None is implemented by this PR validation workflow.

Do not add protected data, registry credentials or cloud credentials to the existing PR job. Do not activate paid services or deployments as a test. Record unavailable Docker/host controls and use a supported independently reviewed execution environment before M3 certification.
