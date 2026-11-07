# Observation inventory references in candidates and releases

M2 increment 6 adds opt-in development candidate and release envelopes at
`2.0.0`. They use the [existing inventory transport](observation-inventory-v1.md)
and preserve the observation, source, quality-report and restoration-report wire
contracts at `1.0.0`. This is the local development boundary described in
[specification §§8–9](specification-v1.md#8-data-architecture--git-dvc-and-mlflow)
and [§12.2](specification-v1.md#122-transport-defaults).

## Identity and compatibility

| Layer | Binding |
| --- | --- |
| Observation population | SHA-256 of the canonical array of all v1 observations ordered by observation ID. The shared hasher applies the same duplicate capture and conflicting confirmed property rules. |
| Inventory reference | The closed v1 manifest in the `inventory` field. It specifies the logical digest, count, schema and writer profiles, fixed file name, and exact Parquet SHA-256 and byte size. |
| Candidate | Canonical SHA-256 excluding its self-reference. V2 replaces the inline `observations` field with `inventory` and keeps the source summaries, lineage, logical digest and aggregate quality report. |
| Release | Canonical SHA-256 excluding its self-reference. V2 binds a v2 candidate, the same exact inventory manifest, Git and DVC identities, and independent artifact hashes and sizes. |

Changing the Parquet encoding can change candidate and release identity while the
logical digest and quality report stay identical. The logical digest also remains
equal between v1 and v2 for the same observations. Reordering supplied source
envelopes or moving identical inventory bytes preserves candidate identity.
Changes inside a source envelope change its exact source SHA-256 and can change
the candidate even when all observation facts stay the same. Git commit identity
is supplied by the adapter. The release envelope stays outside the DVC payload to
avoid hashing a commit or DVC object into itself.

The standalone schema names `observation-candidate` and `dataset-release` still
validate the original v1 shapes. The additive names `observation-candidate-v2` and
`dataset-release-v2` validate v2 shapes. The semantic candidate and release APIs
recognize both versions. Candidate construction without `inventory_directory`
still builds v1 using the original bounds and default layout. V2 requires the
inventory directory during candidate construction, validation and projection.
Supplying a directory for a v1 candidate is a version mismatch. Inline and
reference-backed release layouts are separate. Existing v1 files and callers
require no conversion. Development split entry points accept both versions;
see [development splits from reference-backed releases](development-splits-reference-releases.md).

## Verified local workflow

1. Build a verified inventory with `write_observation_inventory`. Supply its
   owned directory and the complete exact source envelopes to
   `build_observation_candidate(..., inventory_directory=...)`. The builder
   derives the logical digest from the source records, then verifies the
   manifest, file SHA-256 and size, Parquet layout and every row. Candidate
   validation also requires an external `expected_candidate_ref` and pins the
   exact canonical manifest before opening Parquet. It rebuilds all lineage
   and report counts. `project_candidate_observations` returns a fresh list
   from that verified source reconstruction after all checks succeed.
2. Call `write_payload` with the same candidate, source bytes, expected reference
   and inventory directory. It verifies first, writes to an exclusive new
   directory and copies Parquet in bounded chunks. It checks the staged
   SHA-256 roster and atomically installs `candidate.json` last. The temporary
   candidate lives outside the closed roster, so cleanup failure can leave a
   temporary sibling without affecting the payload.
3. Call `LocalDvcStore.track_payload(..., contract_version="2.0.0")` and supply
   the exact committed metadata binding as in the [v1 protocol](dataset-releases-v1.md#local-dvc-protocol).
   Pass the staged `payload/inventory` directory, source bytes and artifact
   roster to `build_dataset_release`. It verifies the v2 candidate and inventory
   and requires the roster to match the embedded manifest. The pure
   `validate_dataset_release` checks envelope identity and declared correspondence.
   Actual file verification is the responsibility of `verify_payload`.
4. For local `push`, the adapter checks the committed binding, working payload
   and DVC status for stale tracked content. For `restore`, it pulls the recorded
   object into a fresh cache and checks the entire exact roster, sources, candidate,
   quality report and inventory before installing a restoration report. A v1
   restoration report binds the release reference and complete artifact roster
   digest in both workflows. `read_verified_restore` requires that report and an
   independent `expected_release_ref`, repeats the checks and returns the compact
   v2 candidate. Callers retain their expected references independently of
   untrusted documents and payload paths.

The v2 payload has exactly these paths, including one or more source files.

```text
payload/
  candidate.json
  quality-report.json
  sources/<source-sha256-hex>.json
  inventory/observation-inventory.json
  inventory/observations.parquet
```

The manifest roster entry hashes the exact canonical manifest bytes. The Parquet
entry carries the file hash and size from that manifest. The directory name
and both filenames are fixed. Documents supply no host path or URL for lookup.
Use resolved absolute paths to owned local directories for v2. Traversal,
symlink components, nonregular leaves, extra or missing files, unknown versions
and substituted inventory data fail validation. Keep inputs immutable during use.
A failed copy or verification leaves no accepted staging result or restoration
report. Retry with a new destination. Inspect any leftover temporary file or
incomplete workspace before removing it, and clean up only owned disposable outputs.

## Bounds and evidence

Each source envelope, the candidate including its lineage, and the release JSON
still have a 1 MiB cap. V2 allows 4 MiB combined source bytes across envelopes.
The existing inventory limits still apply, including an 8 KiB manifest, 128 MiB
Parquet and at most 100,000 observations. The source projection and lineage are
rebuilt in memory under the stricter source and JSON limits. A Parquet inventory
within its own limits can therefore exceed the supported candidate size. Source
envelopes retain metadata rows to make lineage independently reconstructible.
If larger releases need support, version and test bounded external lineage and
source projection before raising the limits.

Evidence covers exact local synthetic bytes, declared provenance and complete
populations in owned single-writer workspaces. The source declarations, time
quality, property matching and feature/target lineage need separate evidence.
Concurrent hostile filesystem access, power-loss durability, authorized real-data
resolution, storage and retention policy, isolation and independent verification
remain external prerequisites. See the [task record](../tasks/2026-11-07-m2-inventory-references/plan.md)
and [development checks](../development.md#observation-inventory-references).
