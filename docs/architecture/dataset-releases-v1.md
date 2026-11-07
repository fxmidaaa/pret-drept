# Development dataset releases and local restoration v1

Source proposal for frozen specification §§8–9, 12.2 and 15–16. It extends the
[metadata candidate](observation-candidates-v1.md) without changing the
[development evaluation proposal](evaluation-contracts-v1.md), legacy training or
trusted policy. This increment restores **synthetic development metadata** with
real DVC; it does not publish or approve datasets.

## Responsibilities and identities

`rent_contracts` packages the closed `dataset-release` and `restoration-report`
schemas at `1.0.0`. `rent_data.releases` constructs/validates their pure identities
and correspondence. `rent_data.release_io` stages and revalidates the fixed payload.
`rent_data.dvc_local` invokes pinned public Git/DVC CLIs for owned local workspaces.
It has no DVC SDK, harness, trusted-platform or model dependency. YAML parsing is
the optional `data` extra; DVC runs in a separately locked environment.

| Identity | Meaning |
| --- | --- |
| Listing, observation, property | Existing candidate references, including unresolved identity and unknown times; preserved without filtering |
| Candidate SHA-256 | Existing complete projection, source lineage and quality-report declaration |
| Git metadata commit | Exact full commit containing `payload.dvc`, never a branch name or shortened revision |
| Metadata SHA-256 | Exact bytes of that committed `payload.dvc` |
| DVC object | Native MD5 directory identity, including `.dir`; separate from independent artifact SHA-256 |
| Release SHA-256 | Canonical release envelope, including all provenance, metadata and artifact identities |
| Split SHA-256 | Separate development-split identity; sealing does not create membership or authorize evaluation |
| Tool profile SHA-256 | Canonical filename-to-SHA-256 map for both data-tool and build-backend locks |

Canonical JSON uses the existing UTF-8, sorted-key, compact, `ensure_ascii=False`
rule. Release/report digests omit only their respective top-level `release_digest`
or `report_digest`. Manifest construction copies caller-owned collections. Every
restore/reader requires an independently supplied `expected_release_ref`; accepting
a document's self-declared digest alone cannot establish its authenticity.

There is no hash cycle: first write the payload, run DVC add, then explicitly commit
its DVC metadata in the disposable producer repository. Construct the release
manifest from that already committed metadata. Keep the manifest and subsequent
restoration reports **outside** the tracked payload. The adapter never commits a
caller's repository. Git's actual commit identity is a binding input, not something
the release builder synthesizes or promises to reproduce from new commit dates.

## Release contents and scope

A manifest identifies dataset family, observation schema, complete observation
inventory digest/count, candidate and quality-report references, transformation and
projection/domain/property-policy revisions, and every source's exact metadata and
declared raw-source/acquisition references and acquisition period. Missing provenance
and times stay null; no dates or physical-property matches are inferred.

State is `SEALED_CANDIDATE`, access domain is `development`, and retention is
`PENDING_REVIEW` with a null policy reference. This local content-sealing step maps
to the candidate/sealing part of §8.3; it grants no published/retained lifecycle
transition or access. There is no retention duration, garbage collection, storage
approval or publication operation.

The only supported tree is:

```text
payload/
  candidate.json
  quality-report.json
  sources/<source-sha256-hex>.json
```

Candidate and standalone quality report use canonical bytes. Source envelopes keep
their exact original bytes. The manifest's sorted, unique artifact roster records
each safe relative path, SHA-256 and positive byte size. Its source roster must
match those artifacts exactly; DVC file/byte totals and source observation totals
must agree. Duplicate source/raw identities and undeclared artifacts fail.

This remains the bounded JSON metadata foundation: the existing 1 MiB document
limit also applies to each artifact. Nothing truncates or silently drops records to
fit it. This is not the §12.2 scalable table transport, a historical CSV migration,
raw-source archive or preservation proof for source data named only by a reference.
Private free text, contacts, labels and unreviewed fields have no new intake path.

## Local DVC protocol

