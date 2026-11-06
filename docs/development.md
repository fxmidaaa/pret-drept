# Development and verification

Audit fixes use a [report index](reports/README.md) and one summary report per handled finding.
Each report links the detailed task plan and record, the published source, recorded verification,
and remaining work. Maintain both the summary and task evidence when an audit increment is published.

Use Python 3.13. The M1 evidence uses CPython 3.13.16 on macOS ARM64. The original application's direct pins remain in `requirements.txt`; `requirements-dev.lock` pins their transitive closure plus test/build tools with hashes, resolved universally for Python 3.13 with platform markers for Mac/Linux/Windows. Local installation is verified; each published revision also needs a successful Linux CI run. This is a development/test environment lock, not a certified inference image.

The legacy application runs from the checkout
with `python -m pip install -r requirements.txt` and a separately supplied local model.
Those runtime pins do not install pytest, Ruff, build tooling or `jsonschema`.
`python -m pip install .` installs the foundations packages and declared `jsonschema`
dependency; it does not install the legacy API/frontend/model. For repository work, use
the locked development setup below, including the editable foundations install and
explicit actionlint installation. It includes the runtime pins plus test/build tools.
Local DVC is a fourth, separate tool environment described below; it is never
installed into the ML/development environment as an incidental dependency.

Frontend checks additionally use Node.js **24.21.0**, pinned in checkout CI. This is a
development prerequisite; the served page needs no Node runtime, framework or build step.
The tests use Node's built-in runner and require no npm installation.

