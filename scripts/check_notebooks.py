"""Check that tracked notebooks contain source without saved output."""

import json
import os
import subprocess
import sys
from pathlib import Path


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document = dict(pairs)
    if len(document) != len(pairs):
        raise ValueError("duplicate notebook JSON key")
    return document


def _notebook_issue(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return "expected a regular notebook file"
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError, RecursionError):
        return "unreadable or invalid notebook JSON"

    if (
        not isinstance(notebook, dict)
        or notebook.get("nbformat") != 4
        or not isinstance(notebook.get("cells"), list)
        or not isinstance(notebook.get("metadata"), dict)
    ):
        return "expected a v4 notebook with cells and metadata"
    if notebook["metadata"].get("widgets", {}) != {}:
        return "saved widget state"

    for number, cell in enumerate(notebook["cells"], start=1):
        if not isinstance(cell, dict) or cell.get("cell_type") not in ("code", "markdown", "raw"):
            return f"cell {number} has an invalid structure"
        if cell.get("outputs", []) != []:
            return f"cell {number} has saved output"
        if cell.get("execution_count") is not None:
            return f"cell {number} has a saved execution count"
        if cell.get("attachments", {}) != {}:
            return f"cell {number} has embedded attachments"
    return None


def check_notebooks(root: Path) -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "*.ipynb"], cwd=root)
    paths = [os.fsdecode(path) for path in tracked.split(b"\0") if path]
    failed = False
    for path in paths:
        issue = _notebook_issue(root / path)
        if issue:
            print(f"{path!a}: {issue}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"Notebook publication check passed ({len(paths)} tracked notebooks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_notebooks(Path(__file__).resolve().parents[1]))
