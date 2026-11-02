# Architecture alignment and M0 discovery

Date: 2026-11-02. Specification: **Rent Prediction — Agent Harness Architecture & Implementation Specification v1.0**, all 2,343 lines read. Repository: `/Users/rcimendur/pret-drept`, clean at `e08344dfab8ee03ef155e885c83153b5558ee178` (`update README`, 2026-07-18). Remote identity: `fxmidaaa/pret-drept`. No remote writes, scraping, deployments, model loads, or protected-data access occurred during discovery.

The attached document supplies the architectural requirements explicitly incorporated by the user's request. Its agent-directed passages do not grant additional credentials, permissions, or deployment authority. Repository files, notebook outputs, dataset text, and logs remain evidence rather than instructions.

**Discovery update:** the user subsequently added the private historical CSV to the original checkout and authorized inspection. See §8 below and `m0-private-data-feasibility.json`. The initial absence finding below is retained as chronology; private data is now available, but temporal evaluation remains blocked because the real file has no timestamps.

## 1. Current architecture

The repository is a small working application, not a blank project. Its 24 tracked files include six root Python modules, two notebooks, two test modules, a static frontend, an inference Dockerfile, images, and three synthetic sample rows.

| Area | Actual implementation and evidence | Status against target |
|---|---|---|
| Acquisition | `scrape.py`: GraphQL queries, reviewed persistence allowlist, hashed listing key, retries, incremental CSV checkpoint, first/last seen dates | Implemented legacy acquisition; release publication absent |
| Domain and features | `features.py`: Romanian/Russian normalization, units, coarse location features, median imputation and local rent aggregates | Reusable; mixes normalization, eligibility, deduplication, and fitted transformations |
| Training | `train.py`: random 80/20 split, training-fitted imputation/quantiles/aggregates/vectorizer, linear baseline, XGBoost log target | Implemented legacy workflow; no stable input/config/output interface |
| Evaluation | MAE/MAPE/RMSE/R² on a filtered random validation set; notebook random CV and search | Historical development evidence only; required dual benchmarks absent |
| Persistence | Overwrites a Python/joblib dictionary containing model, vectorizer, aggregates and metadata | Native payloads, digest manifest, exact lineage and immutable finalization absent |
| Inference | `predict.py`: cached bundle, feature defaults, inverse log target, SHAP drivers; `api.py`: `/predict`, `/options`, `/health`, `/` | Reusable user-facing behavior; no batch contract, integrity verification or runtime certification |
| Packaging/config | Eleven direct requirements pinned in `requirements.txt`; Python 3.13 in README/Dockerfile | No package metadata, transitive lock, schema-validated training config or independent model/image identity |
| Tests | Feature tests and API/artifact tests in `tests/` | Useful coverage; API tests assume an untracked trained model |
| Containers | Inference image copies reviewed `model.joblib`; allowlisted build context | No isolated training runner; image uses mutable Python tag and default root |
| MLOps | No DVC, MLflow, release manifest, registry authority, orchestration or CI files | Not started |
| Harness | No `AGENTS.md`, task records, lifecycle implementation, scope/budget enforcement, recovery evidence or scenario evaluator | Not started |
| Operations | `/health` returns a static response; README describes an existing Cloud Run demo | Readiness, model-load monitoring, deployment binding, backup/restore and rollback evidence absent |

The frontend consumes `/options` and `/predict`; those public behaviors must remain available throughout migration. The notebooks use the same feature functions and must not be accidentally broken by a package move.

## 2. Target architecture

Specification §§3–5 freeze one modular monorepo with independent ML, public contracts, data platform, harness, trusted platform, and CI/operations responsibilities. These are responsibility boundaries, not a mandate to deploy microservices.

