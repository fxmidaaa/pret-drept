import csv
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

import scrape

FIRST = "0000000000000001"
SECOND = "abcdef0123456789"


def row(key):
    return {
        "listing_key": key,
        "first_seen": "2026-10-01",
        "last_seen": "2026-10-01",
        "price_value": "500.00",
        "Sector": "NA",
        "Textul anunțului": 'synthetic text, with "quotes"\nand a newline',
    }


def write_csv(path, rows):
    pd.DataFrame(rows.values()).to_csv(path, index=False, encoding="utf-8-sig")


@pytest.fixture(autouse=True)
def checkpoint(tmp_path, monkeypatch):
    path = tmp_path / "listings.csv"
    monkeypatch.setattr(scrape, "CSV_PATH", str(path))

    def block_network(*args, **kwargs):
        pytest.fail("checkpoint tests must not access the network")

    monkeypatch.setattr(scrape.requests, "post", block_network)
    return path


def test_legacy_schema_is_rejected_without_modifying_the_file(checkpoint):
    original = b"id,price_value\nsynthetic-1,500\nsynthetic-2,600\n"
    checkpoint.write_bytes(original)

    with pytest.raises(ValueError, match="listing_key"):
        scrape.load_checkpoint()

    assert checkpoint.read_bytes() == original


def test_main_rejects_incompatible_checkpoint_before_fetch(checkpoint, monkeypatch):
    original = b"id,price_value\nsynthetic-1,500\n"
    checkpoint.write_bytes(original)

    def reject_fetch(*args, **kwargs):
        pytest.fail("checkpoint validation must happen before collection")

    monkeypatch.setattr(scrape, "fetch_ids_on_page", reject_fetch)
    with pytest.raises(ValueError, match="listing_key"):
        scrape.main()
    assert checkpoint.read_bytes() == original


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"listing_key\ninvalid-key\n",
        f"listing_key,Sector\n{FIRST},centru\n,botanica\n".encode(),
        f"listing_key\n{FIRST}\n{FIRST}\n".encode(),
        f"listing_key,listing_key\n{FIRST},{SECOND}\n".encode(),
        f"listing_key,\n{FIRST},value\n".encode(),
        f"listing_key\n{FIRST},extra\n".encode(),
        f"listing_key,Sector\n{FIRST}\n".encode(),
        f'listing_key,Sector\n"{FIRST},centru\n'.encode(),
        b"listing_key,Sector\n0000000000000001,\xff\n",
    ],
    ids=[
        "empty",
        "invalid-key",
        "missing-key",
        "duplicate-key",
        "duplicate-column",
        "blank-column",
        "extra-cell",
        "missing-cell",
        "unclosed-quote",
        "invalid-utf8",
    ],
)
def test_invalid_checkpoint_is_never_silently_reduced(checkpoint, payload):
    checkpoint.write_bytes(payload)
    with pytest.raises(ValueError):
        scrape.load_checkpoint()
    assert checkpoint.read_bytes() == payload


def test_missing_checkpoint_initializes_without_creating_files(tmp_path):
    path = tmp_path / "not-created" / "listings.csv"
    assert scrape.load_checkpoint(path) == {}
    assert not path.parent.exists()


def test_header_only_checkpoint_is_valid_empty_state(checkpoint):
    checkpoint.write_bytes(b"listing_key\n")
    assert scrape.load_checkpoint() == {}
    assert checkpoint.read_bytes() == b"listing_key\n"


def test_checkpoint_round_trip_preserves_keys_population_and_cell_text(checkpoint):
    rows = {FIRST: row(FIRST), SECOND: row(SECOND)}
    write_csv(checkpoint, rows)
    assert scrape.load_checkpoint() == rows
    scrape.save_checkpoint(rows)
    assert scrape.load_checkpoint() == rows
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_explicit_checkpoint_path_does_not_write_the_default(checkpoint, tmp_path):
    path = tmp_path / "separate" / "progress.csv"
    rows = {FIRST: row(FIRST)}
    scrape.save_checkpoint(rows, path)
    assert scrape.load_checkpoint(path) == rows
    assert not checkpoint.exists()


def test_empty_checkpoint_save_is_readable(checkpoint):
    scrape.save_checkpoint({})
    assert scrape.load_checkpoint() == {}


def test_long_cell_round_trip_restores_the_process_csv_limit(checkpoint):
    previous_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(64)
        rows = {FIRST: {**row(FIRST), "Textul anunțului": "synthetic text " * 100}}
        scrape.save_checkpoint(rows)
        assert scrape.load_checkpoint() == rows
        assert csv.field_size_limit() == 64
    finally:
        csv.field_size_limit(previous_limit)


