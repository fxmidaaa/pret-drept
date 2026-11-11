"""Clean one listing CSV and save a grouped training/evaluation split."""

import argparse
import io
import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

import features
from mlops.dataset import validate_snapshot

GROUP_COLUMNS = ["sector", "rooms", "area", "floor", "total_floors"]
PREPARED_COLUMNS = [
    name for name in features.MODEL_FEATURES if name not in {"is_ground", "is_top"}
] + ["price"]
REQUIRED_COLUMNS = {
    "price_value",
    "price_unit",
    features.ROOMS_COL,
    features.AREA_COL,
    features.SECTOR_COL,
    features.AUTHOR_COL,
}


def prepare(
    source: Path,
    output: Path,
    config: dict,
    *,
    synthetic: bool = False,
    snapshot: Path | None = None,
) -> None:
    outputs = [
        output / name for name in ("train.csv", "evaluation.csv", "dataset.json")
    ]
    if source.resolve() in {path.resolve() for path in outputs}:
        raise ValueError(
            "Choose an output directory that does not overwrite the input CSV."
        )

    # Validate and hash the same input bytes. Only prepared features are saved below.
    content = source.read_bytes()
    if snapshot is not None:
        if synthetic:
            raise ValueError("A scraper snapshot cannot be labelled synthetic.")
        validate_snapshot(content, json.loads(snapshot.read_text()))
    raw = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(
            f"Missing required listing columns: {', '.join(sorted(missing))}"
        )
    raw_rows = len(raw)
    cleaned = features.clean_data(raw, deduplicate=False)[PREPARED_COLUMNS].copy()
    floor = cleaned["floor"]
    total = cleaned["total_floors"]
    valid_floors = floor.between(1, 50) & total.between(1, 50) & (floor <= total)
    # Treat an invalid floor pair as unknown. Serving uses the same floor-flag rule.
    cleaned.loc[~valid_floors, ["floor", "total_floors"]] = np.nan
    clean_rows = len(cleaned)
    cleaned = cleaned.drop_duplicates()

    # Reposts with the same coarse apartment key stay together even when asking rent changes.
    group_keys = pd.util.hash_pandas_object(
        cleaned[GROUP_COLUMNS].fillna({"floor": -1, "total_floors": -1}), index=False
    )
    if group_keys.nunique() < 20:
        raise ValueError(
            "Need at least 20 distinct apartment keys after cleaning to split the data."
        )
    split = GroupShuffleSplit(
        n_splits=1,
        test_size=config["evaluation_fraction"],
        random_state=config["seed"],
    )
    train_indices, eval_indices = next(split.split(cleaned, groups=group_keys))
    train = cleaned.iloc[train_indices]
    evaluation = cleaned.iloc[eval_indices]
    output.mkdir(parents=True, exist_ok=True)
    # Unlink generated files first so direct writes cannot change DVC's cached copies.
    for path in outputs:
        path.unlink(missing_ok=True)
    train.to_csv(output / "train.csv", index=False, lineterminator="\n")
    evaluation.to_csv(output / "evaluation.csv", index=False, lineterminator="\n")

    manifest = {
        "dataset": "synthetic" if synthetic else "private",
        "input_sha256": sha256(content).hexdigest(),
        "input_rows": raw_rows,
        "excluded_rows": raw_rows - clean_rows,
        "duplicate_rows": clean_rows - len(cleaned),
        "training_rows": len(train),
        "evaluation_rows": len(evaluation),
        "training_sha256": sha256((output / "train.csv").read_bytes()).hexdigest(),
        "evaluation_sha256": sha256(
            (output / "evaluation.csv").read_bytes()
        ).hexdigest(),
        "split": {
            "strategy": "group_shuffle",
            "seed": config["seed"],
            "evaluation_fraction": config["evaluation_fraction"],
            "group_columns": GROUP_COLUMNS,
        },
    }
    (output / "dataset.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"Prepared {len(train)} training rows and {len(evaluation)} evaluation rows in {output}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a local legacy listing CSV.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, default=Path("params.json"))
    parser.add_argument(
        "--snapshot", type=Path, help="Validate the raw CSV against its snapshot.json."
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="Label generated demo data."
    )
    args = parser.parse_args()
    prepare(
        args.source,
        args.output,
        json.loads(args.config.read_text(encoding="utf-8")),
        synthetic=args.synthetic,
        snapshot=args.snapshot,
    )


if __name__ == "__main__":
    main()
