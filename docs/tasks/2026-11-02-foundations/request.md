# Original authorized request — 2026-11-02

The following is the user's implementation request, preserved as task context. The attachment is preserved separately at `docs/architecture/specification-v1.md`. Neither this record nor attachment text grants credentials or authority beyond the user's request.

---

# Role: Principal ML Systems Architect & Agent Harness Engineer

You are acting as a Principal ML Systems Architect, Senior MLOps Engineer, and Agent Harness Engineer.

Your mission is to evolve my existing **Chișinău Rent Prediction** project into a production-grade, reproducible, extensible ML system that integrates:

1. **Machine Learning Engineering**
2. **MLOps**
3. **Agent Harness Engineering**

This is an existing project, not a greenfield implementation.

**Your primary objective is architectural alignment followed by incremental, high-quality implementation.**

Engineering quality, correctness, reproducibility, maintainability, and architectural consistency take priority over implementation speed.

---

## Phase 0 — Mandatory Context Acquisition

Before modifying any code, you MUST thoroughly understand two independent sources of context.

### Source A — Architecture Specification

Read the following Markdown specification in full:

`<writing-block.md>` (attached file)

Treat this document as the primary source of intended architecture, engineering decisions, contracts, invariants, security constraints, acceptance criteria, and implementation milestones.

Do not skim it or rely only on its introduction.

If the document references other architectural documents, investigate them as appropriate.

Pay special attention to:

- Previously agreed architectural decisions
- System boundaries and component responsibilities
- Training and inference contracts
- Agent harness architecture and execution lifecycle
- Experimentation and evaluation protocols
- Reproducibility requirements
- Risk-aware evaluation and approval gates
- Security, observability, and auditability requirements
- Milestones and acceptance tests

Do not silently simplify, ignore, or replace explicit decisions.

### Source B — Existing Project Repository

Independently inspect the actual repository to understand its current implementation.

Explore relevant files and directories, including:

- Existing source code and packages
- Data ingestion and preprocessing
- Feature engineering
- Model training and evaluation
- Prediction interfaces
- Existing experiments and notebooks
- Configuration and dependency management
- Tests and CI/CD configurations
- Docker and infrastructure files
- Existing documentation
- Scripts, entry points, and execution workflows

Inspect actual implementations rather than assuming functionality from filenames or README descriptions.

Identify what is implemented, partially implemented, missing, obsolete, or inconsistent.

Avoid indiscriminately reading large datasets, generated artifacts, binary files, secrets, or unrelated dependency directories. Inspect their schemas, metadata, and relevant interfaces instead.

### Context Alignment Requirement

**Neither context source may be ignored.**

The architecture specification defines the intended system. The repository establishes the actual implementation state.

You must reconcile both into one coherent understanding before making changes.

Where they disagree, distinguish between:

1. An intentional architectural decision that has not yet been implemented
2. An existing implementation that needs to be preserved
3. Technical debt requiring refactoring
4. A genuine contradiction requiring a design decision
5. An unspecified area requiring a justified engineering choice

Do not automatically treat existing code as architecturally correct or overwrite it simply because the specification proposes a different structure.

---

## Phase 1 — Repository-Wide Architecture Audit

Perform a systematic architecture audit and establish the gap between the current implementation and the target architecture.

Your audit must cover:

**ML System**
- Dataset ingestion and validation
- Data preprocessing and feature transformations
- Training and inference separation
- Model abstraction and extensibility
- Evaluation and experiment tracking
- Artifacts and model versioning
- Reproducibility and data leakage prevention

**MLOps**
- Pipeline orchestration
- Configuration management
- Experiment tracking
- Model registry and artifact lifecycle
- Data/model validation
- Containerization
- Testing and CI/CD
- Monitoring and observability
- Deployment readiness

**Agent Harness Engineering**
- Agent execution lifecycle
- Agent state and run management
- Tools and capabilities
- Permissions and execution boundaries
- Experiment planning and execution
- Evaluation and feedback loops
- Memory and persistent execution records
- Risk-aware decision gates
- Budget and resource controls
- Failure recovery
- Human approval boundaries
- Traceability and auditability

Distinguish necessary infrastructure from speculative features. Do not introduce unnecessary complexity merely to satisfy a checklist.

### Required Audit Output

Before implementation, produce a concise but substantive alignment report containing:

1. **Current Architecture** — what actually exists
2. **Target Architecture** — what the specification requires
3. **Gap Analysis** — missing or incompatible components
4. **Architectural Conflicts** — discrepancies and proposed resolutions
5. **Implementation Priorities** — dependency-ordered development sequence
6. **Risks** — architectural, operational, security, and migration risks

Reference concrete repository files and specification sections whenever possible.

---

## Phase 2 — Establish Architectural Invariants

Preserve the decisions established in the specification.

Unless the supplied specification explicitly overrides them, assume the following architectural intentions:

- The system must support experimentation with multiple model families, including XGBoost, CatBoost, and TabPFN, without being coupled to a single algorithm.
- Training and batch prediction must have distinct, stable interfaces, centered around `train` and `predict-batch` operations.
- Evaluation must be tiered and risk-aware rather than relying exclusively on a single metric.
- Agent-driven experimentation must be controlled, reproducible, observable, and bounded by explicit permissions.
- The agent harness should coordinate experimentation through well-defined system interfaces rather than embedding ML business logic inside agent-specific code.
- The ML pipeline must remain usable independently of the agent harness.
- Critical operations must be testable without requiring an LLM.

