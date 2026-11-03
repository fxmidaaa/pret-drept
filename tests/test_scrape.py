import csv
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

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


def advert(identifier, **fields):
    return {
        "advert": {
            "id": identifier,
            "groups": [
                {
                    "controls": [
                        {"title": name, "feature": {"value": value}}
                        for name, value in fields.items()
                    ]
                }
            ],
        }
    }


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


@pytest.mark.parametrize("column", ["Contacte", "sector"])
@pytest.mark.parametrize("has_row", [False, True], ids=["header-only", "with-row"])
def test_unexpected_checkpoint_columns_are_rejected_without_modification(
    checkpoint, column, has_row
):
    original = f"listing_key,{column}\n"
    if has_row:
        original += f"{FIRST},synthetic-private-value\n"
    original = original.encode()
    checkpoint.write_bytes(original)
    with pytest.raises(scrape.CheckpointError, match="unexpected columns") as error:
        scrape.load_checkpoint()
    assert checkpoint.read_bytes() == original
    assert column not in str(error.value)
    assert "synthetic-private-value" not in str(error.value)


@pytest.mark.parametrize("existing", [False, True], ids=["new-path", "existing-checkpoint"])
def test_unexpected_save_fields_are_rejected_before_creating_output(checkpoint, tmp_path, existing):
    path = checkpoint if existing else tmp_path / "not-created" / "listings.csv"
    rows = {FIRST: row(FIRST)}
    if existing:
        write_csv(path, rows)
    original = path.read_bytes() if existing else None
    rows[SECOND] = {**row(SECOND), "Contacte": "synthetic-private-value"}
    with pytest.raises(scrape.CheckpointError, match="unexpected columns") as error:
        scrape.save_checkpoint(rows, path)
    assert rows[SECOND]["Contacte"] == "synthetic-private-value"
    assert "Contacte" not in str(error.value)
    assert "synthetic-private-value" not in str(error.value)
    if existing:
        assert path.read_bytes() == original
        assert set(path.parent.iterdir()) == {path}
    else:
        assert not path.parent.exists()


def test_unexpected_checkpoint_columns_stop_collection_before_fetch(checkpoint, monkeypatch):
    original = f"listing_key,Contacte\n{FIRST},synthetic-private-value\n".encode()
    checkpoint.write_bytes(original)

    def reject_fetch(*args, **kwargs):
        pytest.fail("column validation must happen before collection")

    monkeypatch.setattr(scrape, "fetch_ids_on_page", reject_fetch)
    with pytest.raises(scrape.CheckpointError, match="unexpected columns"):
        scrape.main()
    assert checkpoint.read_bytes() == original


@pytest.mark.parametrize("has_row", [False, True], ids=["header-only", "with-row"])
def test_save_refuses_unexpected_columns_in_existing_destination(checkpoint, has_row):
    original = "listing_key,Contacte\n"
    if has_row:
        original += f"{FIRST},synthetic-private-value\n"
    original = original.encode()
    checkpoint.write_bytes(original)
    with pytest.raises(scrape.CheckpointError, match="unexpected columns"):
        scrape.save_checkpoint({FIRST: row(FIRST)})
    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_all_approved_columns_round_trip_without_loss(checkpoint):
    approved = {
        name: f"synthetic-{index}"
        for index, name in enumerate(scrape.FEATURE_FIELDS + scrape.FILTER_FIELDS)
    }
    approved.update(row(FIRST), price_unit="UNIT_EUR")
    write_csv(checkpoint, {FIRST: approved})
    assert scrape.load_checkpoint() == {FIRST: approved}
    scrape.save_checkpoint({FIRST: approved})
    assert scrape.load_checkpoint() == {FIRST: approved}


