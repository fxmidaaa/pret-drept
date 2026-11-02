# A01 option 1 — implementation, verification, and engineering review

Date: **2026-11-02**. Task: [RP-20261102-A01](../tasks/2026-11-02-ci-workflow/task.json). Baseline: `0427a092426c11efe7f30110c3d26e94c9bfb969`. Status: **implemented and locally verified; ready for review**. Actual GitHub execution is unavailable pending separately approved publication. No commit/push or repository-host policy change occurred.

## Change and architectural fit

The previous job-level `MPLCONFIGDIR` and `NUMBA_CACHE_DIR` expressions used the unavailable `runner` context, causing GitHub to reject the workflow before scheduling a job. Both settings now belong to the deterministic-test step. The job retains its read-only contents permission, timeout, immutable action references, and disabled checkout credential persistence. See [GitHub context availability](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability).

The workflow explicitly installs and runs actionlint **1.7.12** before dependency installation. A small standard-library installer downloads the maintainer's versioned platform archive, verifies its reviewed SHA-256, reads only the regular `actionlint` member, and atomically replaces the executable in the requested development-tool directory. Unsupported platforms and checksum mismatches fail before replacement. No tool is downloaded by pytest; the pinned executable must already exist. Local commands validate workflow semantics independently of the workflow's ability to start.

