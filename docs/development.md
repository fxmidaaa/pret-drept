# Development and verification

Use Python 3.13. The M1 evidence uses CPython 3.13.16 on macOS ARM64. The original application's direct pins remain in `requirements.txt`; `requirements-dev.lock` pins their transitive closure plus test/build tools with hashes, resolved universally for Python 3.13 with platform markers for Mac/Linux/Windows. Local installation is verified; each published revision also needs a successful Linux CI run. This is a development/test environment lock, not a certified inference image.

On macOS, the existing XGBoost wheel also needs the native OpenMP library (`brew install libomp`). Discovery reached the real model and demonstrated a missing `libomp.dylib`; libomp **23.1.4** was installed to resolve this environment prerequisite without changing ML code or Python pins. Python package hashes do not cover native libraries. A future certified inference image must preserve and verify its complete runtime. See [XGBoost installation guidance](https://xgboost.readthedocs.io/en/stable/install.html).

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python scripts/install_actionlint.py --directory .venv/bin
.venv/bin/actionlint -shellcheck= -pyflakes=
.venv/bin/python scripts/check_notebooks.py
.venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/rent-check-architecture --root .
.venv/bin/python -m pytest -q -ra
.venv/bin/python scripts/check_distribution.py
```

`MANIFEST.in` declares the foundations source distribution, including the schema resources and
the self-contained contract, prediction and bundle, task lifecycle, and architecture tests. Keep
tests that require the application, workflow files, or project task records in checkout CI.
`scripts/check_distribution.py` builds the wheel from the source archive and runs the shipped
suite twice from a temporary extraction. The source run imports from the extracted `src/` tree.
The wheel run imports from the wheel and exercises all seven packaged schemas. Both runs bypass
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

To intentionally refresh the lock, use `uv pip compile requirements-dev.in --python-version 3.13 --universal --generate-hashes --output-file requirements-dev.lock` in an authorized dependency-resolution environment, review the diff and rerun checks. Do not silently update legacy pins merely to make tests pass.

The workflow in `.github/workflows/validate.yml` is unprivileged PR validation source: read-only content token, no persisted checkout credentials, no secrets/OIDC, no shared package cache, pinned action commits and a timeout. It does not run protected rebuild, data access or promotion. Its source tests do not prove that GitHub rulesets, reviewer requirements or host permissions are configured. See [CI activation](operations/ci-activation.md).

The architecture checker inventories Python source in the checkout and classifies the legacy entry points, declared `src/` packages, tests and tooling. It rejects unclassified sources and symlinks in the scanned tree. Discovery skips hidden directories, Python caches, packaging metadata and the root `build`, `data`, `dist` and `venv` directories. Application domains may not import tooling or those root artifact locations. Add new application packages to the explicit domain map.

The checker parses each source once and reports a shortest forbidden import chain with its first import location. It resolves ordinary absolute and relative imports against the root and `src/` layout, including package initializers. Recognized dynamic loaders require one literal absolute module name. The checker rejects indirect use of those loader references and wildcard imports from local packages or loader modules. Custom import hooks, arbitrary reflection, notebooks and runtime isolation are outside the analysis.

Task record reads and saves share a 1 MiB limit on the stored UTF-8 JSON, including indentation and the final newline. A save that exceeds the limit fails before creating output. Store large execution logs separately and reference them from the task record.

Current implementation/evidence: [M1 verification](reports/m1-verification.md). Data limitations: [M0 audit](reports/m0-alignment.md), including the user-provided historical snapshot addendum. The full system is not production-ready. `train` and `predict-batch` wire contracts exist; their new operational implementations, DVC/MLflow, trusted runner, native model adapters, protected verification and deployment remain subsequent milestones.
