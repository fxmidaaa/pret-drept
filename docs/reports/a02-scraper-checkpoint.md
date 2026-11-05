# A02 option 1 — checkpoint preservation and engineering review

Current publication status was reconciled on 2026-11-05. The approved fix is published and its
exact-commit CI passed. See [publication reconciliation](#publication-reconciliation).
The dated local review below is retained as a historical checkpoint.

Date: **2026-11-02**. Task: [RP-20261102-A02](../tasks/2026-11-02-scraper-checkpoint/task.json). Branch: `fix/repository-audit`, baseline `2a5beefc74ff51f3c962156a1cf6eaf2f1ae287e`. Status: **implemented and locally verified; ready for review**. No A02 commit/push, real collection, migration, training or protected operation occurred. The two pre-existing local A01 evidence updates remain byte-identical.

## Implemented behavior and architectural fit

The legacy loader silently discarded rows missing `listing_key`, allowing the next page save to replace the historical CSV with only newly collected state. It now rejects incompatible input before any fetch, validates the complete CSV without silently skipping records, and preserves unique 16-character lowercase hexadecimal keys exactly. Standard-library CSV reading keeps cell text, leading zeros, literal `NA`, quotes, Unicode and multiline fields. Duplicate/blank headers, inconsistent row widths, invalid keys, duplicate records, invalid UTF-8 and unreadable/empty existing files fail with safe diagnostics. A missing path starts empty state without creating files; a valid header-only CSV is a readable empty checkpoint.

Saving validates new identities and the existing destination, refuses record deletion, writes a private same-directory temporary file, flushes/fsyncs it, re-reads its schema/population, and calls `os.replace` only after validation. Earlier bytes survive the tested pre-replacement failures; temporary files are cleaned on handled failures. Symlink checkpoints are rejected. Working-state replacement is not dataset publication, and published releases must not be used as checkpoints.

The existing `python scrape.py` entry point/default path remain. Its incompatible historical `id` schema now produces an error before collection. The additive `--checkpoint` option supports a separately selected working file for future authorized collection. It does not migrate the historical file, invent timestamps, or change `train.py`'s input. A separate reviewed migration remains necessary if the historical data is to be converted.

This implements the bounded A02 repair under specification §§4.3, 6 and 8.3–8.5: acquisition stays independent of the harness, historical input remains recoverable and unchanged, and mutable working checkpoints are distinguished from immutable releases. No service, framework, dependency or new ML/agent layer was introduced. `scrape.py` was formatted as the changed legacy file; AST comparison confirms the existing six fetch/filter/key functions and fifteen collection constants are semantically unchanged. CI/development static checks now include the touched scraper and new tests.

## Executed verification

Environment: existing **CPython 3.13.16, macOS ARM64** environment with unchanged hash-locked dependencies and real local legacy model. All scraper fixtures use synthetic files and block `requests.post`. The CLI help check runs in-process with checkpoint reads blocked as well; no child process can escape test network interception.

| Check | Result | Limit |
|---|---|---|
| New legacy-schema rejection test against unchanged code | **Failed as expected**: no exception; loader reported zero records | Reproduced the A02 failure without modifying the synthetic file or accessing the network |
| Review probe with a long cell and reduced process CSV limit | **Initially failed; corrected and passed** | Parser now sizes its temporary limit to the open file and restores it on exit |
| `.venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short tests/test_scrape.py` | **31 passed**, 0.34 s | Real CSV/atomic filesystem behavior with simulated failures; no live acquisition |
| Full local pytest suite with `-p no:cacheprovider -q -ra --tb=short` | **173 passed, 0 failed, 0 skipped**, 19.09 s | One existing Starlette/httpx deprecation warning; not model-quality certification |
| Ruff check/format on `src scripts scrape.py tests/foundations tests/test_scrape.py tests/conftest.py` | **Passed**, 23 files formatted | Other legacy style debt is outside this increment |
| `.venv/bin/actionlint -shellcheck= -pyflakes=` | **Passed** | Source-semantic validation, not execution of this unpublished revision |
| `.venv/bin/rent-check-architecture --root .` | **Passed** | Existing A05 checker gaps remain; no runtime isolation claim |
| Input/prior-work SHA-256 checks | **Passed**, four unchanged identities | Private CSV/model and the two pre-existing A01 evidence files; no row values logged |
| AST and protected-source Git comparison | **Passed** | Legacy acquisition logic/constants, ML/API/training, contracts, architecture, dependency pins and Docker source preserved |
| Final task reload, documentation links and `git diff --check` | **Passed** | Final metadata validated after evidence persistence |
| A02 real GitHub run | **Unavailable** | Publication requires branch/message approval; A01's successful run does not verify A02 |

The 31 regression cases cover legacy schema rejection, rejection before fetching, malformed CSV/key/header/encoding cases, missing/header-only/empty states, round-trip cell values, explicit paths, write/fsync/replace failures, incomplete serialized rows/columns, invalid mapping or dropped records, incompatible destinations, symlinks, long fields, compatible synthetic resume, and offline CLI help.

Full-suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/pret-drept-a02-20261102/matplotlib NUMBA_CACHE_DIR=/private/tmp/pret-drept-a02-20261102/numba .venv/bin/python -m pytest -p no:cacheprovider -q -ra --tb=short
```

The full test log and preservation digests are under `/private/tmp/pret-drept-a02-20261102`. No large logs, raw data or model payloads were added to task records. No environment/dependency recovery was needed; the two expected failing probes were resolved as described above.

## Engineering review and limits

Validation and atomic replacement address different failures: validation prevents silently reduced state from becoming authoritative, while replacement prevents an interrupted direct CSV write from destroying the previous checkpoint. Rechecking the destination also protects direct calls to the new save helper from overwriting incompatible data. Read-back population and column checks detect incomplete serialization before replacement. The actual collection flow is tested with synthetic results, not merely mocked successful writes.

Review caught the standard CSV parser's default cell-size limit, which could reject legitimate long ad text. The implementation temporarily raises that limit only to accommodate the open file size and restores the prior process setting; a regression verifies both round-trip and restoration. This standalone legacy script assumes one checkpoint operation at a time. Concurrent checkpoint access, hostile filesystem races, sudden power-loss durability and DVC backup/restoration remain unverified. A hard kill before replacement can leave a private temporary file; it does not make that file an approved replacement.

A03 retry/completeness behavior and A04 resumed-field minimization remain open. Optional columns are preserved, so the existing broad privacy claims are not certified by this storage repair. Immutable observation history, dataset release publication/retention and official temporal evaluation remain later work. A05 and A11 remain unresolved; this increment does not certify static isolation or extracted-distribution tests. This review was performed by the implementing agent and is not independent protected verification.

## Exact next recovery action

Read the task record, inspect the A02 diff and preserve the two prior local A01 evidence updates. Proposed A02 commit message: `fix(scraper): preserve checkpoints with validated atomic saves`; branch: `fix/repository-audit`. Obtain user publication approval before commit/push. After approved publication, inspect the exact new GitHub run and record its actual result and any private-artifact skips. A real migration, live collection and other audit fixes each require their own approval.

## Publication reconciliation

Git history and GitHub CI were reconciled on 2026-11-05. The approved A02 fix was published as
[`9341519`](https://github.com/fxmidaaa/pret-drept/commit/9341519338a35f37541b9c25b1d89ff4b9f787ba)
on `fix/repository-audit`. [Run 41526231926](https://github.com/fxmidaaa/pret-drept/actions/runs/41526231926)
matches that exact source and passed. Its test log reports 161 passed, 12 private-model checks
skipped, and one existing warning.

The earlier local suite recorded above had 173 passes with the private artifact available.
The task record now includes the published revision and CI reference. Current recovery starts
by confirming this revision in Git history and reading the run. A02's checkpoint fix is
published. Historical-data migration remains a separate decision.
