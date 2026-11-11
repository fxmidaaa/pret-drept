"""Select a completed scraper snapshot as the current DVC input."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def validate_snapshot(content: bytes, manifest: dict) -> int:
    if manifest["status"] != "complete":
        raise ValueError("Use a completed scraper snapshot.")
    if hashlib.sha256(content).hexdigest() != manifest["csv_sha256"]:
        raise ValueError("The CSV differs from its scraper snapshot manifest.")
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    rows = sum(1 for row in reader if row) - 1  # Exclude the header and blank lines.
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
    output.mkdir(parents=True, exist_ok=True)
    # Replace filenames rather than writing through a possible DVC cache link.
    for name, data in (("listings.csv", content), ("snapshot.json", manifest)):
        temporary = output / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.chmod(0o600)
        temporary.replace(output / name)
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