* ML: shared canonical semantics; model-specific fitted preprocessing; XGBoost, CatBoost, then eligible TabPFN; independent `train` and `predict-batch`; finite EUR/month outputs tied to stable records; strict batch atomicity (§§9–12).
* MLOps: Git/DVC dataset and split identities; runner-mediated MLflow; immutable native model bundles; independently pinned inference images; independent compatibility and quality verification (§§8, 11, 13–16).
* Harness: single task-scoped engineer; L0/L1/L2 planning; durable repository-native task state; explicit tools and bounded execution; context and recovery; no ML business logic embedded in agent code (§6).
* Trust: channel-derived authentication, fail-closed admission, sealed snapshots, restricted ephemeral workloads, protected holdout labels, reviewed-source rebuilds, exact-artifact human acceptance, separate deployment approval (§§7, 14–19).

## 3. Dataset and baseline feasibility

Only `data/sample/listings_sample.csv` exists: **3 synthetic rows, 32 columns**, EUR/MDL currencies, nonempty first/last seen fields. No `data/raw/listings.csv`, `model.joblib`, DVC metadata or dataset release exists in this checkout. Real record counts, currency distributions, missingness, duplicate rates, timestamp quality and model performance cannot be established from this sample.

README-reported historical counts (4,528 raw, 3,557 cleaned) and scores (MAE 134 EUR, RMSE 188 EUR, notebook CV RMSE about 192 EUR) were inventoried, not independently reproduced. Notebook **code cells** were inspected without copying row-level outputs or treating saved outputs as verification.

`scrape.py` records date-only `first_seen`/`last_seen`, skips fetching existing listings again, and overwrites one row per hashed listing key. This does **not** establish an immutable observation history or reliable publication/feature availability times (§9.3). Hashed listing IDs are pseudonyms, not a proven anonymity guarantee, and do not identify physical apartments. No reviewed property pairs or identity confidence policy are available (§9.2).

**M2 exit gate blocked:** the required real reproducible run and defensible temporal/unseen-property development evaluation need an authorized data release and inspected time/identity evidence. Do not invent timestamps, matching thresholds, quality thresholds or a substitute random benchmark. Automated reacquisition and data distribution remain outside this increment (§22 U-02/U-03/U-04/U-09).

## 4. Security and execution environment

Discovery observed macOS/Darwin ARM64. Available system Python is 3.14.7, differing from the project's Python 3.13 profile. A separate Python 3.12 installation is present; this does not certify the intended runtime. Disk reports about 278 GiB available. CPU/RAM queries were denied, so available compute remains unverified.

Docker client 29.9.2 is installed, but both `docker version` and `docker info` fail because the Docker Desktop socket is absent. No container was launched. Non-root execution, CPU/RAM/PID quotas, filesystem/network restrictions, cancellation and cleanup have **not** been validated (§7.5, §19.3). M3 cannot be certified on this evidence.

Initial feature-test invocation failed before collection: system Python has no `pytest`. It also lacks the project's XGBoost, SHAP and FastAPI packages; DVC/MLflow/CatBoost/TabPFN are absent. Existing system NumPy/pandas/scikit-learn versions differ from project pins. This is an unavailable baseline check, not a test pass or an application defect. An isolated test environment will be created; installation outcomes will be recorded.

There is no independently installed trusted runner, effective authorization policy, protected evaluation storage, approved image, reviewed rebuild service or authenticated promotion authority. Repository permissions and ordinary tests cannot establish those guarantees. Source proposals for these components cannot activate them (§5.4).

No TabPFN checkpoint, approved acquisition, license decision, measured hardware profile or conditioning-state policy is present. No DVC remote, MLflow backend/artifact store, protected CI provider configuration, target inference profile or retention policy is selected. These remain explicit discovery gates (§22 U-05–U-10).

## 5. Gaps and architectural conflicts