`LocalDvcStore` accepts an absolute installed executable, explicit lock-profile
reference and bounded process timeout. `create_workspace` requires a new output
directory and existing absolute local store directory with no workspace overlap.
It creates its own Git repository, local cache and configuration. The pinned
executable must report DVC **3.67.1**. Missing tools/wrong versions fail with setup
guidance; no operation downloads or installs anything.

The supported committed YAML is exactly one directory output: root `outs`, with
`md5`, `size`, `nfiles`, `hash: md5` and `path: payload`. Reject unknown root/output
fields, imports/dependencies, per-output remote overrides, duplicate keys, anchors,
aliases, unsafe paths, invalid hashes and ambiguous totals **before invoking DVC
with that metadata**. Existing metadata is also checked before retracking. A tool
upgrade or wider profile requires deliberate compatibility/version review.

System/global DVC configuration and site cache use owned empty directories. The
controlled profile disables analytics, update checks and Studio networking. Each
workspace has only the explicit local remote and a copy-based cache; configuration
fingerprints are checked before operations. Subprocesses use an environment
allowlist, no shell, bounded duration and bounded returned output, with static safe
errors instead of raw commands, tool output or source values. Temporary diagnostic
files are not a host disk quota. No cloud remote, credentials or user configuration
are required.

`track_payload` inventories all regular payload files and checks DVC totals.
`metadata_binding` reads the exact commit and validates its metadata.
`build_dataset_release` binds that metadata to the fully rebuilt candidate and
canonical artifact roster. `push` rechecks committed/current metadata and payload
before writing to the explicit local store. Callers persist the manifest separately
and keep its expected reference independently.

`restore` reads committed metadata, creates a fresh consumer repository with its own
initially empty cache/configuration, and calls real `dvc pull` against the local
store. It never falls back to producer cache or current metadata. It then:

1. Inventories the full tree, rejecting extra/missing paths, symlinks and nonregular
   files; reads are bounded and do not follow leaf links or block on FIFOs.
2. Recomputes every artifact SHA-256/size against the release roster.
3. Rebuilds the entire candidate from all source envelopes using increment 2 and
   checks source-record lineage, observation population, unknown facts, standalone
   quality report and release provenance/canonical bytes.
4. Writes a same-directory temporary report, flushes/fsyncs it, then atomically
   links `restoration-report.json` outside the payload, refusing replacement.

The report binds the release, metadata commit, DVC version, declared tool profile,
artifact-roster digest/count, observation population and verifier Python/platform/
machine. Its `PASSED`/fresh-cache claim is **local development evidence**, not an
authenticated attestation; pure report construction cannot prove a DVC operation.
The adapter controls when it creates the completion marker. `read_verified_restore`
requires the valid marker and revalidates all payload bytes and semantics again.

Existing outputs are never reused/overwritten. An interrupted/failed attempt may
leave a new incomplete workspace; without a valid marker it is not completed. To
retry, use a new destination, or remove only that owned disposable failed workspace
after inspecting it. Earlier completed artifacts remain untouched.

## Evidence and boundaries

Checkout integration runs actual add/push/pull with disposable local repositories,
two revisions, separate empty-cache consumers, old-revision recovery, unavailable
objects and corrupted directory/artifact objects. Core shipped tests exercise
contracts, canonicalization, population/provenance mismatches, unsupported metadata,
unsafe paths, interrupted writes and process failure/timeout without pretending
those unit fixtures are successful DVC runs. See [development setup](../development.md)
and the [increment report](../reports/m2-local-dvc-releases.md).

These are single-writer local workspaces, not an OS security sandbox for hostile
processes/storage, power-loss certification, trusted data resolution or independent
verification. The lock digest identifies declared dependency inputs; numeric DVC
version checks and local installation evidence do not attest every installed byte or
the native host. Published storage, permissions, retention and protected reference
enforcement need separate external decisions and checks.

Restoration preserves supplied metadata, including eligibility issues; it does not
establish raw-source truth, feature availability, reviewed identity quality,
target-aggregate lineage or leakage freedom. The M0 historical CSV has no observation
timestamps and current acquisition does not refresh known listings (A14). No
timestamp/identity remediation or evaluation policy is activated by this increment.
The M2 reproducible-run/development-evaluation exit gate remains open.
