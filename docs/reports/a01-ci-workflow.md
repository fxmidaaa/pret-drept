# A01 option 1 — implementation, verification, and engineering review

Date: **2026-11-02**. Task: [RP-20261102-A01](../tasks/2026-11-02-ci-workflow/task.json). Baseline: `0427a092426c11efe7f30110c3d26e94c9bfb969`. Status: **implemented, published with user approval, and verified locally and in GitHub CI**. Published commit: [`2a5beef`](https://github.com/fxmidaaa/pret-drept/commit/2a5beefc74ff51f3c962156a1cf6eaf2f1ae287e), branch `fix/repository-audit`. No repository-host policy change occurred. The post-CI evidence update was recorded locally after the approved source push; no additional commit/push was performed.

## Change and architectural fit

The previous job-level `MPLCONFIGDIR` and `NUMBA_CACHE_DIR` expressions used the unavailable `runner` context, causing GitHub to reject the workflow before scheduling a job. Both settings now belong to the deterministic-test step. The job retains its read-only contents permission, timeout, immutable action references, and disabled checkout credential persistence. See [GitHub context availability](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability).

The workflow explicitly installs and runs actionlint **1.7.12** before dependency installation. A small standard-library installer downloads the maintainer's versioned platform archive, verifies its reviewed SHA-256, reads only the regular `actionlint` member, and atomically replaces the executable in the requested development-tool directory. Unsupported platforms and checksum mismatches fail before replacement. No tool is downloaded by pytest; the pinned executable must already exist. Local commands validate workflow semantics independently of the workflow's ability to start.

The installer has reviewed digests for macOS/Linux on ARM64/x86-64. Real installation and execution were verified locally on macOS ARM64 and subsequently on Linux x86-64 in the approved GitHub run. macOS x86-64/Linux ARM64 execution remains unverified. Version/checksum source: [maintainer release](https://github.com/rhysd/actionlint/releases/tag/v1.7.12) and [release checksums](https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_checksums.txt). Optional shellcheck/pyflakes integrations are explicitly disabled so workflow-semantic checks do not depend on unpinned tools present on a particular host.

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
| Actual GitHub workflow execution | **Passed**, [run 41520470597](https://github.com/fxmidaaa/pret-drept/actions/runs/41520470597), exact published commit | **130 passed, 12 skipped**, one pytest warning; private-artifact checks unavailable in CI |

The full suite used `PYTHONDONTWRITEBYTECODE=1`, `MPLCONFIGDIR=/private/tmp/pret-drept-a01-20261102/matplotlib`, and `NUMBA_CACHE_DIR=/private/tmp/pret-drept-a01-20261102/numba`. Local test/build logs and distribution artifacts are under `/private/tmp/pret-drept-a01-20261102`; no large logs or binaries are committed as task records.

Setup recovery: the restricted-network checksum request failed DNS resolution; an authorized read-only request retrieved the maintainer list. Offline Python dependency installation then failed because `annotated-doc==0.0.5` was absent from the cache. Recovery was `UV_CACHE_DIR=/private/tmp/pret-drept-audit-20261102/uv-cache uv pip sync --require-hashes --python .venv/bin/python requirements-dev.lock` with authorized network access, followed by `uv pip install --offline --no-deps --no-build-isolation --python .venv/bin/python -e .` using the same cache directory. No pins changed. All deterministic checks subsequently ran without dependency or tool downloads.

## Authorized publication and exact-commit CI

After the branch and message were presented, the user instructed: "push please to the branch." The reviewed ten-file patch was committed as `2a5beefc74ff51f3c962156a1cf6eaf2f1ae287e` with message `fix(ci): correct runner context scope and validate workflows` and pushed without force to `origin/fix/repository-audit`. The remote ref and local upstream both matched that commit.

[GitHub run 41520470597](https://github.com/fxmidaaa/pret-drept/actions/runs/41520470597), job `125534882330` (`foundations`), completed successfully at `2026-11-02T20:35:37Z` for that exact SHA. It used Ubuntu 24.04, Python **3.13.17 x86-64**. Verified steps: checksum-pinned actionlint installation/validation, hash-locked dependency and source installation, lint/format, architecture inspection, deterministic tests, and wheel/sdist build. Logs report **130 passed, 12 skipped, 1 warning in 4.11 s**. All twelve skips explicitly identify the absent private `model.joblib`; CI did not load, substitute, or certify that artifact. The existing pytest deprecation remains, and the host also warned that the pinned actions target deprecated Node.js 20 and were run under Node.js 24. No action pins were changed in response.

This resolves A01's missing real CI evidence. It does not establish protected host enforcement, model acceptance, production readiness, or resolution of other audit findings. Only the approved source commit was pushed; this subsequent evidence checkpoint remains local until a separately approved publication.

## Engineering review after the fix

1. **The correction addresses the scheduling failure.** The positive check invokes the real pinned validator on every current workflow. Each negative fixture moves one real setting back to job-level `env` and requires the corresponding expression error, demonstrating that the maintained checks detect the original failure mechanism.
2. **Configuration remains close to its consumer.** The test step is the consumer of the matplotlib/numba temporary directories. Static checking, source installation, architecture inspection, and distribution building do not import the legacy model stack. A shared environment preparation step would add an ordering dependency without solving another current requirement.
3. **Tool acquisition has explicit failure behavior.** The real installation passed integrity verification; synthetic corrupt downloads preserve an existing executable, and unsupported platforms do not attempt a download. Only one regular archive member is read; arbitrary archive paths are never extracted. Network and upstream availability remain setup dependencies, with checksum mismatches failing closed.
4. **Local validation remains essential.** The added CI check protects workflows GitHub can schedule. It cannot run inside a workflow already rejected by GitHub, so the standalone local command is part of the documented pre-publication procedure.
5. **Evidence stays within its actual authority.** These are development-source checks. The architecture checker still has the separately audited A05 gaps, package extraction still has A11, and repository protection, runtime isolation, protected verification, model acceptance and deployment remain separate. Other audit findings were not changed or declared resolved.

No further implementation changes were identified in this review. This is a review by the implementing agent, not independent protected verification. The reviewed patch was published with user approval and its real GitHub validation passed.

## Exact next recovery action

Continue on `fix/repository-audit` at published commit `2a5beefc74ff51f3c962156a1cf6eaf2f1ae287e`; its exact-commit CI run passed. The only subsequent local edits record publication/CI evidence in this report and the task record. Present the branch and proposed commit message before publishing those updates or any further changes. Address A02 or another audit finding only after its separate design decision and approval. Re-run relevant checks after any source edit; existing protected-policy, isolation, data/evaluation, and other audit gaps remain outside A01.