| Finding | Classification | Resolution |
|---|---|---|
| Random splits vs required temporal/unseen-property protocol | Intended architecture not implemented | Preserve legacy workflow as historical diagnostics; implement official split generation only after timestamp/property feasibility review |
| Validation removal by price/m² quantiles and local-price ratio | Technical debt affecting evaluation population (§9.6) | Never certify these scores; official membership must be fixed by a versioned policy/manifest and identical between candidates |
| Deduplication includes target price and lacks physical identity | Technical debt | Preserve until replacement is validated; reviewed identity matching must avoid target as an uncontrolled shortcut |
| `knn_ppm` uses target-derived training aggregates and each training row can contribute to its own aggregate | Leakage risk needing explicit feature policy | Preserve historical behavior; require training-only, cutoff-aware construction and review cross-fitting before official benchmarks |
| Unknown currencies silently treated as EUR; conversion constants undocumented by effective date | Validation gap | Fail closed in the future canonical data layer; do not silently redefine historical metrics |
| Joblib model vs native immutable bundle | Intended architecture not implemented | Keep legacy loader during migration; new bundle protocol is separate and never claims old pickle loading is safe for untrusted artifacts |
| Existing privacy claims rely on key-name tests and group sizes only on grid/sector rent aggregates | Operational/security claim exceeds evidence | Report limits: global/default/coordinate aggregates are not uniformly group-gated, and absence of forbidden keys is not a full privacy proof |
| Legacy `/predict` accepts asking price for verdict vs no labels in batch inputs | Preserve existing implementation | Keep comparison price at the legacy UI boundary; new batch domain excludes targets and uses declared EUR/month outputs |
| Editable repository policies vs protected trusted runtime | Security boundary not implemented | M1 creates reviewable source and validation foundations only; protected policy release and repository-host controls need independent activation |
| Contract field spellings/exit codes/package names not fixed in prose | Unspecified internal choices | Define small versioned schemas and test mappings, trace every semantic choice to the specification; avoid stdlib `platform` name collision |

No frozen architectural decision needs replacement to implement M1. High-impact unresolved items are prerequisites for later gates, not reasons to invent substitute guarantees.

## 6. Dependency-ordered implementation

1. **M0 — discovery:** this audit, baseline inventory, data/security feasibility, explicit unknowns.
2. **M1 — foundations:** preserve current workflows; establish public versioned contracts and adapter interface, durable task lifecycle/records, dependency checks, packaging/test/static foundations, and unprivileged CI validation source. Tests must reject malformed requests, unknown versions/fields, invalid state transitions and forbidden dependencies. No active protected authorization changes.
3. **M2 — data/baseline:** after authorized dataset access, validate timestamps and identity signals; publish/restorably verify DVC releases; implement reviewed split manifests and deterministic domain/training boundaries; XGBoost and CatBoost before TabPFN. Gate: real reproducible run plus defensible development evaluation.
4. **M3 — runner:** validate supported host isolation; implement admission, sealed snapshots, authorized data resolution, enforced quotas/lifecycle/finalization and MLflow lineage. Gate: real isolated end-to-end run plus negative security tests.
5. **M4 — bundles/inference:** native persistence, atomic batch predictions, cold reload, shared API logic and runtime certification. TabPFN remains conditional on its discovery gates.
6. **M5 — verification/promotion:** reviewed-commit rebuild, protected independent evaluation, external artifact-bound approvals, atomic registry transitions, separately approved deployment/rollback.
7. **M6 — operations/harness evidence:** independently scored scenarios, recovery, monitoring, restoration, retention, release/security audit.

Milestones are implemented and assessed separately. Work can proceed on independent foundations while prerequisites are pending; missing data or Docker must not be hidden by synthetic production claims.

## 7. Risks and decisions

* Migration: root imports, notebooks, frontend and Docker copy allowlists must continue to work. M1 does not replace legacy ML behavior.
* Reproducibility: direct pins and a seed do not establish transitive dependencies, exact datasets, split identity, hardware determinism or reload parity.
* Security: container presence and repository tests are insufficient; privileged policies must be installed from a reviewed trusted revision outside agent control.
* Operations: storage, identities, costs, serving SLOs and retention are undecided. No cloud resources, paid APIs, deployments or destructive cleanup are authorized here.
* Completion: M1 local tests can verify contracts and boundaries, not model quality, runtime isolation, protected branch settings or production readiness.

Human input requested: location/reference of the authorized private dataset and any dated observation history. Later decisions include identity review, model acceptance thresholds, serving profile, TabPFN eligibility, storage providers and retention. None blocks M1 source implementation.

