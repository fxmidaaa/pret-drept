"""Score prepared listings with local Spark workers and the shared predictor."""

import argparse
import os
import sys
from collections.abc import Iterator
from functools import partial
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from features import categorical
from predict import configured_model_path, load_bundle, model_matrix, predict_eur

REQUIRED_COLUMNS = {"rooms", "area", "sector", "author"}
PREDICTION_COLUMN = "predicted_rent_eur"
WORKERS = 2


def predict_batches(
    batches: Iterator[pd.DataFrame], *, bundle: dict
) -> Iterator[pd.DataFrame]:
    for batch in batches:
        if batch.empty:
            continue
        valid_rows = (
            batch["rooms"].between(1, 6)
            & batch["area"].between(10, 400)
            & batch["sector"].fillna("").str.strip().ne("")
            & batch["author"].fillna("").str.strip().ne("")
        )
        if not valid_rows.all():
            raise ValueError(
                "Each listing needs 1–6 rooms, 10–400 m², a sector and an author."
            )

        matrix = model_matrix(batch.to_dict(orient="records"), bundle)
        scored = batch.copy()
        scored[PREDICTION_COLUMN] = predict_eur(matrix, bundle).astype(float)
        yield scored


def score_csv(source: Path, output: Path, model: Path) -> None:
    source = source.expanduser().resolve()
    model = model.expanduser()
    output = output.expanduser().absolute()
    if not source.is_file() or not model.is_file():
        raise ValueError("Expected a local input CSV and a trusted model file.")
    if output.exists(follow_symlinks=False):
        raise FileExistsError(
            f"Choose a new output directory. {output} already exists."
        )

    # Spark serializes this bundle with the worker function, once per task.
    bundle = load_bundle(model)
    os.environ["PYSPARK_PYTHON"] = sys.executable
    spark = (
        SparkSession.builder.appName("pret-drept-batch")
        .master(f"local[{WORKERS}]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.execution.arrow.maxRecordsPerBatch", 1024)
        .getOrCreate()
    )
    try:
        spark.sparkContext.setLogLevel("WARN")
        raw = spark.read.csv(
            str(source), header=True, mode="FAILFAST", multiLine=True, escape='"'
        )
        missing = REQUIRED_COLUMNS.difference(raw.columns)
        if missing:
            raise ValueError(
                f"Missing prepared feature columns: {', '.join(sorted(missing))}"
            )
        columns = [
            F.col(name)
            if name in categorical
            else F.col(name).cast("double").alias(name)
            for name in bundle["features"]
            if name in raw.columns
        ]
        if "listing_key" in raw.columns:
            columns.insert(0, F.col("listing_key"))
        inputs = raw.select(*columns)
        if inputs.isEmpty():
            raise ValueError("The input CSV has no listings to score.")

        schema = inputs.schema.add(PREDICTION_COLUMN, "double", nullable=False)
        scores = inputs.repartition(WORKERS).mapInPandas(
            partial(predict_batches, bundle=bundle), schema
        )
        # Spark's _SUCCESS marker identifies a finished output directory.
        scores.write.csv(str(output), header=True, mode="error")
    finally:
        spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a local prepared CSV with PySpark."
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Prepared listing features CSV."
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory for scored CSV parts."
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=configured_model_path(),
        help="Trusted bundle. Defaults to PRET_DREPT_MODEL or model.joblib.",
    )
    args = parser.parse_args()
    score_csv(args.input, args.output, args.model)
    print(f"Wrote batch predictions to {args.output}.")


if __name__ == "__main__":
    main()
