# Artifact publication review

Status: manual review guidance recorded for A17. This document does not implement a
trusted gate, grant access or sharing permission, or approve an artifact. The
[frozen architecture](../architecture/specification-v1.md) governs acceptance,
deployment, data access and retention. Stronger automated controls remain M2/M4
work with separately approved requirements.

## Current controls and their limits

The legacy scraper limits persisted columns and excludes dedicated contact fields.
Permitted ad text, map coordinates and photo references remain potentially personal
or linkable. Listing keys are deterministic hash pseudonyms; candidate IDs can be
matched by recomputing them. Checkpoint schema validation does not redact content.

Git ignore rules and the Docker build allowlist reduce accidental inclusion. They
do not prove storage access controls, inspect learned model state, or authorize
sharing. The Dockerfile copies the supplied model without reviewing it. Notebook
publication checks reject saved cell state, while source, charts and other artifacts
still need their own review.

Grid and sector rent maps have a default 15-row threshold. Global rent fallbacks,
coordinate defaults and other fitted statistics do not share that guard. Rows are
not necessarily distinct physical properties. Neither this count nor the absence
of known raw-data keys is an anonymity guarantee.

## Review inputs

Before a sharing decision, identify:

- The exact artifact: kind, byte size and digest; for an image, both image identity
  and the identity of each included model/data payload. Inspect the actual payloads,
  not only a manifest or an intended file list.
- Reviewed source and available data/split/transformation provenance. Record missing
  provenance explicitly; a training date or historical score does not replace it.
- The intended destination, audience and access model: for example, public download,
  restricted storage, or a prediction service. Different exposures need separate review.
- Authorized data use and sharing rights, applicable restrictions, the approved
  disclosure-risk criteria and their version, and the required external reviewer.

Do not describe an artifact as approved for a destination while its required inputs
or review criteria are unresolved. An inspection result is evidence for a decision,
not authorization. Do not deserialize untrusted joblib/pickle files merely to inspect
them; use an appropriate controlled review environment and an approved method.

## Review steps

1. Preserve original observations and previously finalized artifacts. Prepare any
   approved transformed export at a distinct destination; retain lineage under
   architecture §§8.3/8.5. Review does not authorize deletion or in-place cleanup.
2. Inventory all payloads and relevant metadata. Include identifiers, text, photo/URL
   references, coordinates, categorical vocabularies, helper statistics, fitted/native
   model state, logs and saved notebook/chart content. Keep reports to safe schemas,
   types, counts and digests; omit private values and arbitrary object dumps.
3. Assess each exported field and cohort against the approved criteria. Check global
   fallbacks, coordinate/default statistics and small or overlapping groups as well
   as grid/sector rent maps. Use defensible group membership/support evidence; scalar
   values alone do not establish how many independent properties contributed.
4. Review model-specific inference state and the intended exposure. Required fitted
   parameters must remain intact for reproducible inference. For TabPFN, conditioning
   state has explicit preservation and unauthorized-data-exposure requirements in
   §10.6. Removing necessary state solely to pass a key-name test is not a valid migration.
5. Run the approved disclosure-risk checks, including authorized adversarial checks
   when required, and verify any derived artifact's inference/format compatibility.
   Record passed, failed, skipped and unavailable checks separately. The existing
   known-key regression, notebook-output check and package exclusions cover specific
   mechanisms; they are not exhaustive privacy tests.
6. Record the outcome and remaining restrictions, then obtain the external decision
   required for that exact artifact and destination. A modified artifact or changed
   destination needs a corresponding review and decision. Keep verification and
   approval records outside immutable model bundles (§11.3).

An approval record should identify the artifact digest, reviewed source/provenance,
destination and audience, criteria version, evidence references and limits, externally
authenticated decision reference, and retained restrictions. Follow the relevant
authorization process; a repository task record or self-authored checklist is not
proof of approval.

Model acceptance still requires reviewed-source rebuild, independent verification
and exact-artifact human approval. Deployment remains separate. A model approval
does not authorize distributing its training dataset, and a local review does not
certify a previously deployed image.

## M2/M4 handoff

These are decisions and implementation prerequisites, not controls activated by A17.

| Work | Required decision and implementation | Exit evidence |
| --- | --- | --- |
| M2 data publication | Define allowed destinations/fields, content handling, identifier policy and release-specific disclosure criteria. Preserve authorized raw observations separately and record transformations. | Reviewed policy/version, permitted-field/content fixtures, immutable release identity and tested restoration. |
| M2 group evidence | Define relevant populations, distinct-property treatment, support/cohort rules and fallback behavior. Do not assume 15 rows is a universal sufficient criterion. | Reviewed memberships/support counts, tests for small/overlapping groups and every exported default/fallback, documented coverage effects. |
| M4 model/image publication | Define per-adapter exposure rules for native payloads, preprocessing, vocabularies, coordinate defaults and conditioning state; bind the candidate to its image separately. | Exact-artifact inventory, applicable disclosure-risk evidence, cold-reload/inference compatibility and independent review. |
| Identifier migration, if required | Decide whether a protected keyed mapping/HMAC is needed, with ownership, retention/rotation and explicit checkpoint migration. Changing the hash algorithm alone leaves candidate matching possible. | Authorized key-management design, compatibility/migration evidence and preservation of original observations. |

Acquisition/sharing permissions remain the U-09 gate; operational retention is U-10.
This handoff neither selects thresholds, provisions keys, changes permissions nor
authorizes experiments, public exports or deployment.

For general guidance, [NIST SP 800-188](https://csrc.nist.gov/pubs/sp/800/188/final)
emphasizes sharing models, measurable criteria and disclosure-risk evaluation.
It informs the review approach; it is not a project-specific certification or
authorization. Current local evidence is in the [A17 report](../reports/a17-privacy-claims.md).