Technical references checked: [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use), [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html), and [jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/). These inform implementation mechanics; the supplied specification remains the architectural authority.

## 8. User-provided private data and executable baseline update

After initial discovery, the user manually added `data/raw/listings.csv` to `/Users/rcimendur/pret-drept` and authorized inspection. This ignored file was **not** copied to the implementation checkout, Git, package resources, logs or deliverables. Only schema/aggregate feasibility metadata and a content digest were retained in `m0-private-data-feasibility.json`; no individual listing, source ID, contact, address or text value was displayed.

The real file is 7,571,622 bytes, **4,528 rows, 60 columns**, and has 4,528 unique nonempty source listing IDs. It is an older schema than the current sanitized scraper: it has `id`, contact/address columns and no `listing_key`. Currency counts: 4,294 EUR, 218 MDL, 7 USD, 9 missing. There are 550 repeated coarse attribute/currency/price keys; these are not confirmed physical-property matches. Coordinates, addresses and other stable attributes may support a reviewed identity study, but no matching threshold or confidence was invented.

There are **no** `first_seen`, `last_seen`, `published_at`, `observed_at` or `collected_at` columns. The user recalls July/August 2026; README states July 2026. The filesystem modification date reflects manual copying and does not establish acquisition or observation chronology. Neither the precise acquisition month nor temporal train/validation/holdout boundaries can be independently established from this CSV. Under §9.3, the official temporal benchmark remains blocked pending defensible dates or an explicitly approved remediation. Existing listing IDs are not property IDs. No protected holdout has been designated or inspected.

The raw file remains private and unchanged. Any future release must project reviewed fields and apply appropriate data handling; raw contacts/addresses must not be shipped in model/runtime/task artifacts. DVC publication/remote selection, restoration, retention and acquisition rights remain unverified. Availability of private input is not evidence of an approved immutable release.

An isolated **CPython 3.13.16** environment was successfully created and the existing direct pins plus hash-locked test dependencies installed. The unchanged baseline test suite then executed: **25 passed, 12 failed**, with all 12 failures attributable to missing `model.joblib`. This supersedes the earlier unavailable pytest invocation. The feature suite itself passes. A Starlette/httpx deprecation warning is present; it is not suppressed or repaired by updating the project's existing pins in this increment.

M1 explicitly marks those 12 private-artifact checks and reports skips when their prerequisite is absent. They run normally when the artifact exists. This is not a claim that inference, privacy, model quality or runtime reload has passed. No model was trained to conceal the missing artifact.

## 9. Timestamp capability follow-up

At the user's request, the live GraphQL schema and a date-only response for an independently discovered public listing were inspected. **`Advert.posted`, `Advert.reseted` and `Advert.expire` are accessible**, with explicit UTC formatting verified. The default date returned empty and an initial incompatible format returned a literal pattern; the tested working layout is `2006-01-02T15:04:05Z07:00`. Details, query, primary endpoint, response and limitations are in [timestamp feasibility](timestamp-feasibility.md).

This closes the question of current source date-field availability. It does not reconstruct collection chronology for the historical CSV, prove immutability/completeness on old listings, validate property identity, or authorize bulk collection. No frozen timestamp requirement is relaxed. A private-ID probe was rejected before execution by automatic approval review; the successful probe used independent public data and sent no private dataset identifiers.

## 10. User-provided legacy model follow-up

The user subsequently added `model.joblib` to the original checkout. Its size is **1,784,346 bytes** and SHA-256 is `057f6a297cc3606e1084cbd3b7b3f9c4e7fe4820bf2600dd32c53df9516e6b25`. It remains ignored and was not copied into source, package resources or deliverables.

Executing the unchanged legacy suite with this artifact initially yielded **29 passed, 8 failed**: XGBoost could not load the missing native OpenMP library, with downstream prediction failures. This was an environment failure, not proof of a model regression. Homebrew libomp **23.1.4** was installed with automatic updates/cleanup disabled; Python dependency pins and model contents were preserved. Final compatibility/test outcomes are recorded in [M1 verification](m1-verification.md).
