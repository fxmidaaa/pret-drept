# M1 source implementation and verification

Date: 2026-11-02. Baseline: `e08344dfab8ee03ef155e885c83153b5558ee178`. Scope: specification **M1**, plus M0 follow-up inspection explicitly requested by the user. No architecture decision was weakened. This is an incremental source proposal; the full architecture and protected runtime are not complete.

## Implemented

| Files/modules | Behavior and contract | Specification |
|---|---|---|
| `src/rent_contracts/schemas/v1/*.json` | Seven explicit contracts: apartment, experiment request, resolved training request, batch request/result, bundle manifest, task record | §§6.4, 7.2, 10–12 |
| `rent_contracts.validation` / `requests` | Strict UTF-8/JSON/schema checks; unknown fields/versions, duplicate keys, nonfinite values, oversized/deep documents rejected; local-only schema resources; adapter config checked through an explicit registration map; immutable parsed payload | §§7.2–7.3, 10.3, 12.2 |
| `rent_contracts.predictions` | Whole-population validity, stable identities, one finite EUR/month result per input, exact bundle correspondence; no tolerated omissions or target labels | §§10.1, 12.5–12.8 |
| `rent_contracts.bundles` | Noncircular canonical manifest identity, safe/unique payload paths, declared preprocessing path/digest consistency | §§11.2–11.4 |
| `rent_contracts.errors` | Every minimum application category mapped to a unique documented nonzero code; future CLI integration explicitly deferred | §12.9 |
| `rent_prediction.adapters` | Provider-independent model adapter protocol, with model-specific representations and fitted state | §10.3 |
| `rent_agent.tasks` | L0/L1/L2 planning requirements, canonical lifecycle/history, verification completeness, reload and atomic context persistence; failed replacement preserves prior state | §§6.2–6.8 |
| `rent_checks.architecture` | Actual legacy/new source dependency checks without importing inspected code; negative fixtures cover forbidden/aliased/dynamic/escaping imports and source symlinks | §§4.3, 16.5 |
| `pyproject.toml`, `requirements-dev.in/.lock` | Installable foundations, packaged schemas, Python 3.13 test/build configuration, universal transitive hash lock preserving all existing direct pins | M1, §15.1 |
| `.github/workflows/validate.yml` | Unprivileged PR validation source; read-only content token, no secrets/OIDC, no persisted checkout credentials, immutable actions, bounded job | §15.1 Level 1 |
| `AGENTS.md`, architecture/development/operations docs, task plan/request/JSON record | Navigation, protected invariants, recovery context, exact authorization record, source/effective-policy distinction and activation prerequisites | §§5.4, 6, 15 |
| `tests/test_api.py`, `tests/conftest.py` | Twelve artifact-dependent checks explicitly marked; absent prerequisites produce transparent development skips, real artifacts run the unchanged assertions | §§6.8, 16 |

New `train` and `predict-batch` **contracts** exist; operational command handlers and concrete model adapters are not claimed. Manifest validation does not read/load/certify model bytes. Task state is editable context, never permission. Static checks do not prove runtime isolation. The initial wheel distributes foundations; legacy application scripts/frontend remain in the checkout.

## Compatibility and tests executed

The user supplied the real historical CSV and legacy model during the session. Both remain in the original checkout, ignored and unchanged; neither was copied into the implementation checkout or package outputs. Their presence updates the initial M0 absence findings.

Executed evidence before applying source to the original checkout:

* **100 new foundation tests passed** in the implementation checkout: real validation, state transitions, failure/recovery and negative dependency fixtures. No LLM, scraping, model training or fake integration success was used.
* **37 original tests passed with the supplied real model** against the unchanged original application after resolving its native runtime prerequisite. This includes existing feature, API, prediction and aggregate-key privacy assertions. These are useful legacy checks, not a new privacy proof or independent model-quality evaluation.
* Ruff static checks passed and all 19 new Python files passed format verification. Existing ML source style/behavior was preserved.
* Architecture CLI passed on the actual implementation tree; forbidden dependency fixtures were detected without executing them.
* Hash-locked dependencies installed in CPython 3.13.16; the universal lock was rechecked offline on macOS ARM64. Linux CI execution remains unverified.
* Source distribution and wheel built successfully. Fresh isolated wheel import loaded and checked all **7** schema resources; archive inspection found no raw CSV or trained model payload. This was a foundation package check, not model cold-reload/runtime certification.
* Whitespace/diff checks passed outside the byte-for-byte supplied specification, whose original intentional Markdown hard breaks are preserved.