On macOS, the existing XGBoost wheel also needs the native OpenMP library (`brew install libomp`). Discovery reached the real model and demonstrated a missing `libomp.dylib`; libomp **23.1.4** was installed to resolve this environment prerequisite without changing ML code or Python pins. Python package hashes do not cover native libraries. A future certified inference image must preserve and verify its complete runtime. See [XGBoost installation guidance](https://xgboost.readthedocs.io/en/stable/install.html).

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python scripts/install_actionlint.py --directory .venv/bin
# Also complete the separate data-tool setup below before checkout pytest.
.venv/bin/actionlint -shellcheck= -pyflakes=
.venv/bin/python scripts/check_notebooks.py
node --test tests/frontend/*.test.cjs
.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/integration tests/test_scrape.py tests/conftest.py
.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/integration tests/test_scrape.py tests/conftest.py
.venv/bin/rent-check-architecture --root .
.venv/bin/python -m pytest -q -ra
.venv/bin/python scripts/check_distribution.py
```

`MANIFEST.in` declares the foundations source distribution, including the schema resources and
the self-contained contract, prediction and bundle, task lifecycle, and architecture tests. Keep
tests that require the application, workflow files, or project task records in checkout CI.
`scripts/check_distribution.py` builds the wheel from the source archive and runs the shipped
suite twice from a temporary extraction. The source run imports from the extracted `src/` tree.
The wheel run imports from the wheel and exercises all fifteen packaged schemas. Both runs bypass
the checkout's editable install and use dependencies from the locked development environment.

Tracked notebooks are published as source with cleared outputs. Keep executed copies that use
private data outside the tracked tree. Before committing a notebook, clear its cell outputs and
execution counts, remove embedded attachments and saved widget state, and run
`.venv/bin/python scripts/check_notebooks.py`. Stage new notebooks first so the check sees them.
CI runs the same check over all tracked `.ipynb` files without executing cells. Review notebook
source and other published assets separately.

Workflow validation uses development-only **actionlint 1.7.12**. The explicit installer supports macOS/Linux on ARM64 and x86-64, downloads the maintainer's release archive, and checks its pinned SHA-256 before installing the executable. It replaces no Python dependencies. Installation needs network access; subsequent semantic checks and regression tests run offline. Optional shellcheck/pyflakes integrations are disabled to keep the semantic tool set identical locally and in CI. Review version/checksum changes together against the [maintainer release](https://github.com/rhysd/actionlint/releases/tag/v1.7.12).

The tests require that pinned executable beside the Python interpreter, or at an explicitly supplied `ACTIONLINT` path. A missing/wrong validator fails with setup instructions rather than silently skipping. Regression fixtures move each runner-dependent directory back to job-level `env` and require a semantic error. Run the standalone actionlint command **before publication**: a GitHub-rejected workflow cannot start its own validation. These checks establish workflow semantics, not successful remote execution or protected policy enforcement.

The legacy feature suite runs without private data. `/health` and homepage tests run without a model. Twelve legacy prediction/options/privacy checks are marked `legacy_artifact`; they execute normally when the private `model.joblib` exists and are explicitly skipped otherwise. Missing artifacts are never replaced with fake models. A skipped private-artifact check cannot certify model behavior, privacy or runtime compatibility. Protected model acceptance must fail if its required artifact/evidence is missing; these development skips are not an acceptance policy.

The frontend validates response fields it displays before rendering. A valid estimate has a
positive finite `fair_price`; omitted drivers are allowed, while supplied drivers need text
labels and a known effect. A supplied verdict needs a known value and finite `deviation_pct`.
Unused response fields are ignored. Dropdowns need nonempty text lists for all four categories
before submission is enabled. Loading failures instruct the user to refresh the page.

HTTP 422 responses show recognized form-field messages as text, associate errors with controls,
and omit raw input/context objects. Unknown or unusable details use a generic validation
summary. Other HTTP errors use a service message; network failures and malformed responses
have separate messages. Dynamic rendering uses DOM text APIs. New requests clear stale results
and field errors, prevent duplicate submissions, and restore the button after completion.

`tests/frontend/app.test.cjs` executes the actual inline script with synthetic fetch responses
and a narrow DOM double that rejects HTML-writing APIs. It covers response validation,
rendering and controller state without accessing a model or the network. It does not emulate
a complete browser. When changing this boundary, also smoke-check the served page in a real
browser with synthetic responses, including literal HTML-like labels, field errors and
recovery. See the [A16 report](reports/a16-frontend-responses.md) for recorded browser evidence.

A15 makes `clean_price` require `UNIT_EUR`, `UNIT_MDL`, or `UNIT_USD` and a positive finite
amount. Unsupported currencies and malformed prices become missing required values and are
excluded during cleaning. `parse_latlon` accepts numeric JSON coordinates within the existing
city bounds. Other coordinate representations become a missing pair for the existing imputer.
`first_number` extracts finite signed tokens, including decimal commas, decimal fractions,
and exponents. Negative area and room values reach the existing range filters with their signs.

`clean_data(frame, diagnostics=report)` returns the cleaned DataFrame and replaces the supplied
dictionary with per-call counts after successful cleaning. `field_issues` counts unsupported
currencies, invalid amounts, and missing or invalid coordinate pairs across the input.
`excluded_rows` records removals at each cleaning stage in order, so those counts sum to
`input_rows - output_rows`. Field issues can overlap row exclusions. The legacy trainer prints
this report as JSON containing counts and static reason codes.

Legacy conversions divide MDL by `MDL_PER_EUR=19.5` and multiply USD by `EUR_PER_USD=0.92`.
These are fixed historical constants. A dated exchange-rate policy and conversion provenance
belong to the M2 dataset release work.

`tests/test_scrape.py` exercises legacy checkpoint preservation with synthetic CSVs, blocked requests and simulated write/fsync/replacement failures. It does not scrape or migrate the real dataset. Checkpoints require a `listing_key` column with unique 16-character lowercase hexadecimal values; CSV column names/row widths and UTF-8 encoding must be unambiguous. Optional cells are loaded as text to preserve leading zeros and literal values such as `NA`. The parser accommodates long cells within the file size and restores its process-wide field limit afterward. A missing file starts empty state, an empty existing file is rejected, and a valid header-only file represents an empty checkpoint. Saves refuse to drop existing identities and validate the temporary file's population and columns before atomic replacement. Concurrent checkpoint access and power-loss recovery are not certified.

A04 option 2 enforces `CHECKPOINT_FIELDS`: the existing reviewed feature/filter names plus `listing_key`, `price_value`, `price_unit`, `first_seen` and `last_seen`. One validator checks CSV headers before rows are read and checks every row submitted to saving before any output is created; the existing destination and serialized temporary file pass through the same reader. Unexpected columns, even in a header-only checkpoint, raise a safe `CheckpointError` without disclosing names/values or modifying the original. Column names match exactly; optional approved columns remain optional. Tests verify direct-save rejection, preservation of contaminated destinations, complete approved-column round trips, serialized-column injection rejection, and exclusion of unapproved fetched controls. Files with unexpected columns require a separately reviewed, versioned migration to a new destination retaining the original; no automatic cleanup/migration is provided. Column validation does not redact personal information from approved free text (A17).

A03 option 2 keeps failed, unavailable and malformed detail retrievals outside completed state. Successfully retrieved listings with valid eligibility fields can still be rejected; missing/invalid eligibility is unresolved. The offline tests cover failure-then-success across runs, mixed successful/failed/ineligible pages, prior rejection reuse, HTTP/transport/JSON/GraphQL errors, malformed search results, normal exhaustion, progress preservation and nonzero CLI exit. Request failures retain a maximum of three attempts with two intervening waits; GraphQL/shape failures do not add retries. Search failures stop pagination. Detail failures allow other page progress to be saved, then `AcquisitionError` reports incomplete collection and the CLI exits 1. Diagnostics use static messages/counts without source payloads, listing IDs or exception text. Failed IDs are not queued durably: retry requires encountering them again. Existing rejection markers are not reclassified. A successful command does not certify market coverage or publish a dataset release.

New deterministic tests cover public request rejection, registered configuration validation, no remote schema resolution, prediction identity/population checks, manifest identities/paths, task transitions/recovery/failed writes and dependency violations. No model training, scraping, protected holdout access, promotion or deployment is performed by these tests. Contract fixtures do not simulate successful model integrations.

`load_document` decodes byte input strictly as UTF-8 without a BOM. UTF-16/32, malformed
Unicode and unsupported wire input types are rejected; the 1 MiB limit counts UTF-8
bytes. Both `ExperimentRequest.from_document` and ordinary payload construction require
`model_schemas` and validate the envelope, adapter registration and configuration.
The canonical immutable payload does not retain caller-owned state or the registry.
These are public syntax checks, not trusted execution admission.

To intentionally refresh the lock, use `uv pip compile requirements-dev.in --python-version 3.13 --universal --generate-hashes --output-file requirements-dev.lock` in an authorized dependency-resolution environment, review the diff and rerun checks. Do not silently update legacy pins merely to make tests pass.

The workflow in `.github/workflows/validate.yml` is unprivileged PR validation source: read-only content token, no persisted checkout credentials, no secrets/OIDC, no shared package cache, pinned action commits and a timeout. It does not run protected rebuild, data access or promotion. Its source tests do not prove that GitHub rulesets, reviewer requirements or host permissions are configured. See [CI activation](operations/ci-activation.md).

The architecture checker inventories Python source in the checkout and classifies the legacy entry points, declared `src/` packages, tests and tooling. It rejects unclassified sources and symlinks in the scanned tree. Discovery skips hidden directories, Python caches, packaging metadata and the root `build`, `data`, `dist` and `venv` directories. Application domains may not import tooling or those root artifact locations. Add new application packages to the explicit domain map.

The checker parses each source once and reports a shortest forbidden import chain with its first import location. It resolves ordinary absolute and relative imports against the root and `src/` layout, including package initializers. Recognized dynamic loaders require one literal absolute module name. The checker rejects indirect use of those loader references and wildcard imports from local packages or loader modules. Custom import hooks, arbitrary reflection, notebooks and runtime isolation are outside the analysis.

Task record reads and saves share a 1 MiB limit on the stored UTF-8 JSON, including indentation and the final newline. A save that exceeds the limit fails before creating output. Store large execution logs separately and reference them from the task record.

Current implementation/evidence: [M1 verification](reports/m1-verification.md). Data
limitations: [M0 audit](reports/m0-alignment.md), including the user-provided historical
snapshot addendum. The full system is not production-ready. `train` and `predict-batch`
wire contracts exist; their new operational implementations, production DVC storage,
MLflow, trusted runner, native model adapters, protected verification and deployment
remain subsequent work. Local synthetic DVC restoration is covered below.

Use the audit index's [current checkpoint and recovery](reports/README.md#current-checkpoint-and-recovery)
for today's Git state and uncommitted work. Earlier task plans and CI counts are historical
evidence. [A10](reports/a10-xgboost-preprocessing.md#incomplete-artifact-prerequisites)
and [A14](reports/a14-evaluation-handoff.md#incomplete-benchmark-prerequisites) remain
incomplete; documentation does not close their artifact/evaluation gaps.

M2's first increment adds self-contained synthetic evaluation-contract tests, shipped
in the source distribution and exercised against the wheel. Run
`.venv/bin/python -m pytest -q tests/foundations/test_evaluation_contracts.py` for the
focused checks, then the relevant aggregate checks above after edits. The
[development evaluation proposal](architecture/evaluation-contracts-v1.md) requires
semantic helpers in addition to low-level schema validation. Tests cover declared
eligibility, time/property overlap and fixed populations; they do not validate real
features, target-aggregate lineage, dataset release/restoration or isolation.
Policy review and authorized evidence precede any real-data application.

M2's second increment adds the independent `rent_data` metadata-candidate API and
three local schemas. Focused synthetic checks:
`.venv/bin/python -m pytest -q tests/foundations/test_observation_candidates.py tests/foundations/test_evaluation_contracts.py tests/foundations/test_architecture.py`.
The shipped suite exercises candidate rebuilding, source-byte identity, full record
lineage/projection, safe aggregate counts and unchanged split semantics from both
source and wheel imports. See [observation candidates](architecture/observation-candidates-v1.md).
No raw CSV reader, acquisition, data publication or training is performed. Existing
1 MiB bounds fail without truncation; real release transport/restoration is deferred.

## Separate local data tools

M2 increment 3 implements [development release contracts and local restoration](architecture/dataset-releases-v1.md).
The optional foundations `data` extra declares **PyYAML 6.0.3**, already present in
the existing development lock. A standalone foundations consumer can install
`.[data]`/the wheel's `data` extra for the metadata parser. Pure JSON release/IO
helpers need no DVC installation. Preserve `requirements.txt` and
`requirements-dev.lock`; DVC is deliberately absent from both.

`requirements-data-tools.in` pins DVC **3.67.1** and its source-build backend;
`requirements-data-tools.lock` pins/hashes the separate complete dependency closure
for Python 3.13. ANTLR 4.9.3 has a source distribution, so first install the exact
setuptools backend from `requirements-data-build.lock`, then disable pip build
isolation to avoid implicitly resolving unpinned build dependencies. Both lock
contents contribute to `data_tool_profile_digest`. These development tool locks
identify dependency inputs, not a certified image/native runtime.

Explicit setup (public package downloads; subsequent tests need no network):

```bash
.venv/bin/python -m venv .venv-data-tools
.venv-data-tools/bin/python -I -m pip --isolated --disable-pip-version-check install --no-cache-dir --index-url https://pypi.org/simple --require-hashes -r requirements-data-build.lock
.venv-data-tools/bin/python -I -m pip --isolated --disable-pip-version-check install --no-cache-dir --index-url https://pypi.org/simple --no-build-isolation --require-hashes -r requirements-data-tools.lock
.venv-data-tools/bin/python -m pip check
.venv-data-tools/bin/dvc --version
.venv/bin/python -m pytest -q -ra tests/foundations/test_dataset_releases.py tests/foundations/test_release_io.py tests/foundations/test_dvc_local.py tests/integration/test_dvc_restoration.py
```

Use an absolute `RENT_DATA_DVC` executable path when the tool environment is
elsewhere. Checkout integration defaults to `.venv-data-tools/bin/dvc`; missing or
wrong-version DVC fails with setup guidance rather than skipping or installing it.
Git must also be installed. CI creates the environment under `RUNNER_TEMP`, supplies
`RENT_DATA_DVC` at **step scope**, and preserves the read-only, credential-free PR
workflow. It uses the same backend bootstrap and no-build-isolation installation.

`tests/integration/test_dvc_restoration.py` performs actual Git commits **only in
owned disposable synthetic repositories**, DVC add/push/pull through local filesystem
stores, A-after-B recovery and missing/corrupted-object checks with fresh consumer
caches. No `.dvc` project or remote is created in this checkout, no cloud/credentials
are used and no private/raw input is read. The shipped source/wheel suite includes
the deterministic release/IO/parser/failure tests; actual DVC integration remains a
checkout check with explicit prerequisites. A valid local completion report is not
protected independent verification, publication approval, isolation or leakage proof.

To intentionally refresh tooling in an authorized environment, resolve only
`requirements-data-tools.in` with `uv --no-config pip compile --python-version 3.13
--universal --generate-hashes --default-index https://pypi.org/simple --output-file
requirements-data-tools.lock requirements-data-tools.in` (resolution here used uv
0.13.1). Review the dependency/build-backend and supported metadata profile together,
update both applicable locks, and rerun all relevant checks including real integration.
Do not change ML pins to accommodate DVC.