The installer has reviewed digests for macOS/Linux on ARM64/x86-64. Real installation and execution were verified on macOS ARM64 only. The current Linux CI path remains unexecuted locally. Version/checksum source: [maintainer release](https://github.com/rhysd/actionlint/releases/tag/v1.7.12) and [release checksums](https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_checksums.txt). Optional shellcheck/pyflakes integrations are explicitly disabled so workflow-semantic checks do not depend on unpinned tools present on a particular host.

| Architecture requirement | Implementation/evidence |
|---|---|
| §§1.2, 4.3: maintainability and independent ML | Configuration is scoped to its consumer; the standalone development installer adds no ML/runtime dependency or coupling |
| §§5.4, 15: trust and CI levels | Existing Level 1 restrictions remain; this source correction does not activate protected policy or configure repository rules |
| §6: risk-based planning and durable context | Approved L1 request, persistent plan, lifecycle record, acceptance criteria, progress and recovery are in the task directory |
| §§6.8, 15.3: meaningful verification | Pinned semantic validation, real counterexamples, offline regression tests, complete local suite, source checks and explicit remote limits |

Changed source: `.github/workflows/validate.yml`, `scripts/install_actionlint.py`, `tests/foundations/test_ci_source.py`, and `tests/foundations/test_actionlint_install.py`. Development/CI instructions and this task's records/evidence are synchronized. Legacy code, public contracts, the frozen architecture, application requirements, and the Python development lock are unchanged.

## Executed verification

Environment: **CPython 3.13.16, macOS ARM64**; unchanged hash-locked development dependencies; existing native OpenMP runtime and supplied legacy model. Commands ran from the repository root. `ACTIONLINT` defaults to the executable beside the Python interpreter; CI sets its explicit runner-temporary path on the test step.

| Check/command | Result | Limit |
|---|---|---|
| Baseline actionlint against the unchanged workflow | **Failed as expected: two expression errors** | Reproduced A01 before implementation |
| `.venv/bin/python scripts/install_actionlint.py --directory .venv/bin` | **Passed**: real release downloaded, archive digest matched, executable installed | macOS ARM64 only |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | **Passed**, no diagnostics | Source semantics; no remote jobs executed |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra tests/foundations/test_ci_source.py tests/foundations/test_actionlint_install.py` | **6 passed** | Includes the existing CI-restriction assertion plus five new cases |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short` | **142 passed, 0 failed, 0 skipped**, 68.24 s | One existing Starlette/httpx deprecation warning; no model-quality or privacy certification |
| `.venv/bin/python -m ruff check src scripts tests/foundations tests/conftest.py` | **Passed** | Scoped foundations/tooling coverage; legacy lint debt remains |
| `.venv/bin/python -m ruff format --check src scripts tests/foundations tests/conftest.py` | **Passed**, 21 files | Same scope |
| `.venv/bin/rent-check-architecture --root .` | **Passed** | A05 static-analysis gaps remain unresolved; no isolation certification |
| `uv pip check --python .venv/bin/python` | **Passed**, 58 packages compatible | Dependency compatibility only |
| `.venv/bin/python -m build --no-isolation --outdir /private/tmp/pret-drept-a01-20261102/distributions` | **Passed**, wheel and sdist built | A11's extracted-sdist test defect remains outside scope |
| Distribution member inspection | **Passed**: no raw CSV, private model payload, or development environment | Filename inventory, not a new privacy proof |
| Private-input SHA-256 comparison and protected-source Git comparison | **Passed**: both inputs unchanged; legacy/ML/harness/contracts/architecture/dependency pins unchanged | Hashes only; no raw records reported |
| `git diff --check`, final task reload, changed-document link/whitespace checks | **Passed** | Final records are validated after recording results |
| Actual GitHub workflow execution | **Unavailable** | Requires separately approved publication and inspection of a real run |

The full suite used `PYTHONDONTWRITEBYTECODE=1`, `MPLCONFIGDIR=/private/tmp/pret-drept-a01-20261102/matplotlib`, and `NUMBA_CACHE_DIR=/private/tmp/pret-drept-a01-20261102/numba`. Local test/build logs and distribution artifacts are under `/private/tmp/pret-drept-a01-20261102`; no large logs or binaries are committed as task records.

Setup recovery: the restricted-network checksum request failed DNS resolution; an authorized read-only request retrieved the maintainer list. Offline Python dependency installation then failed because `annotated-doc==0.0.5` was absent from the cache. Recovery was `UV_CACHE_DIR=/private/tmp/pret-drept-audit-20261102/uv-cache uv pip sync --require-hashes --python .venv/bin/python requirements-dev.lock` with authorized network access, followed by `uv pip install --offline --no-deps --no-build-isolation --python .venv/bin/python -e .` using the same cache directory. No pins changed. All deterministic checks subsequently ran without dependency or tool downloads.

## Engineering review after the fix

1. **The correction addresses the scheduling failure.** The positive check invokes the real pinned validator on every current workflow. Each negative fixture moves one real setting back to job-level `env` and requires the corresponding expression error, demonstrating that the maintained checks detect the original failure mechanism.
2. **Configuration remains close to its consumer.** The test step is the consumer of the matplotlib/numba temporary directories. Static checking, source installation, architecture inspection, and distribution building do not import the legacy model stack. A shared environment preparation step would add an ordering dependency without solving another current requirement.
3. **Tool acquisition has explicit failure behavior.** The real installation passed integrity verification; synthetic corrupt downloads preserve an existing executable, and unsupported platforms do not attempt a download. Only one regular archive member is read; arbitrary archive paths are never extracted. Network and upstream availability remain setup dependencies, with checksum mismatches failing closed.
4. **Local validation remains essential.** The added CI check protects workflows GitHub can schedule. It cannot run inside a workflow already rejected by GitHub, so the standalone local command is part of the documented pre-publication procedure.
5. **Evidence stays within its actual authority.** These are development-source checks. The architecture checker still has the separately audited A05 gaps, package extraction still has A11, and repository protection, runtime isolation, protected verification, model acceptance and deployment remain separate. Other audit findings were not changed or declared resolved.

No further implementation changes were identified in this review. This is a review by the implementing agent, not independent protected verification. The patch remains ready for user review.

## Exact next recovery action

Read the current task record and inspect `git diff` plus untracked task/tool/test files. Re-run the standalone actionlint command and relevant checks if source changes. Obtain separate publication approval before commit/push; after authorized publication, inspect the GitHub run for the exact published commit, verify jobs actually execute, record its URL/identifier and conclusion, and investigate any Linux-specific failure before claiming remote CI success. Address A02 or another audit finding only after its separate design decision and approval.