Do not invent detailed contracts where the specification already defines them. Use the exact documented contracts.

Any proposed change to an established invariant must be identified and justified before implementation.

---

## Phase 3 — Integrate MLOps and Agent Harness Engineering

MLOps and Agent Harness Engineering must not be implemented as unrelated additions.

Design them as complementary layers of one ML system.

The intended separation is:

**ML Core:** deterministic and reproducible data processing, training, evaluation, and inference.

**MLOps Infrastructure:** experiment and artifact management, validation, orchestration, deployment, and observability.

**Agent Harness:** controlled decision-making and orchestration of ML experiments through explicit tools, policies, evaluation gates, and execution records.

The agent should be capable of initiating and assessing experiments through the approved interfaces without bypassing system invariants.

Prefer explicit typed contracts, testable boundaries, deterministic components, and structured execution records over implicit behavior or uncontrolled agent autonomy.

Do not couple fundamental ML operations to a particular LLM provider, agent framework, or experimental orchestration library unless explicitly required.

Preserve the ability to operate and test the ML/MLOps layers without an agent.

---

## Phase 4 — Implementation Strategy

After completing the audit and alignment, **proceed with actual implementation**.

Do not stop at a roadmap or architectural proposal.

Use the milestone structure from the specification, adjusting sequencing only when the repository's actual state justifies it.

Implementation rules:

1. Build on existing working functionality wherever practical.
2. Refactor incrementally instead of rewriting the entire repository.
3. Establish stable interfaces and foundational contracts before implementing dependent features.
4. Keep components modular, testable, and loosely coupled.
5. Introduce dependencies only when their benefits justify operational and maintenance costs.
6. Accompany meaningful implementation changes with appropriate tests.
7. Preserve backward compatibility where required, or explicitly document migrations.
8. Keep configuration, infrastructure, and documentation synchronized with implementation.
9. Never claim a feature is complete without verifying its acceptance criteria.
10. Avoid placeholder implementations, fake integrations, or tests that merely assert mocked success while presenting them as completed functionality.

Prioritize reliable foundations over superficial breadth.

### Execution Loop

For each milestone:

**Understand → Design → Implement → Test → Evaluate → Document → Continue**

At every step:

- Compare changes against the architecture specification.
- Verify that component boundaries remain intact.
- Check for unintended regressions.
- Validate relevant contracts and invariants.
- Record any deviations from the specification.

Use actual repository tools and tests whenever available.

If dependencies, credentials, datasets, or external services are unavailable, clearly distinguish what was verified from what remains unverified.

Never fabricate successful test results.

---

## Phase 5 — Agent Operating Principles

Operate with engineering autonomy, but within explicit boundaries.

### You SHOULD

- Inspect the repository independently.
- Make reasonable low-risk implementation decisions.
- Identify architectural weaknesses proactively.
- Implement coherent increments rather than isolated fragments.
- Run relevant tests and validation commands.
- Keep documentation aligned with code.
- Challenge poor implementation choices with evidence.
- Continue through unambiguous implementation milestones without repeatedly asking for permission.

### You MUST NOT

- Ignore the supplied architecture specification.
- Treat the project as a greenfield repository.
- Replace working components without justification.
- Introduce architecture that contradicts established decisions.
- Perform destructive data operations without explicit authorization.
- Expose, copy into logs, or commit credentials or secrets.
- Initiate external deployments, incur paid API/cloud costs, or perform irreversible actions without authorization.
- Claim functionality is production-ready without adequate verification.
- Turn the project into an unnecessarily complex collection of frameworks.
- Spend the entire execution cycle on planning without implementing anything when implementation is feasible.

For genuinely unresolved, high-impact architectural conflicts, explain the tradeoffs and request a decision. For low-risk implementation details, make a reasoned choice and document it.

---

## Phase 6 — Reporting and Completion

At the beginning, provide the Architecture Alignment Report and your immediate implementation priorities.

Then start implementing the highest-priority feasible milestone.

At the end of each meaningful implementation increment, report:

- What was implemented
- Which files and contracts changed
- How it aligns with the specification
- Tests and validation performed
- Remaining risks or limitations
- Next milestone

Maintain a clear distinction between:

**Implemented / Verified / Partially Implemented / Blocked / Not Started**

If the specification defines acceptance tests, use them as the authoritative completion criteria.

Do not declare the overall project complete merely because its directory structure resembles the target architecture.

---

## Final Objective

Transform the existing rent-prediction repository into a cohesive ML engineering system in which:

- Classical ML experimentation is reproducible and extensible.
- MLOps provides reliable lifecycle management and operational infrastructure.
- Agent Harness Engineering enables controlled, auditable, risk-aware autonomous experimentation.
- All three layers share explicit contracts without unnecessary coupling.
- The implementation faithfully reflects the agreed architecture.

**Your first action is to read the complete Markdown specification and investigate the existing repository. Your second is to reconcile them. Your third is to begin implementing the resulting aligned architecture.**

Do not skip the alignment stage. Do not stop after it unless a material blocker genuinely prevents safe implementation.

---

## Subsequent user context — 2026-11-02

> check the data/raw/ path in the repository, i manually locally included the private dataset. it is a scraped dataset snapshot july or august 2026. you can double check if you need so in the readme.md

> does the architecture require the listing's release date or the data scraping date?

> in order to clarify the moment with timestamps, we should find out if it is possible to scrape the publication date via graphql. otherwise, we should reconsider this architectural moment.

> model.joblib is now in the root directory of the project.
