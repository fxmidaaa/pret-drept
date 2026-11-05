# Public contracts v1.0.0

Authority: supplied specification §§7, 10–12 and §6.4. The prose fixes semantics; the JSON schemas in `src/rent_contracts/schemas/v1/` define the initial wire spelling. Schemas are package resources, so the same validators work from an installed wheel. These are new interfaces alongside the legacy application, not a claim that the future runner or ML CLI is implemented.

## Versions and transport

Version the domain (`apartment`), adapter interface (`RegressionAdapter`), bundle format and prediction protocol independently. Their initial versions happen to be `1.0.0`; validators reject unsupported versions instead of assuming compatibility. A future adapter can register an identifier/configuration schema without changing the experiment protocol. Registration and execution approval are separate.

JSON is UTF-8 without a byte-order mark (BOM). Byte input is decoded explicitly as
UTF-8 before JSON parsing; UTF-16/32 auto-detection is disabled. `load_document` accepts
only text or `bytes`, with the same BOM/Unicode rules for each. Unknown object fields,
duplicate JSON keys, nonfinite numbers, unsupported Python object types, documents over
1 MiB (counted in UTF-8 bytes) and nesting beyond 64 levels are rejected. These parser
limits are implementation choices, not resource authorization. Parquet remains the
intended table transport (§12.2); no pretend CSV/Parquet training implementation is introduced in M1.

`load_document(raw)` performs strict decoding. `validate_document(name, document)`
validates the named public **structural** schema only.
`ExperimentRequest.from_document(..., model_schemas=registered_schemas)` additionally
validates adapter registration and configuration. Direct construction with
`ExperimentRequest(payload, model_schemas=registered_schemas)` performs the same checks
and canonicalizes the JSON before immutable storage. The registry is required and is
not retained in the request. Construction without it fails, including replacement
without the required registry. Callers must independently perform channel authentication,
effective task authorization, immutable-reference resolution, policy bounds and sealing.
Passing schema validation never admits an experiment.

The additive M2 [development evaluation proposal](evaluation-contracts-v1.md) defines
`observation-reference`, `evaluation-policy` and `development-split`, with semantic
helpers for explicit eligibility/exclusions, temporal/property checks and fixed
candidate populations. These development-only contracts require policy review
before real-data use and do not expose restricted final-holdout details or certify
feature leakage, a dataset release or the M2 exit gate.

Schemas are loaded from bundled local resources. External schema lookup is denied; adapter schemas are explicitly supplied by the caller's registry. No configuration can select a Python import path, command, host mount, credentials or runtime security options.

Identifiers such as `record_id` and `task_id` contain 1 to 128 characters. The first
character is an ASCII letter or digit. The rest can also use `_`, `.` and `-`.
SHA-256 digests are `sha256:` followed by exactly 64 lowercase hex digits. A non-null
`reviewed_commit` contains exactly 40 or 64 lowercase hex digits. These checks apply
to the complete string. Identity comparisons use the submitted value as-is.

## Request contracts

| Schema | Initial fields and semantics |
|---|---|
| `experiment-request` | `contract_version`, `task_ref`, `operation=train`, `code_snapshot_ref`, `dataset_ref`, `split_ref`, `model_family`, `configuration`, `random_seed`, `resource_profile`, `idempotency_key` |
| `train-request` | `contract_version`, `model_family`, `configuration`, resolved `training_partition` and nullable `validation_partition`, `dataset_ref`, `split_ref`, `random_seed`, nullable approved `checkpoint_ref`, assigned `output_directory` |
| `predict-batch-request` | `contract_version`, exact `bundle_ref` (resolved path plus digest), `input_path`, `input_schema_version`, `inference_configuration`, assigned `output_path` |

Dataset/split digests identify the release and manifest envelopes. A later DVC release will also retain its own DVC object identity (§8.2). Retrieval must be verified separately. Snapshot references must already be sealed in this initial protocol. A future sealable-reference workflow requires its own validated admission path.

Resource shape is positive integer CPU, MiB and duration, plus nonnegative GPU count. Policy maxima, approved image, authenticated principal, output paths, resource enforcement and retry limits belong to trusted admission; callers cannot grant them through these fields. Initial experiment operation is training; promotion/deployment are never workload operations. The explicit seed is a necessary identity input, not a promise of cross-hardware bitwise determinism.

Model configuration is deliberately not forced into a common set of hyperparameters. It must pass the registered model adapter's schema and semantic checks. Structural `train-request` validation alone is insufficient. `RegressionAdapter` in `src/rent_prediction/adapters.py` defines validation, fitting, prediction, native export/load, requirements and runtime capabilities without importing any harness or privileged platform package. Concrete adapters remain M2/M4 work.

