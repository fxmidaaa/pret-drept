# Observation provenance and candidates v1.0.0

Status: source implementation for review; **metadata candidates only**. Authority:
frozen specification §§4–5, 8–9 and 16.2, and the
[first M2 handoff](../tasks/2026-11-05-m2-evaluation-contracts/plan.md).
This extends [public contracts](contracts-v1.md) without changing the
[proposed evaluation rules](evaluation-contracts-v1.md), legacy cleaning or training.

## Boundary and ownership

`rent_contracts` owns three additional closed JSON schemas. `rent_data.candidates`
owns pure candidate building, source correspondence and validated projection. It
imports public contracts and the standard library, independently of ML, the harness,
privileged resolution, DVC, MLflow and network services. The existing architecture
checker already classifies `rent_data` as the data domain.

The input is a list of **already projected UTF-8 metadata envelopes as bytes**.
This is not an adapter for the private historical CSV or the scraper checkpoint.
It neither reads a host path nor strips unknown fields from raw records. Unexpected
fields fail the complete input. An authorized, independently reviewed upstream
extractor must eventually establish the correct private field projection and facts.
No target, address, contact, source text, arbitrary feature or selector fields exist
in these envelopes. Identifiers/digests may still be sensitive; allowlisting does
not establish anonymization or permission to publish.

## Three documents

| Schema | Contents |
| --- | --- |
| `observation-source` | `raw_source_ref`, nullable acquisition provenance/period bounds, and nonempty `records` mapping a stable `source_record_id` to the existing `observation-reference`. |
| `observation-quality-report` | Assessment version, source/inventory identities, observation/listing counts, property-resolution counts, existing non-window eligibility issue counts, affected-observation union count, missing acquisition evidence counts and a self-digest. |
| `observation-candidate` | Dataset family, development-only scope, fixed `UNPUBLISHED_CANDIDATE` state, transformation/projection/domain/matching references, source summaries, full lineage/inventory, aggregate report and a self-digest. |

All use `contract_version=1.0.0` and local schema references. Unknown fields/versions
fail. `validate_document` is structural; semantic helpers are required for calendar
validity, integrity, exact population and counts. No document grants data access,
policy approval, sealing or publication.

`raw_source_ref` identifies the claimed upstream raw snapshot. Its bytes are **not**
provided or verified here. The separate candidate `source_ref` hashes the exact
supplied metadata-envelope bytes. Neither reference proves that the upstream
projection was complete, privacy-safe or truthful. The candidate conserves the
supplied metadata inventory; an authorized resolver/reviewed extractor must later
establish its relation to actual raw data.

## Identity, lineage and time

Source record IDs are explicit upstream identities scoped by `source_ref`; they
may repeat across sources. The builder never assigns them or observation/listing/
property IDs from row positions, hashes, attributes or prices. A reviewed upstream
identity policy remains necessary. Repeated listing captures and properties are
retained at distinct collection instants.

One metadata envelope per raw snapshot is supported in v1. Duplicate source bytes
or raw-source references fail, as do duplicate source record IDs within an envelope.
The existing inventory validator also rejects duplicate observation IDs, aliased
listing/collection instants and conflicting confirmed property IDs for one listing.
These are whole-candidate errors, not deduplication. Sharding/multiple projections
of one raw snapshot require a versioned transport/lineage extension.

Lineage has one `(observation_id, source_ref, source_record_id)` entry per supplied
record. Sources sort by digest; observations/lineage sort by observation ID. All
observations are projected, including invalid/unresolved domain metadata, unknown
times and uncertain properties. Recipe domain/matching references must agree with
every observation.

Acquisition bounds describe the upstream collection period, not import time. Each
is explicitly nullable. Known bounds use the existing timezone-qualified instant
syntax and real calendar dates; start must be at/before end. A known collection
instant must lie within each known bound, inclusively. Impossible dates, reversed
periods and contradictory source collection claims fail. Publication may predate
acquisition. Observation availability order uses the existing evaluation semantics.
No bound is inferred from record dates or the clock.

Missing acquisition evidence is counted and preserved; it does not silently alter
evaluation policy. Source claims still require independent verification. M0's
historical CSV has no defensible observation chronology; an import timestamp or
today's source metadata cannot repair that omission.

