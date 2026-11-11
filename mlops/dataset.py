"""Select a completed scraper snapshot as the current DVC input."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from mlops.files import atomic_output


def validate_snapshot(content: bytes, manifest: dict) -> int:
    if manifest["status"] != "complete":
        raise ValueError("Use a completed scraper snapshot.")
    if hashlib.sha256(content).hexdigest() != manifest["csv_sha256"]:
        raise ValueError("The CSV differs from its scraper snapshot manifest.")
    rows = (
        sum(bool(row) for row in csv.reader(io.StringIO(content.decode("utf-8-sig"))))
        - 1
    )
    if rows < 1 or rows != manifest["saved_rows"]:
        raise ValueError(
            "The CSV row count differs from its scraper snapshot manifest."
        )
    return rows


def stage_dataset(snapshot: Path, output: Path = Path("data/dataset")) -> None:
    if snapshot.resolve() == output.resolve():
        raise ValueError(
            "Keep the scraper archive separate from the current DVC input."
        )
    content = (snapshot / "listings.csv").read_bytes()
    manifest = (snapshot / "snapshot.json").read_bytes()
    rows = validate_snapshot(content, json.loads(manifest))
    # Replace copies atomically; never edit a file linked to DVC's cache in place.
    for name, data in (("listings.csv", content), ("snapshot.json", manifest)):
        with atomic_output(output / name) as temporary:
            temporary.write_bytes(data)
    print(f"Selected {rows} original rows from {snapshot} into {output}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select a completed raw snapshot for DVC."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Directory containing listings.csv and snapshot.json.",
    )
    parser.add_argument("--output", type=Path, default=Path("data/dataset"))
    args = parser.parse_args()
    stage_dataset(args.snapshot, args.output)


if __name__ == "__main__":
    main()
