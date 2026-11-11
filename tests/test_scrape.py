import csv
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest

import scrape


@pytest.fixture
def snapshot_root(tmp_path, monkeypatch):
    root = tmp_path / "snapshots"
    monkeypatch.setattr(scrape, "SNAPSHOTS_DIR", root)
    monkeypatch.setattr(scrape, "SLEEP", 0)
    return root


def run_scraper(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["scrape.py", *args])
    scrape.main()


def response(payload):
    return SimpleNamespace(
        status_code=200, raise_for_status=lambda: None, json=lambda: payload
    )


def search_page(*ids, total=None):
    return response(
        {
            "data": {
                "searchAds": {
                    "count": len(ids) if total is None else total,
                    "ads": [{"id": ad_id} for ad_id in ids],
                }
            }
        }
    )


def listing(price, offer="De închiriat lunar"):
    controls = [
        {"title": "Preț", "feature": {"value": {"value": price, "unit": "UNIT_EUR"}}},
        {"title": "Tipul ofertei", "feature": None, "option_title": offer},
        {"title": "Regiune", "feature": {"value": "Chișinău"}},
        {"title": "Telefon", "feature": {"value": "private fixture"}},
    ]
    return response({"data": {"advert": {"groups": [{"controls": controls}]}}})


def read_snapshot(directory):
    manifest = json.loads((directory / "snapshot.json").read_text(encoding="utf-8"))
    path = directory / "listings.csv"
    assert manifest["status"] == "complete"
    assert manifest["csv_sha256"] == sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return manifest, list(csv.DictReader(stream))


def test_fresh_snapshots_fetch_current_details_and_preserve_earlier_files(
    snapshot_root, monkeypatch
):
    prices = iter([450, 500])
    fetched = []

    def post(url, *, json, **kwargs):
        if json["query"] == scrape.SEARCH_QUERY:
            return search_page("a", "a", "b", "c", "d")
        ad_id = json["variables"]["i"]["id"]
        fetched.append(ad_id)
        if ad_id == "a":
            return listing(next(prices))
        if ad_id == "b":
            return listing(250, offer="De vânzare")
        assert ad_id == "c"
        return response({"data": {"advert": None}})

    monkeypatch.setattr(scrape.requests, "post", post)
    legacy_path = snapshot_root.parent / "listings.csv"
    legacy_path.write_text("old snapshot\n", encoding="utf-8")

    run_scraper(monkeypatch, "--limit", "3")
    (first,) = snapshot_root.iterdir()
    first_manifest, first_rows = read_snapshot(first)
    run_scraper(monkeypatch, "--limit", "1")
    (second,) = set(snapshot_root.iterdir()) - {first}
    _, second_rows = read_snapshot(second)

    assert fetched == ["a", "b", "c", "a"]
    assert legacy_path.read_text(encoding="utf-8") == "old snapshot\n"
    assert read_snapshot(first) == (first_manifest, first_rows)
    assert first_manifest["stop_reason"] == "limit_reached"
    assert first_manifest["checked_ads"] == 3
    assert first_manifest["saved_rows"] == first_manifest["outside_scope_ads"] == 1
    assert first_manifest["unavailable_ads"] == 1
    (first_row,) = first_rows
    (second_row,) = second_rows
    assert (
        first_row["listing_key"] == second_row["listing_key"] == scrape.listing_key("a")
    )
    assert first_row["price_value"] == "450" and second_row["price_value"] == "500"
    assert first_row["price_unit"] == "UNIT_EUR"
    assert "Telefon" not in first_row
    observed_at = datetime.fromisoformat(first_row["observed_at"])
    assert observed_at.tzinfo == UTC
    assert (
        first_manifest["started_at"]
        <= first_row["observed_at"]
        <= first_manifest["finished_at"]
    )


def test_api_error_keeps_partial_page_resumable(snapshot_root, monkeypatch):
    fetched = []

    def post(url, *, json, **kwargs):
        if json["query"] == scrape.SEARCH_QUERY:
            return search_page("a", "b")
        ad_id = json["variables"]["i"]["id"]
        fetched.append(ad_id)
        if fetched == ["a", "b"]:
            return response({"errors": [{"message": "Fixture failure"}]})
        return listing(450)

    monkeypatch.setattr(scrape.requests, "post", post)
    with pytest.raises(SystemExit) as failure:
        run_scraper(monkeypatch)
    assert failure.value.code == 1
    (directory,) = snapshot_root.iterdir()
    checkpoint_path = directory / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["status"] == "partial"
    assert not (directory / "snapshot.json").exists()
    key = scrape.listing_key("a")
    earlier_observation = checkpoint["rows"][key]["observed_at"]

    run_scraper(monkeypatch, "--resume", directory.name)
    assert fetched == ["a", "b", "b"]
    assert not checkpoint_path.exists()
    manifest, rows = read_snapshot(directory)
    assert manifest["started_at"] == checkpoint["started_at"]
    assert manifest["stop_reason"] == "end_of_results"
    assert manifest["saved_rows"] == len(rows) == 2
    assert (
        next(row for row in rows if row["listing_key"] == key)["observed_at"]
        == earlier_observation
    )

    with pytest.raises(SystemExit) as failure:
        run_scraper(monkeypatch, "--resume", directory.name)
    assert failure.value.code == 1
    assert read_snapshot(directory) == (manifest, rows)