The earlier baseline failures are preserved, not hidden: initially pytest was unavailable; after setup, 25 legacy checks passed and 12 failed for missing `model.joblib`; after the user supplied it, 29 passed and 8 failed due to missing `libomp.dylib` and downstream effects. Installing Homebrew **libomp 23.1.4** resolved the native library requirement; all 37 then passed. No ML code or Python pins were changed to manufacture compatibility. A Starlette/httpx deprecation warning remains.

## Final original-checkout verification

Applied the bounded source patch to `/Users/rcimendur/pret-drept` after verifying its unchanged audited HEAD and patch applicability. No commit, push or remote activation was performed.

Executed there in CPython 3.13.16 with the real local `model.joblib`:

* `python -m pytest -p no:cacheprovider -q -ra --tb=short`: **137 passed, 0 failed, 0 skipped**, in 4.79 seconds (100 new foundation cases plus 37 original cases). One existing Starlette/httpx deprecation warning remains.
* `python -m rent_checks.architecture --root .`: passed on original-checkout source.
* Ruff checks and format verification: passed; 19 new Python files formatted.
* Fresh isolated wheel import/resource validation and wheel/sdist private-payload exclusion checks: passed.
* Private CSV and model SHA-256 checks: both unchanged from inspected identities.
* Git comparison of legacy ML/acquisition/inference/frontend/container code and original feature tests to the audited commit: unchanged. Only README navigation, development ignores and artifact test markers change existing tracked files.

The M1 local source exit gate (architecture/basic contract tests) passes. Protected policy review/activation and actual CI execution remain external; task state is READY_FOR_REVIEW, not full architecture completion. Final task-record reload and evidence synchronization are checked after this documentation checkpoint.

## M0 timestamp investigation

Live GraphQL introspection and a date-only public sample confirmed `posted`, `reseted` and `expire`, with explicit UTC formatting required. See [timestamp feasibility](timestamp-feasibility.md). No private CSV IDs were sent: automatic approval review rejected the proposed private-ID query before execution, and the successful test used a listing independently discovered from public search. Historical backfill is unperformed. Date-field accessibility does not certify feature-availability chronology in the July/August snapshot.

## Status, limitations and next milestone

| Area | Status |
|---|---|
| M0 architecture/data/environment audit | Implemented and verified within recorded observations; unknowns retained |
| M1 source contracts, task context, dependency checks, test/package foundations | Implemented and locally verified: 137 combined tests passed in the original checkout |
| Protected CI effectiveness | Partially implemented as source foundations; independent review/release, host rules and actual CI execution pending |
| Real historical data and legacy artifact | Available and inspected/tested; not an approved DVC release or accepted model |
| M2 official data/evaluation/training exit gate | Blocked on defensible historical/ongoing observation chronology and reviewed property identity; DVC release/storage policy also unconfigured |
| M3 trusted experiments/MLflow | Not started; Docker daemon and effective isolation/trusted authority prerequisites remain unverified |
| M4 native model bundles/CLI/API certification | Not started beyond M1 contracts; current joblib remains a legacy artifact |
| M5 protected verification/promotion/deployment | Not started; no protected state changed |
| M6 scenarios/monitoring/backup/restore | Not started |

The next milestone is M2: preserve/version the historical input, establish approved acquisition provenance and timestamp-aware observation retention, evaluate physical-property matching using reviewed pairs, then implement releases/splits and XGBoost/CatBoost training through the public interfaces. Work on source can continue incrementally, but official temporal evaluation cannot be claimed from fabricated dates or from today's metadata paired with unverified historical prices/features. Do not relax §9.3 solely because the old CSV omitted fields the source actually exposes.

Required external actions remain independent review/activation of trusted policy and CI controls, supported container isolation validation, storage/identity/retention decisions and any authorization for private-ID enrichment or new acquisition. No paid API, cloud resource, deployment, model acceptance, bulk scrape, data deletion or protected evaluation was executed. Runner/MLflow/CI execution identifiers: none.

Recovery: read the task record, compare actual Git state to the audited baseline, inspect final verification evidence and private input identities, then resolve the next data milestone's prerequisites. Do not treat this narrative or a green development run as authority to promote a model.