def test_serialized_unexpected_column_cannot_replace_checkpoint(checkpoint, monkeypatch):
    write_csv(checkpoint, {FIRST: row(FIRST)})
    original = checkpoint.read_bytes()
    writer = pd.DataFrame.to_csv

    def inject_column(frame, stream, **kwargs):
        writer(frame.assign(Contacte="synthetic-private-value"), stream, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", inject_column)
    with pytest.raises(scrape.CheckpointError, match="unexpected columns"):
        scrape.save_checkpoint({FIRST: row(FIRST), SECOND: row(SECOND)})
    assert checkpoint.read_bytes() == original
    assert set(checkpoint.parent.iterdir()) == {checkpoint}


def test_collection_drops_unapproved_controls_before_persistence(checkpoint, monkeypatch):
    identifier = "synthetic-approved"

    def query(query, variables):
        if query == scrape.SEARCH_QUERY:
            return {"searchAds": {"count": 1, "ads": [{"id": identifier}]}}
        return advert(
            identifier,
            **{
                "Tipul ofertei": "De închiriat lunar",
                "Regiune": "Chișinău",
                "Preț": {"value": "500.00", "unit": "UNIT_EUR"},
                "Contacte": "synthetic-private-value",
                "unreviewed-field": "unneeded",
                "listing_key": "untrusted-source-key",
            },
        )

    monkeypatch.setattr(scrape, "gql", query)
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    scrape.main()
    restored = scrape.load_checkpoint()
    assert restored == {
        scrape.listing_key(identifier): {
            "listing_key": scrape.listing_key(identifier),
            "first_seen": scrape.TODAY,
            "last_seen": scrape.TODAY,
            "Tipul ofertei": "De închiriat lunar",
            "Regiune": "Chișinău",
            "price_value": "500.00",
            "price_unit": "UNIT_EUR",
        }
    }
    assert "synthetic-private-value" not in checkpoint.read_text(encoding="utf-8-sig")


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


def test_failed_listing_is_retried_on_the_next_run(checkpoint, monkeypatch):
    identifier = "synthetic-retry"
    outcomes = iter(
        [
            {"errors": [{"message": "sensitive synthetic error"}]},
            {
                "data": advert(
                    identifier,
                    **{
                        "Tipul ofertei": "De închiriat lunar",
                        "Regiune": "Chișinău",
                        "Preț": {"value": "500.00", "unit": "UNIT_EUR"},
                    },
                )
            },
        ]
    )
    fetched = []

    def post(*args, **kwargs):
        request = json.loads(kwargs["data"])
        if request["query"] == scrape.SEARCH_QUERY:
            payload = {"data": {"searchAds": {"count": 1, "ads": [{"id": identifier}]}}}
        else:
            fetched.append(request["variables"]["i"]["id"])
            payload = next(outcomes)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)

    monkeypatch.setattr(scrape.requests, "post", post)
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    with pytest.raises(scrape.AcquisitionError, match="Collection incomplete: 1"):
        scrape.main()
    assert scrape.load_checkpoint() == {}

    scrape.main()
    assert fetched == [identifier, identifier]
    assert scrape.load_checkpoint()[scrape.listing_key(identifier)]["price_value"] == "500.00"


def test_failed_search_is_not_normal_exhaustion(monkeypatch):
    monkeypatch.setattr(scrape, "gql", lambda *args: None)
    with pytest.raises(scrape.AcquisitionError, match="Search"):
        scrape.fetch_ids_on_page(0)


@pytest.mark.parametrize("failure", ["transport", "http", "json"])
def test_request_failures_are_bounded_and_do_not_echo_response_contents(
    monkeypatch, capsys, failure
):
    calls, sleeps = [], []

    def fail():
        if failure == "transport":
            raise scrape.requests.Timeout("sensitive synthetic exception")
        if failure == "http":
            raise scrape.requests.HTTPError("sensitive synthetic exception")
        raise ValueError("sensitive synthetic JSON")

    def post(*args, **kwargs):
        calls.append(kwargs)
        if failure == "transport":
            fail()
        return SimpleNamespace(
            raise_for_status=fail if failure == "http" else lambda: None,
            json=fail,
        )

    monkeypatch.setattr(scrape.requests, "post", post)
    monkeypatch.setattr(scrape.time, "sleep", sleeps.append)
    assert scrape.gql("synthetic query", {}) is None
    assert len(calls) == 3
    assert all(call["timeout"] == 25 for call in calls)
    assert sleeps == [3, 3]
    assert "sensitive" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"data": None},
        {"data": []},
        {"data": {"advert": {}}, "errors": [{"message": "sensitive synthetic error"}]},
    ],
)
def test_invalid_graphql_responses_are_failures(monkeypatch, capsys, payload):
    monkeypatch.setattr(
        scrape.requests,
        "post",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: payload,
        ),
    )
    assert scrape.gql("synthetic query", {}) is None
    assert "sensitive" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "result",
    [
        None,
        {},
        {"count": True, "ads": []},
        {"count": -1, "ads": []},
        {"count": 1, "ads": None},
        {"count": 1, "ads": [{}]},
        {"count": 1, "ads": [{"id": None}]},
        {"count": 1, "ads": []},
        {"count": 0, "ads": [{"id": "synthetic"}]},
    ],
)
def test_malformed_or_prematurely_empty_search_is_not_exhaustion(monkeypatch, result):
    monkeypatch.setattr(scrape, "gql", lambda *args: {"searchAds": result})
    with pytest.raises(scrape.AcquisitionError, match="Search"):
        scrape.fetch_ids_on_page(0)