## Deterministic artifacts and validation

Public operations in `rent_data.candidates`:

```python
candidate = build_observation_candidate(
    source_documents,
    dataset_family=family,
    transformation_ref=transformation,
    projection_policy_ref=projection_policy,
    domain_policy_ref=domain_policy,
    property_matching_policy_ref=matching_policy,
)
validate_observation_candidate(
    candidate, source_documents=source_documents,
    expected_candidate_ref=fixed_candidate_ref,
)
observations = project_candidate_observations(
    candidate, source_documents=source_documents,
    expected_candidate_ref=fixed_candidate_ref,
)
```

The source list is nonempty bytes, not paths, strings, streams or implicit encodings.
Shared strict UTF-8/JSON decoding rejects BOMs, duplicate keys and malformed/nonfinite
input. Construction returns a fresh JSON document; it retains no caller state,
registry, source bytes or mutable global candidate. Validated projection returns an
independent copy. Modified dictionaries require revalidation; they are not immutable
or authenticated storage.

Revalidation checks schema, self-digests and the externally fixed candidate identity,
then rebuilds the complete expected candidate from source bytes. It compares recipe,
source summaries, population, lineage and every report count. Resealing false counts,
altered observations or lineage cannot make them match the original sources. Changing
a valid recipe changes identity; an external expected reference prevents substitution.

Acyclic identity graph:

1. `source_ref`: SHA-256 of exact supplied UTF-8 metadata bytes, including whitespace.
2. `observations_digest`: existing inventory digest, sorted by observation ID.
3. Report `sources_digest`: canonical SHA-256 of sorted source summaries. Its
   `report_digest` hashes all report content except its top-level self-reference.
4. `candidate_digest`: canonical SHA-256 of the full candidate, including its report
   and report digest, except the candidate's own top-level self-reference.

Canonical JSON uses existing local v1 sorted keys, compact separators, UTF-8 and
`ensure_ascii=False`, not RFC 8785. No clock, random IDs, model state or environment
defaults enter construction. Reordering supplied documents leaves the candidate
identical. Reserializing/reordering records **inside source bytes** changes source/
candidate identity; unchanged observation facts retain inventory identity and counts.

Existing 1 MiB document limits apply. Complete supplied source bytes are also bounded
to 1 MiB; expanded output can hit its own bound first. Either case fails without
truncation or a partial result. This is an incremental metadata boundary, not the
final table transport for the historical dataset. Scalable columnar/external inventory
transport must be designed/verified before real releases exceeding these bounds.

## Quality report and evidence limits

The additive public `observation_eligibility_exclusions` helper extracts existing
v1 non-window checks unchanged. Both splits and candidate reports use it. It returns
immutable reasons for invalid/unresolved non-target domain metadata, missing temporal
evidence and invalid availability order. No cutoffs, split selection or matching is
introduced. Uncertain property identity alone does not exclude future-market rows.

Issue counts overlap; `observations_with_eligibility_issues` counts the union.
Property-resolution counts count **observations**, not proven unique apartments.
Listing count uses distinct references. Source counts describe missing evidence/
period bounds per source. None is a model metric, confidence calibration or readiness
gate. No record is dropped because it contributes a quality issue.

The report has no row identities/samples, raw text, addresses, labels or target
statistics. Digests/counts may still require private handling. A standalone schema
pass does not verify counts; export only after full candidate revalidation.

This is not a full §8.2 release: Git/DVC metadata/object identity, verified raw bytes,
retrievability, retention, sealing and publication remain later work. A candidate
digest must not be presented as an approved dataset release reference. No real
development manifest, baseline, feature/aggregate-lineage verification, protected
access enforcement or M2 exit-gate pass is claimed.

Next dependency: immutable Git/DVC release envelopes and local restoration checks,
initially synthetic, with scalable transport and storage/access/retention decisions
before real publication. Real-data projection, domain/currency provenance, acquisition
rights, chronology and property identity require existing reviews/authorizations.
Evidence: [second M2 task](../tasks/2026-11-06-m2-observation-candidates/plan.md).
