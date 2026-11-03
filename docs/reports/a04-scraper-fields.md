# A04 option 2 — enforce approved checkpoint columns

Date: **2026-11-03**. Task: [RP-20261103-A04](../tasks/2026-11-03-scraper-fields/task.json). Branch: `fix/repository-audit`; source baseline `7e12d691575b3a1e06277c1900c6f9637314bd4a`. Status: **implemented and locally verified**. No commit/push, live acquisition, migration or training occurred. The two pre-existing local A03 evidence updates are byte-identical.

## Changes and engineering rationale

The existing acquisition filter excluded unapproved controls from new listings, but checkpoint loading retained entire dictionaries and direct saves accepted arbitrary row keys. Six synthetic regressions failed against unchanged code as expected: unexpected `Contacte`/case-mismatched headers with and without rows, and direct saves to new/existing destinations. This reproduced the A04 bypass without accessing private rows or the network.

The scraper change is **14 added lines**:

- `CHECKPOINT_FIELDS` is one immutable storage allowlist, derived from the existing reviewed feature/filter names plus `listing_key`, `price_value`, `price_unit`, `first_seen` and `last_seen`. It adds no new listing fields or dependency.
- One shared validator rejects unexpected columns in CSV headers and row dictionaries. Header validation happens before row parsing, covering header-only checkpoints. Row validation happens before creating any output, including direct save calls. The existing reader applies the same rule to the destination and serialized temporary file.
- Rejection uses a fixed diagnostic without unexpected names or values. It preserves the original and directs the caller to a separately reviewed, versioned migration into a new destination. Column names match exactly; approved optional columns remain optional. No fields are silently removed or normalized.

Checking both boundaries closes the resume bypass and prevents direct callers from bypassing the collection filter. A shared validator avoids divergent read/write rules; deriving storage fields from the existing reviewed list avoids duplicating control names. Rejecting incompatible input preserves recoverable source data rather than implicitly rewriting it. Existing A02 validation/atomic replacement and A03 failure/retry behavior remain unchanged, as do public function signatures and new-listing filtering.

This is a bounded source correction under specification §§4.3, 6 and 8.3. Acquisition stays independent of ML/harness code, and a mutable checkpoint is not a published data release. Nine existing scraper functions, including acquisition, `main` and atomic saving, are AST-identical to the baseline. Only the existing header/row validation functions and the new shared validator enforce the additional restriction. ML/API/training, contracts, architecture, CI and dependency source are unchanged. README/development instructions document the compatibility restriction.

## Executed verification

Environment: existing **CPython 3.13.16, macOS ARM64**, unchanged dependencies and local legacy model. Scraper fixtures are synthetic; live `requests.post` is blocked unless replaced with a synthetic response. No acquisition, migration or training was used for verification.

| Check | Result | Limit |
|---|---|---|
| Original A04 counterexamples | **6 failed as expected** against unchanged source | Synthetic headers/rows only; the defect was reproduced before implementation |
| Focused scraper suite after final test edit | **75 passed**, 0 failed/skipped, 0.62 s | Includes 12 new A04 cases; existing A02/A03 regressions pass |
| Full local suite after final source/test edit | **217 passed**, 0 failed/skipped, 18.84 s | One existing Starlette/httpx deprecation warning; not model-quality certification |
| Scoped Ruff check and format | **Passed**; 23 files already formatted | Untouched legacy style debt remains outside scope |
| Pinned actionlint workflow semantics | **Passed** | No workflow or CI privilege change |
| Architecture dependency command | **Passed** | Existing A05 limits and runtime isolation remain separate |
| Preservation | **Passed** | Four private/prior-evidence digests, nine unchanged scraper functions and protected source/configuration checks |
| Final task reload, changed-document links, scope and whitespace checks | **Passed** | Includes new evidence files and the pre-existing A03 updates |
| A04 exact-commit remote CI | **Unavailable** | This patch is local; A03's successful CI does not verify A04 |

New regression coverage includes unexpected headers with/without rows, exact-name rejection, safe diagnostics, collection rejection before fetching, direct saves before output creation, contaminated destinations, all approved fields round-tripping unchanged, injected serialized columns being rejected before replacement, and synthetic new listings dropping unapproved controls/source-supplied metadata. Rejection tests compare original file bytes and check that no temporary output remains. Existing optional-subset, empty-checkpoint, long-field, write/fsync/replace and acquisition-retry cases continue to pass.

Commands (from repository root):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short tests/test_scrape.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a04-20261103/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a04-20261103/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/actionlint -shellcheck= -pyflakes=
PYTHONDONTWRITEBYTECODE=1 .venv/bin/rent-check-architecture --root .
git diff --check
```

Logs and preservation identities are under `/private/tmp/pret-drept-a04-20261103`. No large logs, private records or model payloads were added to task documentation. Only the six intentional pre-fix reproductions failed; all final local checks passed without skips.

## Limits and exact recovery action

Column validation does not detect personal information inside approved free text or establish anonymity (A17). It adds no migration tool, concurrent-writer coordination, immutable observation history or dataset-release procedure. Contaminated files must be retained and migrated separately under reviewed source/destination schemas. Runtime isolation, model acceptance and deployment are not certified. This review was performed by the implementing agent, not independent protected verification.

Recovery: read the [task record](../tasks/2026-11-03-scraper-fields/task.json), confirm `fix/repository-audit` remains at `7e12d69` plus the bounded local A04 patch, and preserve the two pre-existing A03 evidence updates. Review the A04 diff and reproduce the commands above. The approved local implementation is complete; obtain separate branch/message approval before any commit/push. Other audit findings, live acquisition and migration require separate decisions.
