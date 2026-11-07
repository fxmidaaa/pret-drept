# M2 increment 6 — verified observation inventory references

## Scope and starting state

L1 engineering under [§6](../../architecture/specification-v1.md#62-risk-classification).
This [request](request.md) concerns the synthetic candidate and development-release
boundary. The observed branch is `main`, HEAD `7f69b177222e3fde58cd070e05228d81cc56539f`
and the index is empty. The inventory transport is merged. The two modified files
in `docs/tasks/2026-11-05-audit-report-consistency/` must retain their starting bytes.

| Existing file | Starting SHA-256 |
| --- | --- |
| `plan.md` | `1ba54d3d91900a393317ab043f0a90c8c46e11bbc0347ce23518461f3a4d16a2` |
| `task.json` | `b38332bc330b29cb66eccc5176ee9d085b0ff570c8c23218ef996e73d7295da6` |

The [inventory handoff](../2026-11-07-m2-observation-inventory/plan.md#later-work)
is the immediate predecessor. The existing candidate rebuilds from all exact JSON
source envelopes. Release verification binds Git/DVC metadata and an independent
SHA-256 roster, then repeats the rebuild. The inventory reader checks the exact
roster, typed Parquet bytes, schema, full ordered population and logical digest.
The development split consumes the v1 inline candidate. The [M0 audit](../../reports/m0-alignment.md)
and [A14 handoff](../../reports/a14-evaluation-handoff.md) leave real chronology,
reviewed property evidence and official evaluation prerequisites open.

## Design and requirements

Use additive candidate and release `2.0.0` documents. Embed the closed v1 inventory
manifest as the reference, replace the candidate's inline observations, and add
the two inventory files under a fixed directory inside the same v2 DVC payload.
The release roster binds their exact SHA-256 and sizes. Candidate rebuild preserves
exact source lineage and quality counts and checks the source-derived logical digest
and count against the verified inventory. Preserve v1 schemas, bytes, defaults and
payload roster. The v1 split boundary stays pinned to its supported release version.

The scoped architecture is §§4.3 and 5 (data and dependency ownership), §§8.1–8.5
(Git/DVC and independent artifact identities, restore, development-only state),
§§9.1–9.6 (stable identity and complete declared observation population), §12.2
(versioned JSON and typed Parquet), and §§15–16 (unprivileged verification and
restoration tests). The wire version change leaves frozen decisions intact.

An unversioned optional field would change the existing closed formats. A detached
sidecar could disappear independently of the release's DVC object. Keeping both
inline rows and Parquet would duplicate the candidate's full population. The v2
roster adds two fixed paths and retains v1 source envelopes for independent lineage
rebuild. A 4 MiB aggregate source-byte cap in v2 permits a multi-envelope inventory
beyond the old aggregate bound while retaining per-document and lineage caps. This
keeps source projection bounded in memory pending separate scalability work.

## Acceptance criteria and implementation plan

1. Package two closed additive schemas and reuse the v1 observation, inventory,
   quality and provenance contracts. Unknown versions and mixed layouts fail.
2. Construct and validate reference-backed candidates using the existing full
   inventory verifier and source population rules. Pin the expected physical
   manifest before Parquet parsing on read. Preserve unknowns, numeric/time wire
   details, source lineage and aggregate quality. Verify deterministic identity and
   identity changes on physical re-encoding and source/provenance substitution.
3. Stage a closed v2 DVC payload without overwriting, bind its exact artifacts to a
   sealed release, and reverify before creating or consuming a restoration marker.
   Reject incomplete, unsafe, oversized, tampered or mismatched inputs with safe
   errors. Keep staging/verification local and the optional PyArrow backend lazy.
4. Test public v1 compatibility and v2 fail-closed behavior at split entry points.
   Use real local Git/DVC in disposable synthetic fixtures, including restoration
   of the exact older v2 release from an independent empty cache and failure paths.
5. Review the final diff, verify the working tree and preservation, run the guide's
   focused, checkout, package/distribution, static and task checks, and record the
   results and exact recovery. Stop at `READY_FOR_REVIEW` if required checks pass.

## Verification and recovery

See the [development guide](../../development.md). Use the pinned local Python,
PyArrow and DVC tools. Run the checkout suite with `-m 'not legacy_artifact'` to
keep the checks within the synthetic scope. Use owned disposable pytest roots.
The starting Git state and 203 file hashes are in
`/tmp/pret-drept-m2-inventory-references-Ws30sHgl`. Reconcile the index and HEAD,
compare those hashes and the scoped diff, and preserve both unrelated edits.
Retry failed staging or restoration in a fresh owned destination. Exact Linux CI
for this working tree awaits a separately authorized source publication.

Real-data work requires approved projection and handling, reviewed chronology or
remediation, property evidence and policy, and storage, access, retention and quality
decisions. Isolated execution, feature lineage and independent verification have
separate prerequisites. The M2 exit gate remains open.

## Maintainer review

The [design](../../architecture/observation-inventory-references-v2.md) separates
syntax validation, declared correspondence and verified file consumption.
Reconstructing both source lineage and the inventory digest makes source
envelopes authoritative for which observations were supplied. The Parquet
manifest additionally pins the precise encoding. The copied artifact is hashed
again before staging completes, and verified restore checks its schema and
population through the existing reader before installing the completion report.

Review found two failure edges. Staging the candidate's temporary file inside
the closed payload could leave an extra artifact after cleanup failure. The
temporary file now lives in the owned parent and the final link remains atomic.
Also, DVC metadata with unchanged file counts and byte totals can describe an
older payload. V2 local push requires a clean pinned DVC status in addition to
the committed metadata binding and SHA-256 verification of the working payload.
Fresh-cache restoration supplies the end-to-end correspondence check.

V2 continues to store exact v1 source envelopes with their observation metadata
and bounded inline lineage. This retains a source-backed reconstruction path
at the cost of duplicated metadata and an in-memory projection. If authorized
inputs exceed the envelope or lineage budgets, version and test a bounded
external source and lineage format before applying the release workflow to them.
Both reference formats use owned immutable local inputs during each operation.
Runtime access controls, hostile concurrent mutation and crash durability require
separate enforcement or evidence.

## Final verification

The final implementation checks used CPython 3.13.16 on Darwin ARM64,
PyArrow 26.0.1, DVC 3.67.1, actionlint 1.7.12 and Node 24.21.0. The actual
v2 DVC fixture recovered 1,800 observations, with 1,796,401 logical JSON bytes,
1,365,703 Parquet bytes, 1,884,906 exact source bytes and a 488,555-byte candidate.
Only disposable synthetic repositories and local stores were used for Git/DVC
integration. The project index and branch tip stayed at their starting state.

| Status | Check | Evidence and exact recovery |
| --- | --- | --- |
| Passed | Focused candidate, inventory, release, evaluation, split and architecture tests | **549 passed**, including 31 new v2 foundation cases. Run the first command under [observation inventory references](../../development.md#observation-inventory-references). The tests reject changed physical encodings, forged logical digests with matching file hashes, source/report/lineage tampering, unsafe paths, missing data and interrupted copies. |
| Passed | Actual local Git and DVC | **14 passed**, including two new v2 cases. Exact older release, independent empty cache, SHA-256, complete observation parity, corrupt and absent Parquet objects, and stale metadata with matching totals were exercised. Run the integration command in the same guide section. Restore the [pinned local tool setup](../../development.md#separate-local-data-tools) and use fresh destinations on retry. |
| Passed | Checkout regression | **875 passed**, **12 private-model checks deselected**, one existing Starlette/httpx deprecation warning. Run the guide checkout command with `-m 'not legacy_artifact'`. |
| Passed | Source and wheel | **680 passed per distribution**, including both v2 schemas. Run `.venv/bin/python scripts/check_distribution.py`. The script uses an extracted source tree and built wheel with editable checkout imports bypassed. |
| Passed | Static, workflow, notebooks, frontend and installed dependencies | Ruff and format for 56 files, architecture, actionlint, two notebook checks, **38 frontend passes** and `uv --offline pip check --python .venv/bin/python` for 59 installed packages. Rerun the [guide commands](../../development.md#development-and-verification) and the uv check. |
| Passed | V1 wire compatibility | The synthetic candidate, release, payload roster and restoration report compare byte-for-byte with the starting source imported from `git archive HEAD src`. Rerun the compatibility comparison in the recovery commands below. |
| Passed | Task, links and working tree | The starting 203 tracked paths include 184 byte-identical files and 19 scoped edits. There are nine added paths. The check pins 18 implementation hashes, verifies all 26 task records, checks local links and preserves both unrelated edits, the 16 original schemas, the frozen specification, workflow and locks. Run the review proof and repository task tests below. |
| Failed, recovered | Interim interrupted-writer regression | The first aggregate run hit `test_interrupted_atomic_creation_leaves_no_final_split[write]` in focused, checkout and extracted-source testing. The shared writer now enters the opened stream and uses the object supplied by its context manager. Rerun the focused interruption tests, then checkout and both distributions. The final runs above passed. |
| Failed, recovered | Local verification setup commands | The uv-managed environment lacks pip. Use the offline uv check above. Use BSD-compatible `mkdir -p "$evidence_dir/baseline"` and `git archive HEAD src \| tar -xf - -C "$evidence_dir/baseline"` instead of GNU tar's `--transform`. Resolve both sides of the compatibility import path assertion because macOS `/tmp` is an alias. |
| Skipped | Private-model checks and work outside this increment | The 12 model-dependent regressions were intentionally excluded. Any separate run requiring a private model or real data needs authorization and approved handling. Split adoption, baseline training, acquisition, data publication and protected operations are later work. |
| Unavailable | Exact-tree Linux CI, protected verification and the M2 exit gate | A later authorized source publication enables exact-revision CI. Real-data and official evaluation need approved input handling, defensible chronology or remediation, reviewed property evidence and policy, storage/retention decisions and isolated reproducible execution with independent evidence. |

Logs and starting/final fingerprints are under
`/tmp/pret-drept-m2-inventory-references-Ws30sHgl`. Use these commands from the
project root to reproduce the final review proof.

```bash
. /tmp/pret-drept-m2-inventory-references-Ws30sHgl/check-env.sh
PYTHONPATH="$evidence_dir/baseline/src:$PWD/tests" .venv/bin/python -P \
  "$evidence_dir/check_inline_compatibility.py" "$evidence_dir/baseline/src" \
  > "$evidence_dir/inline-before.json"
PYTHONPATH="$PWD/src:$PWD/tests" .venv/bin/python -P \
  "$evidence_dir/check_inline_compatibility.py" "$PWD/src" \
  > "$evidence_dir/inline-after.json"
cmp "$evidence_dir/inline-before.json" "$evidence_dir/inline-after.json"
PYTHONPATH="$PWD/src" .venv/bin/python "$evidence_dir/check_review.py" READY_FOR_REVIEW
.venv/bin/python -m pytest -p no:cacheprovider -q -ra \
  tests/foundations/test_repository_tasks.py tests/foundations/test_tasks.py
```

If the temporary evidence directory expires, inspect `git status --short --branch`,
`git rev-parse HEAD`, `git diff --cached --name-only` and `git diff --check`.
Compare the two report-consistency SHA-256 values above, inspect the scoped diff
against the starting HEAD and rerun the guide's checks with fresh owned pytest and
cache directories. Use a fresh local workspace for a failed staging or restore.

## Review handoff

The bounded increment is `READY_FOR_REVIEW` on `main` at `7f69b17`, uncommitted
with an empty index. See the [increment report](../../reports/m2-inventory-references.md).
The single next increment is v2 adoption in development split materialization.
It should bind the verified complete v2 inventory and demonstrate membership
parity with the existing v1 flow on the same synthetic observation population.