## Prediction contract and atomicity

`apartment` describes canonical apartment inputs, with `record_id` rather than positional identity, square-metre area and the existing application's basic ranges. Source normalization and categorical policy remain explicit future domain/adapter work. The schema includes the legacy user-entered features; it excludes target labels, asking-price comparisons, text, coordinates outside the declared city ranges, caller-computed target aggregates and privileged metadata. Current legacy `/predict` still accepts an asking price for its user-facing verdict; this does not become a batch feature.

Apartment validation also checks relationships between fields. The floor must be at or below the building's total floors, and the kitchen area must fit within the apartment area when supplied. Supply both coordinates or leave both absent or null. The legacy HTTP and direct prediction paths use the same rules. Legacy prediction uses its sector estimate when both coordinates are missing.

`prediction-batch` contains `contract_version`, `bundle_digest`, `target_unit=EUR/month` and nonempty `predictions`, each containing `record_id` and finite `predicted_rent_eur`. `validate_prediction_correspondence` validates the **entire** input and output population and exact requested bundle identity. Order may differ because correspondence is by identity. Missing, substituted or duplicate records fail; no clipping or fallback model is implied. An empty batch fails.

Inference configuration is an empty object in initial v1; no tolerant mode is supported. The later prediction writer must stage output and finalize atomically only after every record and prediction passes. M1 validates population semantics; it does not implement filesystem finalization or invoke a model (§12.7).

## Bundle manifest identity

`bundle-manifest` requires all §11.3 groups: identity, provenance, artifact paths/formats/sizes/digests, preprocessing state, independently versioned domain/adapter contracts, runtime dependency/platform requirements, checkpoint identities and governance restrictions.

Candidate provenance includes a source snapshot and nullable `reviewed_commit`: a development candidate may not have reviewed source. M5 acceptance must require the independently reviewed commit and trusted rebuild; a non-null caller declaration is never proof of review. Verification/certification/approval records remain outside the immutable manifest.

The v1 digest is SHA-256 of UTF-8 JSON with recursively sorted keys, no insignificant whitespace and `ensure_ascii=False`, excluding **only the top-level `bundle_digest`**. This is a locally versioned canonicalization rule, not RFC 8785. Payload identities, source, data, split, configuration and seed remain inside the hashed body. Payload bytes are not read by this helper.

`validate_bundle_manifest` verifies schema, canonical self-digest, unique safe relative POSIX artifact paths and that preprocessing references a declared artifact with the same digest. It does not extract files, check actual bytes, verify symlinks on disk, load native estimators or certify a runtime. Those are M3/M4 responsibilities. Model bundles do not contain an inference image identity; certification later binds the independently pinned image and bundle (§11.5–11.7).

## Task context and errors

`task-record` preserves every §6.4 field and a timestamped state history. `TaskRecord` checks planning for L1/L2, valid transitions, chronological timezone-aware history, required verification completeness, and pending work before completion. Writes use a same-directory temporary file, file flush/fsync and atomic replacement; failed replacements preserve the previous record. This is local single-writer context persistence, not a tamper-proof audit log, a concurrent transaction store or authenticated approval.

Task records remain editable context. Risk assessment must reconcile actual changed modules and requested operations; a record's label or `COMPLETED` state grants no permissions. Reconciliation with Git and independent runner/CI evidence is mandatory on recovery. Bounded retries, effective authorization and scenario scoring remain later harness/platform work.

Process mapping reserved for the future application CLI (§12.9):

| Category | Exit |
|---|---:|
| Success | 0 |
| CONTRACT_ERROR | 2 |
| VALIDATION_ERROR | 3 |
| AUTHORIZATION_ERROR | 4 |
| DATA_NOT_FOUND | 5 |
| ARTIFACT_INTEGRITY_ERROR | 6 |
| MODEL_COMPATIBILITY_ERROR | 7 |
| TRAINING_ERROR | 8 |
| PREDICTION_ERROR | 9 |
| RESOURCE_EXHAUSTED | 10 |
| TIMEOUT | 11 |
| CANCELLED | 12 |
| INFRASTRUCTURE_ERROR | 13 |
| INTERNAL_ERROR | 70 |

`rent-check-architecture` is a development checker, using 0/1 for clean/violating source, rather than an ML operation. The error mapping is defined/tested here; actual ML command integration is not claimed. Validator diagnostics omit caller values/property names and raw schema errors. The runner remains authoritative for OOM, termination and infrastructure classification.
