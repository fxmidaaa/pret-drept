# Module boundaries and migration

Authority: specification §§4.3, 5 and 16.5. The current application is preserved at root.
Local synthetic DVC restoration is implemented; trusted platform and orchestration
remain later work.

| Namespace/path | Responsibility | Allowed direction |
|---|---|---|
| `features.py`, `train.py`, `predict.py`, `api.py` | Existing ML/application implementation | Shared application/third-party libraries; no harness or privileged platform |
| `scrape.py` | Existing acquisition | Domain/data libraries; no harness or privileged platform |
| `src/rent_prediction` | Independent new ML interfaces; adapter protocol initially | Public contracts and ML libraries |
| `src/rent_contracts` | Versioned public documents/validation | Standard library, JSON schema validation |
| `src/rent_agent` | Local task context/lifecycle | Public contracts; no ML business logic or platform internals |
| future `src/rent_platform` | Trusted admission/execution/verification/promotion source | Public contracts and protected runtime adapters; never experimental ML implementations |
| `src/rent_data` | Non-publishing metadata candidates, release integrity/local DVC restoration and deterministic development split materialization; real-data policy review remains external | Domain/public contracts, optional safe YAML parser and public CLI; no agent or runner internals |
| `src/rent_checks` | Static development checks | AST parsing without importing inspected code |

The future `rent_platform` name avoids shadowing Python's standard-library `platform`. Direct and aliased imports, absolute `from` imports, package-escaping relative imports, and common explicit dynamic import calls are inspected. Nonliteral dynamic targets fail the check. Tests inject negative fixtures and verify no fixture is executed.

This is a structural check, not a Python security sandbox or a complete information-flow proof. Arbitrary runtime loading, subprocesses, filesystem permissions, accepted registry writes and data access require independent platform/runtime enforcement. Protected checks must use a reviewed trusted revision, not the agent's mutable implementation. Repository directories and editable checkers are not security boundaries.

Migration sequence: retain public root scripts/API first; introduce validated domain/data boundaries and adapters after dataset feasibility; then native bundles and shared batch/API inference. The initial wheel distributes new foundations only. Legacy scripts and frontend still run from the checkout with their existing requirements. Their Docker allowlist and code are unchanged in M1.
