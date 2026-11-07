# Observation inventory transport v1

M2 increment 5 implements the approved local transport for v1 observation
references. The [frozen architecture](specification-v1.md#122-transport-defaults)
selects versioned JSON for structured control documents and typed Parquet for
tabular inputs and outputs. The artifact carries one complete supplied inventory.
Dataset-release identity, source provenance and evaluation membership continue to
use the existing [candidate](observation-candidates-v1.md),
[release](dataset-releases-v1.md) and [split](development-splits-v1.md) contracts.

## Identity and data model

An inventory directory contains `observation-inventory.json` and
`observations.parquet`. The closed v1 manifest identifies the observation contract
version, schema and writer profiles, count, logical digest, fixed Parquet path,
file SHA-256 and byte size. The reader requires an independently supplied expected
logical digest. A later release can also bind the exact manifest and file
identity when restoring a particular physical artifact.

`observations_digest` is SHA-256 of the existing v1 canonical JSON array in
ascending observation ID order. `ObservationInventoryHasher` updates that hash
with each canonical row and the array delimiters. It shares row, calendar,
duplicate listing capture and conflicting confirmed property rules with
`observation_inventory_digest`. The legacy helper still accepts an unordered
list and enforces its 1 MiB canonical JSON cap. The new writer requires a
nonempty iterable with strictly increasing IDs so it can encode one batch at a
time. Listing capture and confirmed property indexes retain at most one entry of
each kind per row. Those indexes are linear in the bounded record count.

The exact `observation-reference-parquet-v1` schema declares UTF-8 fields and
their nullability, with a required property identity struct. Four timestamp
columns preserve the original nullable text, including offsets and fractional
seconds. Unknown and contradictory evidence survive round trip for later
eligibility handling. The struct stores confidence as nullable double plus
nullable `confidence_is_integer`. A null confidence has a null marker. The
marker distinguishes the v1 integer values 0 and 1 from floating values such
as 1.0 and -0.0. Decoding removes the marker and validates the original
observation shape. The schema contains metadata fields and accepts neither
targets nor feature columns. The writer applies no exclusion, matching or time
inference.

The pinned writer profile uses PyArrow 26.0.1, Parquet 2.6, plain uncompressed
pages and page checksums. This increases disk use and keeps decoding and
floating-point representation straightforward. It omits dictionaries,
statistics, page indexes and Arrow schema metadata. The reader checks the
expected schema, footer profile, row counts, local column chunks and their
contiguous byte layout, and enables native page checksum verification. File
SHA-256 identifies the exact bytes. Row group sizing can change that hash while
preserving logical identity. The same writer configuration is tested in
separate local processes. Cross-platform byte equality is outside that evidence.

## Local API and bounds

Use `rent_data.inventory_io` with the optional `parquet` extra.

- `write_observation_inventory(destination, observations, limits=...)` creates a
  new absolute directory under an owned parent. It streams ordered observations,
  hashes the file, rereads and validates every row and atomically installs the
  canonical manifest. It returns the manifest after completion.
- `verify_observation_inventory(root, expected_inventory_ref=..., limits=...)`
  checks the exact directory roster, manifest, bytes, schema, population and
  logical digest, then returns the verified manifest.
- `iter_verified_observations(root, expected_inventory_ref=..., limits=...)`
  performs the same full verification on first use and then yields decoded rows
  on a second pass through the same open file. Exhaust or close the iterator to
  release the file.

`InventoryLimits` defaults to 100,000 records, 128 MiB of Parquet bytes and
1,024 rows per batch. Callers can lower the row and byte caps and use batches
up to 2,048 rows. A write batch is one row group. The reader independently
bounds physical groups to 2,048 rows each and can decode them in smaller batches.
The profile allows up to 4,096 row groups, an 8 MiB Parquet footer and an
8 KiB manifest. A small write batch can exhaust the row group budget before
the row budget. The backend bounds native metadata parsing and verifies the
file size and hash before parsing. These are application limits. Host-level
resource enforcement and admission of hostile inputs require separate controls.

Keep the caller-owned directory and its contents immutable for the duration of
verification and consumption. The reader opens regular leaves at fixed paths and
keeps the verified Parquet descriptor for both passes, which prevents swapping
the input by renaming the path. Concurrent in-place mutation and filesystem crash
durability are outside the local protocol. The writer refuses existing output.
A failed write can leave an incomplete directory. Retry with a new destination,
or inspect and remove only owned disposable files. A missing or invalid manifest
prevents verification.

## Evidence and adoption

Synthetic tests cover exact v1 digests, numeric and time round trips, invalid
metadata and populations, and an inventory whose logical JSON and physical
Parquet each exceed 1 MiB. An actual local DVC fixture restores both files from
exact synthetic Git metadata through an independent empty cache. The production
v1 DVC adapter retains its candidate, quality report and source JSON roster.

Reference-based adoption in candidate and release contracts needs separate
review before split consumers can use these artifacts. Real data requires
authorized projection and handling, defensible chronology or approved
remediation, reviewed property evidence and policy, and storage, access,
retention and quality decisions. Feature and target-derived lineage, isolated
execution and the M2 exit gate require their own evidence.

See the [implementation record](../tasks/2026-11-07-m2-observation-inventory/plan.md)
and [development setup](../development.md#observation-inventory-transport).
