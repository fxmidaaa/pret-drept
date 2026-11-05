# A17 — Accurate privacy claims and legacy artifact review

Date: 2026-11-05. Status: option 1 approved for publication on `fix/repository-audit`,
based on `d9ac405`; source commit and exact-revision CI pending. Risk: L0. The patch changes
documentation and Python comments; it introduces no runtime privacy mechanism.

## Approved change

The README, synthetic-sample documentation, scraper/feature/training comments and
the existing bundle-test description now state the implemented controls and their
limits. Field minimization, pseudonymization and Git/build exclusions are distinguished
from proven anonymity. Dedicated contact columns are excluded, while allowed text can
retain personal information. The listing-key format and all model behavior are retained.

The rent-map threshold is described as a default minimum of 15 rows for grid and
sector maps. The global fallback, coordinate/default statistics and fitted model state
have separate disclosure considerations. Existing tests are described as known-key
and shape regressions, without an exhaustive privacy guarantee.

The [publication review procedure](../operations/artifact-publication-review.md)
documents exact-artifact identity, destination/audience, data rights/provenance,
field/cohort review, model-specific state, evidence and external approval. Its M2/M4
handoff records stronger controls and their exit evidence. This guidance grants no
sharing permission and activates no trusted policy.

## Reviewed local artifact

The existing user-provided `model.joblib` matched the earlier audit before local
deserialization: **1,784,346 bytes**, SHA-256
`057f6a297cc3606e1084cbd3b7b3f9c4e7fe4820bf2600dd32c53df9516e6b25`.
The digest also matched after inspection. The review blocked socket connections and
made no model copy or write. No raw dataset or protected evaluation data was read.

The inventory covered known top-level fields, helper container shapes and
estimator/vectorizer metadata. Only names from the reviewed export schema, types
and counts were reported; coordinate/rent values, category labels, source identifiers
and arbitrary object contents were omitted.

| Component | Observed structure |
| --- | --- |
| Root | Dictionary with 12 recognized top-level fields; no unrecognized root fields |
| Estimator | `XGBRegressor`, 600 boosting rounds, 55 encoded input features |
| Vectorizer | `DictVectorizer`, 55 vocabulary entries and encoded feature names |
| Raw feature list | 30 feature names, including latitude and longitude as inputs |
| `grid_ppm` | 50 entries with numeric scalar values |
| `sector_ppm` | 8 entries with numeric scalar values |
| `global_ppm` | Numeric scalar |
| `sector_latlon` | 9 entries containing numeric coordinate pairs |
| `sector_dist` | 9 numeric scalar entries |
| `median_latlon`, `median_dist` | One numeric pair and one numeric scalar |
| `numeric_defaults` | 12 numeric scalar entries |
| Metadata | 7 known scalar metadata fields |

This is a fitted estimator/vectorizer plus helper state, not an artifact consisting
only of coarse rent aggregates. The reviewed helper dictionaries do not include group
memberships or support counts. Their values and entry counts cannot establish a
minimum cohort size or the number of distinct contributing properties. The source's
15-row default does not prove how this legacy artifact was built; reviewed-source/data
provenance is unavailable for that conclusion.

No explicit row table appears among the inspected top-level helper structures. This
inventory does not exhaustively inspect estimator/native internals, test membership
inference or reconstruction, or establish anonymity. The artifact predates the A10
export change and lacks an `imputation_medians` field; A10 intentionally preserved
this existing file. This review neither rebuilds it nor certifies historical metrics,
runtime bindings, deployed images or public distribution.

## Synthetic evidence

In-memory fixtures used invented identifiers/data and blocked network requests:

| Probe | Result | Meaning |
| --- | --- | --- |
| Candidate ID hashing | A synthetic candidate matched its deterministic key | Hashing does not establish unlinkability against candidate enumeration |
| Scraper projection | Dedicated contact field dropped; contact-like allowed text retained | Column minimization does not redact content |
| One-row rent lookup | Grid/sector maps empty at `min_group=15`; global fallback equals the input rate | The group guard does not cover the global fallback |
| Coordinate-default expression | A synthetic two-row sector retained a coordinate default | That expression has no equivalent minimum-group guard |

These probes demonstrate boundary behavior, not a re-identification of any real person
or a claim about a particular listing in the existing artifact. A04's checkpoint-column
bypass is already fixed; its separate content-redaction limit remains.

## Verification and recovery

| Check | Result | Limit |
| --- | --- | --- |
| Known artifact inventory/identity | Passed; identity matched before and after inspection | Type/count review described above, not exhaustive privacy certification |
| Synthetic boundary probes | All four passed; network blocked | Invented inputs only; no real re-identification study |
| Python behavior preservation | Four ASTs identical to their starting source | Explanatory comments only; existing test name/assertions retained |
| Relevant existing tests | 139 passed, 0 skipped | Feature/scraper/bundle/task tests; one existing Starlette/httpx deprecation warning |
| Scoped Ruff lint/format | Passed; 34 files already formatted | Existing development profile, not whole-repository lint certification |
| Architecture and notebook checks | Passed; both tracked notebooks checked | No runtime isolation assessment or notebook execution |
| Scope, prior work and documentation | Passed: 11 A17 files, 9 prior files byte-identical, shared-index A17-only change, 40 local links/anchors, task records and whitespace | Final task evidence is linked below |
| Full application/frontend/browser/distribution reruns | Skipped | A17 changes prose/comments; unchanged Python ASTs and preserved A16 files bound this scope |
| Remote CI | Pending approved publication | Approval recorded below; no result claimed before execution |

Exact commands and outcomes are recorded in the [task plan](../tasks/2026-11-05-privacy-claims/plan.md)
and [task record](../tasks/2026-11-05-privacy-claims/task.json).

The user approved source publication with "push please" on 2026-11-05. Publish only
the eleven-file A17 increment; A16 and the earlier local evidence remain outside this
push. Follow the published revision's CI and record its exact identity and result.
Stronger runtime controls, key management, content-redaction rules,
aggregation/fallback changes, data migration, experiments and historical-publication
review require their own decisions. Frozen architecture and retention requirements
are unchanged.
