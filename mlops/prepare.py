import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

import features
from mlops.config import Config, load_config
from mlops.dataset import validate_snapshot
from mlops.files import atomic_output, sha256, write_json

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
INPUT_COLUMNS = REQUIRED_COLUMNS | {
    source
    for name, (source, _) in features.COLUMN_PARSERS.items()
    if name in features.MODEL_FEATURES
}


def prepare(
    source: Path,
    output: Path,
    config: Config,
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

    # Read and hash the same bytes. Materialize only the columns used by the model.
    content = source.read_bytes()
    if snapshot is not None:
        if synthetic:
            raise ValueError("A scraper snapshot cannot be labelled synthetic.")
        validate_snapshot(content, json.loads(snapshot.read_text()))
    input_sha256 = hashlib.sha256(content).hexdigest()
    raw = pd.read_csv(
        io.BytesIO(content),
        encoding="utf-8-sig",
        dtype=str,
        usecols=lambda name: name in INPUT_COLUMNS,
    )
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
        n_splits=1, test_size=config.evaluation_fraction, random_state=config.seed
    )
    train_indices, eval_indices = next(split.split(cleaned, groups=group_keys))
    train = cleaned.iloc[train_indices]
    evaluation = cleaned.iloc[eval_indices]
    for frame, path in zip((train, evaluation), outputs[:2], strict=True):
        with atomic_output(path) as temporary:
            frame.to_csv(temporary, index=False, lineterminator="\n")

    write_json(
        outputs[2],
        {
            "dataset": "synthetic" if synthetic else "private",
            "input_sha256": input_sha256,
            "input_rows": raw_rows,
            "excluded_rows": raw_rows - clean_rows,
            "duplicate_rows": clean_rows - len(cleaned),
            "training_rows": len(train),
            "evaluation_rows": len(evaluation),
            "training_sha256": sha256(outputs[0]),
            "evaluation_sha256": sha256(outputs[1]),
            "split": {
                "strategy": "group_shuffle",
                "seed": config.seed,
                "evaluation_fraction": config.evaluation_fraction,
                "group_columns": GROUP_COLUMNS,
            },
        },
    )
    print(
        f"Prepared {len(train)} training rows and {len(evaluation)} evaluation rows in {output}."
    )


def read_partition(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        dtype={name: str for name in features.categorical},
    )
    if list(frame.columns) != PREPARED_COLUMNS or len(frame) < 2:
        raise ValueError(f"Invalid partition at {path}. Run preparation again.")
    if not frame["price"].between(100, 2000).all():
        raise ValueError(
            f"Expected monthly EUR targets between 100 and 2000 in {path}."
        )
    return frame


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
        load_config(args.config),
        synthetic=args.synthetic,
        snapshot=args.snapshot,
    )


if __name__ == "__main__":
    main()