@pytest.mark.parametrize("failure", ["write", "fsync", "replace"])
def test_failed_save_preserves_previous_bytes_and_cleans_temporary_files(
    checkpoint, monkeypatch, failure
):
    write_csv(checkpoint, {FIRST: row(FIRST)})
    original = checkpoint.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("simulated checkpoint failure")

    if failure == "write":

        def partial_write(frame, stream, **kwargs):
            stream.write("partial output")
            fail()

        monkeypatch.setattr(pd.DataFrame, "to_csv", partial_write)
    else:
        monkeypatch.setattr(scrape.os, failure, fail)

    with pytest.raises(OSError, match="simulated checkpoint failure"):
        scrape.save_checkpoint({FIRST: row(FIRST), SECOND: row(SECOND)})

    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_incomplete_serialized_population_is_not_published(checkpoint, monkeypatch):
    write_csv(checkpoint, {FIRST: row(FIRST)})
    original = checkpoint.read_bytes()
    writer = pd.DataFrame.to_csv

    def omit_last_row(frame, stream, **kwargs):
        writer(frame.iloc[:1], stream, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", omit_last_row)
    with pytest.raises(ValueError, match="population"):
        scrape.save_checkpoint({FIRST: row(FIRST), SECOND: row(SECOND)})
    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_serialized_column_loss_is_not_published(checkpoint, monkeypatch):
    write_csv(checkpoint, {FIRST: row(FIRST)})
    original = checkpoint.read_bytes()
    writer = pd.DataFrame.to_csv

    def omit_optional_columns(frame, stream, **kwargs):
        writer(frame[["listing_key"]], stream, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", omit_optional_columns)
    with pytest.raises(ValueError, match="schema"):
        scrape.save_checkpoint({FIRST: row(FIRST), SECOND: row(SECOND)})
    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


@pytest.mark.parametrize(
    "rows",
    [{SECOND: row(FIRST)}, {FIRST: row(FIRST), SECOND: row(FIRST)}, {}],
    ids=["key-mismatch", "duplicate-record", "dropped-existing-record"],
)
def test_invalid_new_state_preserves_existing_checkpoint(checkpoint, rows):
    write_csv(checkpoint, {FIRST: row(FIRST)})
    original = checkpoint.read_bytes()
    with pytest.raises(ValueError):
        scrape.save_checkpoint(rows)
    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_save_also_refuses_an_incompatible_existing_destination(checkpoint):
    original = b"id,price_value\nsynthetic-1,500\n"
    checkpoint.write_bytes(original)
    with pytest.raises(ValueError, match="listing_key"):
        scrape.save_checkpoint({FIRST: row(FIRST)})
    assert checkpoint.read_bytes() == original


@pytest.mark.parametrize("operation", ["load", "save"])
def test_symlink_checkpoint_is_rejected_without_changing_its_target(
    checkpoint, tmp_path, operation
):
    target = tmp_path / "original.csv"
    write_csv(target, {FIRST: row(FIRST)})
    original = target.read_bytes()
    checkpoint.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        if operation == "load":
            scrape.load_checkpoint()
        else:
            scrape.save_checkpoint({FIRST: row(FIRST)})
    assert target.read_bytes() == original
    assert checkpoint.is_symlink()


def test_main_resumes_existing_records_and_saves_new_records(checkpoint, monkeypatch):
    existing = row(scrape.listing_key("synthetic-existing"))
    write_csv(checkpoint, {existing["listing_key"]: existing})
    fetched = []

    def fetch_details(identifier):
        fetched.append(identifier)
        return {
            **row(scrape.listing_key(identifier)),
            "Tipul ofertei": "De închiriat lunar",
            "Regiune": "Chișinău",
        }

    monkeypatch.setattr(scrape, "TODAY", "2026-11-02")
    monkeypatch.setattr(
        scrape, "fetch_ids_on_page", lambda skip: (2, ["synthetic-existing", "synthetic-new"])
    )
    monkeypatch.setattr(scrape, "fetch_listing_details", fetch_details)
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    scrape.main()

    restored = scrape.load_checkpoint()
    assert set(restored) == {existing["listing_key"], scrape.listing_key("synthetic-new")}
    assert fetched == ["synthetic-new"]
    assert restored[existing["listing_key"]]["first_seen"] == "2026-10-01"
    assert restored[existing["listing_key"]]["last_seen"] == "2026-11-02"
    assert restored[existing["listing_key"]]["Textul anunțului"] == existing["Textul anunțului"]


def test_cli_help_documents_the_path_without_reading_a_checkpoint(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scrape.py", "--help"])

    def reject_file_access(*args, **kwargs):
        pytest.fail("--help must not read a checkpoint")

    monkeypatch.setattr(Path, "open", reject_file_access)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(scrape.__file__, run_name="__main__")
    assert result.value.code == 0
    assert "--checkpoint" in capsys.readouterr().out
