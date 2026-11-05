# RP-20261104-A06 task record storage limit

The user approved option 1 on `fix/repository-audit` at `d11304a`. This L1 change covers task record persistence, focused tests and developer guidance under architecture §6. Preserve the existing local A03–A05 evidence.

1. Keep indented UTF-8 JSON with a final newline. Use the existing 1 MiB contract limit for both the bounded read and the bytes written by the atomic writer.
2. Reject an oversized serialization before creating output or replacing an existing record. A synthetic record at the limit must round-trip. A contract-valid record one byte over must leave the previous file intact. Use multibyte text so the tests distinguish bytes from characters.
3. Run the focused tests, full suite, source checks and architecture command. Record evidence and review the local patch. Publication requires separate approval.

## Verification

The one-byte-over regression failed before the change because saving succeeded. After the change, the writer rejects the oversized serialization and preserves the exact bytes of the prior record. The at-limit case round-trips and the reader rejects that same file with one additional newline. Both fixtures include multibyte UTF-8 text.

| Check | Result |
| --- | --- |
| Task record tests | 23 passed |
| Full local suite | 233 passed, zero failed or skipped, one existing Starlette warning |
| Source checks | Ruff lint and format, pinned actionlint, architecture CLI and whitespace checks passed |
| Preservation | All six pre-existing evidence files match their pre-edit digests |
| Remote CI | Passed for 894a016. 221 passed, 12 skipped because the private model is absent, one test warning. [Run 41728652619](https://github.com/fxmidaaa/pret-drept/actions/runs/41728652619) |

Run `.venv/bin/python -m pytest -p no:cacheprovider -q tests/foundations/test_tasks.py` for the focused regressions and the commands in the development guide for the full check set. The full run used `PYTHONDONTWRITEBYTECODE=1` and Matplotlib and Numba caches under `/private/tmp/pret-drept-a06-20261104`.

Recovery: Confirm `fix/repository-audit` at `894a01675425bcf1e8cf05bab28dd42a47b419af`. Preserve the local A03–A06 evidence. Publication of evidence updates requires separate approval.

The user approved publication by asking to push. Publish the five A06 files to `fix/repository-audit` with message `fix(tasks): enforce the storage byte limit before saving`. Verify CI for the published commit.

GitHub confirmed `894a016` on `fix/repository-audit`. The foundations job passed workflow validation, static checks, dependency checks, tests and the distribution build. The test log reported 221 passes and 12 private-model skips in 3.45 seconds. [Run 41728652619](https://github.com/fxmidaaa/pret-drept/actions/runs/41728652619)