def test_empty_successful_search_is_normal_exhaustion(checkpoint, monkeypatch, capsys):
    monkeypatch.setattr(scrape, "gql", lambda *args: {"searchAds": {"count": 0, "ads": []}})
    scrape.main()
    assert "done. checkpoint records:" in capsys.readouterr().out
    assert not checkpoint.exists()


def test_search_failure_after_a_page_preserves_progress_and_stops(checkpoint, monkeypatch, capsys):
    offsets = []

    def search(query, variables):
        offsets.append(variables["i"]["pagination"]["skip"])
        if len(offsets) == 1:
            return {"searchAds": {"count": 2, "ads": [{"id": "synthetic-kept"}]}}
        return None

    monkeypatch.setattr(scrape, "PAGE_SIZE", 1)
    monkeypatch.setattr(scrape, "gql", search)
    monkeypatch.setattr(
        scrape,
        "fetch_listing_details",
        lambda identifier: {
            **row(scrape.listing_key(identifier)),
            "Tipul ofertei": "De închiriat lunar",
            "Regiune": "Chișinău",
        },
    )
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    with pytest.raises(scrape.AcquisitionError, match="Collection incomplete: search"):
        scrape.main()
    assert offsets == [0, 1]
    assert set(scrape.load_checkpoint()) == {scrape.listing_key("synthetic-kept")}
    assert "done." not in capsys.readouterr().out


@pytest.mark.parametrize("failure", ["missing", "malformed", "eligibility", "identity", "control"])
def test_incomplete_detail_does_not_prevent_saving_other_rows(
    checkpoint, monkeypatch, capsys, failure
):
    fetched = []
    identifiers = ["synthetic-failed", "synthetic-kept", "synthetic-ineligible"]

    def query(query, variables):
        if query == scrape.SEARCH_QUERY:
            return {"searchAds": {"count": 3, "ads": [{"id": value} for value in identifiers]}}
        identifier = variables["i"]["id"]
        fetched.append(identifier)
        if identifier == "synthetic-failed":
            if failure == "missing":
                return {"advert": None}
            if failure == "malformed":
                return {"advert": {"id": identifier, "groups": "invalid"}}
            if failure == "identity":
                return advert("synthetic-wrong-listing")
            if failure == "control":
                return {"advert": {"id": identifier, "groups": [{"controls": [None]}]}}
            return advert(identifier)
        return advert(
            identifier,
            **{
                "Tipul ofertei": "De vânzare"
                if identifier.endswith("ineligible")
                else "De închiriat lunar",
                "Regiune": "Chișinău",
            },
        )

    monkeypatch.setattr(scrape, "gql", query)
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    for _ in range(2):
        with pytest.raises(scrape.AcquisitionError, match="Collection incomplete: 1"):
            scrape.main()
        restored = scrape.load_checkpoint()
        assert set(restored) == {scrape.listing_key(value) for value in identifiers[1:]}
        assert restored[scrape.listing_key("synthetic-ineligible")]["Tipul ofertei"] == "rejected"
    assert fetched == identifiers + ["synthetic-failed"]
    assert "done." not in capsys.readouterr().out


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"Tipul ofertei": None, "Regiune": "Chișinău"},
        {"Tipul ofertei": "De închiriat lunar", "Regiune": None},
        {"Tipul ofertei": "De închiriat lunar", "Regiune": {"invalid": "value"}},
    ],
)
def test_missing_or_invalid_eligibility_is_unresolved(fields):
    with pytest.raises(scrape.AcquisitionError, match="eligibility"):
        scrape.target_valid(fields)


@pytest.mark.parametrize("failure", ["search", "detail"])
def test_incomplete_cli_exits_nonzero_with_safe_diagnostics(
    checkpoint, monkeypatch, capsys, failure
):
    monkeypatch.setattr(sys, "argv", ["scrape.py", "--checkpoint", str(checkpoint)])

    def post(*args, **kwargs):
        request = json.loads(kwargs["data"])
        payload = {"errors": [{"message": "sensitive synthetic payload"}]}
        if failure == "detail" and request["query"] == scrape.SEARCH_QUERY:
            payload = {"data": {"searchAds": {"count": 1, "ads": [{"id": "synthetic"}]}}}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)

    monkeypatch.setattr(scrape.requests, "post", post)
    monkeypatch.setattr(scrape.time, "sleep", lambda seconds: None)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(scrape.__file__, run_name="__main__")
    assert result.value.code == 1
    captured = capsys.readouterr()
    assert "Collection incomplete:" in captured.err
    assert "sensitive" not in captured.out + captured.err
    if failure == "search":
        assert not checkpoint.exists()
    else:
        assert scrape.load_checkpoint() == {}
