"""Fixed v1 Parquet profile and lossless observation encoding."""

import math
import os
from contextlib import contextmanager
from itertools import batched

from rent_contracts import ContractError
from rent_contracts.inventory import PYARROW_VERSION

MAX_BATCH_ROWS = 2_048
MAX_ROW_GROUPS = 4_096
MAX_FOOTER_BYTES = 8 * 1024 * 1024


def _backend():
    try:
        import pyarrow
        import pyarrow.parquet
    except ImportError:
        raise ContractError(
            "inventory Parquet backend unavailable; install the parquet extra"
        ) from None
    if pyarrow.__version__ != PYARROW_VERSION:
        raise ContractError("inventory Parquet backend version mismatch")
    return pyarrow, pyarrow.parquet


def _schema(arrow):
    string = arrow.string()
    field = arrow.field
    identity = arrow.struct(
        [
            field("policy_ref", string, nullable=False),
            field("status", string, nullable=False),
            field("property_id", string),
            field("confidence", arrow.float64()),
            field("confidence_is_integer", arrow.bool_()),
        ]
    )
    return arrow.schema(
        [
            field("contract_version", string, nullable=False),
            field("observation_id", string, nullable=False),
            field("listing_id", string, nullable=False),
            field("property_identity", identity, nullable=False),
            field("domain_policy_ref", string, nullable=False),
            field("domain_status", string, nullable=False),
            field("published_at", string),
            field("collected_at", string),
            field("features_available_at", string),
            field("prediction_cutoff_at", string),
            field("temporal_evidence_ref", string),
        ]
    )


def _input_rows(observations):
    try:
        yield from observations
    except Exception:
        # A caller's source iterator can include its raw records in errors.
        raise ContractError("inventory observation source failed") from None


def _encoded_rows(observations, inventory):
    for observation in _input_rows(observations):
        inventory.add(observation)
        identity = observation["property_identity"]
        confidence = identity["confidence"]
        yield {
            **observation,
            "property_identity": {
                **identity,
                "confidence": None if confidence is None else float(confidence),
                "confidence_is_integer": None if confidence is None else type(confidence) is int,
            },
        }


def write_parquet(sink, observations, *, inventory, batch_rows: int) -> None:
    arrow, parquet = _backend()
    schema = _schema(arrow)
    try:
        with parquet.ParquetWriter(
            sink,
            schema,
            version="2.6",
            compression="NONE",
            use_dictionary=False,
            write_statistics=False,
            data_page_version="1.0",
            write_batch_size=512,
            max_rows_per_page=512,
            data_page_size=65_536,
            store_schema=False,
            write_page_index=False,
            write_page_checksum=True,
        ) as writer:
            rows = _encoded_rows(observations, inventory)
            for number, batch in enumerate(batched(rows, batch_rows), start=1):
                if number > MAX_ROW_GROUPS:
                    raise ContractError("inventory Parquet row group limit exceeded")
                table = arrow.Table.from_pylist(batch, schema=schema)
                writer.write_table(table, row_group_size=batch_rows)
    except ContractError:
        raise
    except (arrow.ArrowException, OSError, TypeError, ValueError, OverflowError):
        raise ContractError("inventory Parquet write failed") from None


def _footer_start(stream, size_bytes: int) -> int:
    stream.seek(0)
    if stream.read(4) != b"PAR1":
        raise ContractError("invalid inventory Parquet framing")
    stream.seek(-8, os.SEEK_END)
    trailer = stream.read(8)
    footer_bytes = int.from_bytes(trailer[:4], "little")
    start = size_bytes - 8 - footer_bytes
    if trailer[4:] != b"PAR1" or not 0 < footer_bytes <= MAX_FOOTER_BYTES or start <= 4:
        raise ContractError("invalid or oversized inventory Parquet footer")
    stream.seek(0)
    return start


def _validate_layout(reader, schema, *, footer_start: int, observation_count: int) -> None:
    metadata = reader.metadata
    if (
        metadata.format_version != "2.6"
        or metadata.created_by != f"parquet-cpp-arrow version {PYARROW_VERSION}"
        or metadata.metadata is not None
        or not reader.schema_arrow.equals(schema, check_metadata=True)
    ):
        raise ContractError("inventory Parquet schema or profile mismatch")
    if metadata.num_rows != observation_count or not 0 < metadata.num_row_groups <= MAX_ROW_GROUPS:
        raise ContractError("inventory Parquet count or row group limit mismatch")
    next_offset = 4
    group_rows = 0
    for index in range(metadata.num_row_groups):
        group = metadata.row_group(index)
        group_rows += group.num_rows
        if not 0 < group.num_rows <= MAX_BATCH_ROWS or group_rows > observation_count:
            raise ContractError("inventory Parquet row group count mismatch")
        for column_index in range(group.num_columns):
            column = group.column(column_index)
            size = column.total_compressed_size
            if (
                column.file_path
                or column.compression != "UNCOMPRESSED"
                or not set(column.encodings) <= {"PLAIN", "RLE"}
                or column.has_dictionary_page
                or column.is_stats_set
                or column.has_column_index
                or column.has_offset_index
                or column.data_page_offset != next_offset
                or size != column.total_uncompressed_size
                or not 0 < size <= footer_start - next_offset
            ):
                raise ContractError("inventory Parquet column layout mismatch")
            next_offset += size
    if group_rows != observation_count or next_offset != footer_start:
        raise ContractError("inventory Parquet layout totals mismatch")


@contextmanager
def open_parquet(stream, *, size_bytes: int, observation_count: int):
    arrow, parquet = _backend()
    try:
        footer_start = _footer_start(stream, size_bytes)
        with parquet.ParquetFile(
            stream,
            memory_map=False,
            pre_buffer=False,
            thrift_string_size_limit=1_024,
            thrift_container_size_limit=MAX_ROW_GROUPS,
            schema_depth_limit=4,
            page_checksum_verification=True,
            arrow_extensions_enabled=False,
        ) as reader:
            _validate_layout(
                reader,
                _schema(arrow),
                footer_start=footer_start,
                observation_count=observation_count,
            )
            yield reader
    except ContractError:
        raise
    except (arrow.ArrowException, OSError, ValueError, OverflowError):
        raise ContractError("inventory Parquet read failed") from None


def decoded_observations(reader, *, batch_rows: int):
    for batch in reader.iter_batches(batch_size=batch_rows, use_threads=False):
        for observation in batch.to_pylist():
            identity = observation["property_identity"]
            if identity is None:
                raise ContractError("invalid inventory Parquet property identity")
            integer = identity.pop("confidence_is_integer")
            confidence = identity["confidence"]
            if (integer is None) != (confidence is None):
                raise ContractError("invalid inventory Parquet confidence representation")
            if integer:
                if confidence not in (0.0, 1.0) or math.copysign(1.0, confidence) < 0:
                    raise ContractError("invalid inventory Parquet integer confidence")
                identity["confidence"] = int(confidence)
            yield observation
