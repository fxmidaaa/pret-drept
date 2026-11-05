# RP-20261103-A05 — detect indirect imports and source symlinks

L1 engineering on `fix/repository-audit` at `af574c9`. The user chose A05 option 1. Scope covers the existing checker, focused tests, development guidance and task evidence. Preserve the four local A03/A04 evidence files. The existing dependency rules implement architecture v1 §§4.3 and 16.5. This is source validation for unprivileged CI.

1. Inventory project Python sources and explicitly classify legacy modules, source packages and tooling. Reject unclassified sources, ambiguous module identities and symlinks in the scanned tree. Exclude known environment, cache, data and build locations.
2. Parse each source once. Resolve ordinary absolute and relative imports, package initializers and supported literal loader calls against the checkout. Reject recognized dynamic imports with uninspectable targets.
3. Build a graph and trace forbidden dependencies through classified intermediate modules. Preserve the current CLI and support existing legitimate public contract, standard library and legacy imports.
4. Reproduce the two audit gaps with synthetic fixtures and test valid imports, cycles, package initialization, and diagnostic paths. Run the full local suite, scoped source checks and architecture CLI. Record results and recovery before review. Publication requires separate approval.

The checker models inspectable Python import syntax within the declared checkout layout. Runtime loading, import hooks and environment isolation require separate verification.

## Verification

The two original fixtures each returned zero violations before implementation. The updated checker flags the unclassified bridge and traces its forbidden dependency. It rejects source symlinks at the source root, package level, nested directory level and file level. A classified agent → data → legacy ML fixture verifies that the graph detects a forbidden chain even when the individual imports are allowed. The earlier package-symlink fixture had its target inside the checkout. The test now places the target outside so it can assert that discovery never traverses the link.

| Check | Result |
| --- | --- |
| Architecture regressions | 30 passed, including cycles, package initialization, loader spellings and valid legacy and contract imports |
| Full local suite | 231 passed, zero failed or skipped, one existing Starlette warning |
| Source and workflow checks | Scoped Ruff lint and format, pinned actionlint, architecture CLI and whitespace checks passed |
| Preservation | Four pre-existing A03/A04 evidence files verified against pre-edit digests |
| Remote CI | Passed for d11304a. 219 passed, 12 skipped because the private model is absent, one warning. [Run 41724876763](https://github.com/fxmidaaa/pret-drept/actions/runs/41724876763) |

A temporary 2,002-file source tree produced the expected 2,001-edge forbidden chain in 0.181 seconds on this workstation. This is one synthetic run. Parsing happens once per file. A reverse traversal per domain finds shortest paths through cycles without recursion.

Reproduction commands from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_architecture.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a05-20261103/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a05-20261103/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short
.venv/bin/ruff check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/ruff format --check src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py
.venv/bin/actionlint -shellcheck= -pyflakes=
PYTHONDONTWRITEBYTECODE=1 .venv/bin/rent-check-architecture --root .
git diff --check
```

Recovery: Confirm `fix/repository-audit` at `d11304ad1534f2eae1adb30520b338c9b239839c`. Preserve the local A03, A04 and A05 evidence updates. Publication of the evidence files requires separate approval.

The user approved publication by asking to push the proposed commit to the remote. Publish the five A05 files to `fix/repository-audit` with message `fix(architecture): detect forbidden import chains and source symlinks`. Inspect the resulting GitHub run and record its result locally.

GitHub confirmed the push at `d11304a`. The foundations job completed workflow validation, static checks, dependency checks, tests and the distribution build. The test log reported 219 passes and 12 explicit private-model skips in 3.45 seconds. Existing deprecation warnings remain in the job log. [Run 41724876763](https://github.com/fxmidaaa/pret-drept/actions/runs/41724876763)

## Current recovery pointer — 2026-11-05

Earlier checkpoints above are historical evidence, including their source/CI identities.
Current branch state and next actions are in the [audit index](../../reports/README.md#current-checkpoint-and-recovery)
and [completion plan](../2026-11-05-audit-completion/plan.md): `fix/repository-audit` at
`36e67b7` plus uncommitted audit work. Inspect actual status/diff and preserve all local
changes; do not restore an older branch tip or infer publication authorization.
