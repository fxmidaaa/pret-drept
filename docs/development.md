# Development and verification

Use Python 3.13. The M1 evidence uses CPython 3.13.16 on macOS ARM64. The original application's direct pins remain in `requirements.txt`; `requirements-dev.lock` pins their transitive closure plus test/build tools with hashes, resolved universally for Python 3.13 with platform markers for Mac/Linux/Windows. Local installation is verified; each published revision also needs a successful Linux CI run. This is a development/test environment lock, not a certified inference image.

On macOS, the existing XGBoost wheel also needs the native OpenMP library (`brew install libomp`). Discovery reached the real model and demonstrated a missing `libomp.dylib`; libomp **23.1.4** was installed to resolve this environment prerequisite without changing ML code or Python pins. Python package hashes do not cover native libraries. A future certified inference image must preserve and verify its complete runtime. See [XGBoost installation guidance](https://xgboost.readthedocs.io/en/stable/install.html).

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python scripts/install_actionlint.py --directory .venv/bin
.venv/bin/actionlint -shellcheck= -pyflakes=
.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/rent-check-architecture --root .
.venv/bin/python -m pytest -q -ra
.venv/bin/python -m build --no-isolation
```

Workflow validation uses development-only **actionlint 1.7.12**. The explicit installer supports macOS/Linux on ARM64 and x86-64, downloads the maintainer's release archive, and checks its pinned SHA-256 before installing the executable. It replaces no Python dependencies. Installation needs network access; subsequent semantic checks and regression tests run offline. Optional shellcheck/pyflakes integrations are disabled to keep the semantic tool set identical locally and in CI. Review version/checksum changes together against the [maintainer release](https://github.com/rhysd/actionlint/releases/tag/v1.7.12).

The tests require that pinned executable beside the Python interpreter, or at an explicitly supplied `ACTIONLINT` path. A missing/wrong validator fails with setup instructions rather than silently skipping. Regression fixtures move each runner-dependent directory back to job-level `env` and require a semantic error. Run the standalone actionlint command **before publication**: a GitHub-rejected workflow cannot start its own validation. These checks establish workflow semantics, not successful remote execution or protected policy enforcement.

The legacy feature suite runs without private data. `/health` and homepage tests run without a model. Twelve legacy prediction/options/privacy checks are marked `legacy_artifact`; they execute normally when the private `model.joblib` exists and are explicitly skipped otherwise. Missing artifacts are never replaced with fake models. A skipped private-artifact check cannot certify model behavior, privacy or runtime compatibility. Protected model acceptance must fail if its required artifact/evidence is missing; these development skips are not an acceptance policy.

`tests/test_scrape.py` exercises legacy checkpoint preservation with synthetic CSVs, blocked requests and simulated write/fsync/replacement failures. It does not scrape or migrate the real dataset. Checkpoints require a `listing_key` column with unique 16-character lowercase hexadecimal values; CSV column names/row widths and UTF-8 encoding must be unambiguous. Optional cells are loaded as text to preserve leading zeros and literal values such as `NA`. The parser accommodates long cells within the file size and restores its process-wide field limit afterward. A missing file starts empty state, an empty existing file is rejected, and a valid header-only file represents an empty checkpoint. Saves refuse to drop existing identities and validate the temporary file's population and columns before atomic replacement. Concurrent checkpoint access and power-loss recovery are not certified. Resumed-field allowlisting (A04) and retry semantics (A03) remain separate audit findings.

New deterministic tests cover public request rejection, registered configuration validation, no remote schema resolution, prediction identity/population checks, manifest identities/paths, task transitions/recovery/failed writes and dependency violations. No model training, scraping, protected holdout access, promotion or deployment is performed by these tests. Contract fixtures do not simulate successful model integrations.

To intentionally refresh the lock, use `uv pip compile requirements-dev.in --python-version 3.13 --universal --generate-hashes --output-file requirements-dev.lock` in an authorized dependency-resolution environment, review the diff and rerun checks. Do not silently update legacy pins merely to make tests pass.

The workflow in `.github/workflows/validate.yml` is unprivileged PR validation source: read-only content token, no persisted checkout credentials, no secrets/OIDC, no shared package cache, pinned action commits and a timeout. It does not run protected rebuild, data access or promotion. Its source tests do not prove that GitHub rulesets, reviewer requirements or host permissions are configured. See [CI activation](operations/ci-activation.md).

Current implementation/evidence: [M1 verification](reports/m1-verification.md). Data limitations: [M0 audit](reports/m0-alignment.md), including the user-provided historical snapshot addendum. The full system is not production-ready. `train` and `predict-batch` wire contracts exist; their new operational implementations, DVC/MLflow, trusted runner, native model adapters, protected verification and deployment remain subsequent milestones.
