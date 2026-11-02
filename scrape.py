# Scrapes apartment "long-term rent" listings for Chisinau from 999.md.
#
# 999.md is a Next.js site that loads listings with javascript, so plain
# requests + BeautifulSoup on the HTML does NOT work (the html is just an
# empty shell). BUT the site talks to a public GraphQL API at
#   https://999.md/graphql
# and that API returns everything as clean JSON - already parsed: price,
# area, rooms, floor, sector, heating type, etc. No html parsing needed.

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

GRAPHQL_URL = "https://999.md/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept-Language": "ro,ru;q=0.9,en;q=0.8",
}

SUBCATEGORY_RENT = 1404  # the "apartamente/camere" subcategory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "raw", "listings.csv")
TODAY = date.today().isoformat()

PAGE_SIZE = 50  # how many ids per search page
MAX_LISTINGS = 6000
SLEEP = 0.3  # delay between API calls


# first filter is for "De inchiriat lunar", second is for "Chisinau"

SEARCH_FILTERS = [
    {"filterId": 16, "features": [{"featureId": 1, "optionIds": [912]}]},
    {"filterId": 32, "features": [{"featureId": 8, "optionIds": [13859]}]},
]


# --- the two graphQL queries we use -----------------------------------------

# phase 1: just the ids on a page (cheap)
SEARCH_QUERY = """
query($i: Ads_SearchInput!) {
  searchAds(input: $i) {
    count
    ads { id }
  }
}
"""

# phase 2: all attributes for one listing.
# every attribute comes back as a "control" with a title (the field name in
# romanian) and a feature.value (the value). VIEW_ONE_DEFAULT = the detail page.
DETAIL_QUERY = """
query($i: AdvertInput!) {
  advert(input: $i) {
    id
    groups(placement: VIEW_ONE_DEFAULT) {
      controls { title option_title feature { value } }
    }
  }
}
"""


def gql(query, variables):
    # send one graphql request, retry a couple of times if the connection drops
    payload = json.dumps({"query": query, "variables": variables})
    for attempt in range(3):
        try:
            r = requests.post(GRAPHQL_URL, headers=HEADERS, data=payload, timeout=25)
            data = r.json()

            if "errors" in data:
                print("graphql error:", data["errors"][:1], flush=True)
                return None

            return data["data"]
        except Exception as e:
            print("request failed, retrying...", e, flush=True)
            time.sleep(3)
    return None


def fetch_ids_on_page(skip):
    # returns the total listing count and a list of IDs for a specific page offset
    variables = {
        "i": {
            "subCategoryId": SUBCATEGORY_RENT,
            "hideDuplicates": True,  # 999 collapses agency reports for us
            "filters": SEARCH_FILTERS,  # monthly rent + chisinau
            "pagination": {"skip": skip, "limit": PAGE_SIZE},
        }
    }

    data = gql(SEARCH_QUERY, variables)

    if data is None:
        return 0, []

    search_results = data["searchAds"]
    return search_results["count"], [ad["id"] for ad in search_results["ads"]]


def simplify_feature_value(value):
    # a feature.value can be: a plain string/number/bool, OR a small dict.the dicts look like
    # {"translated": "...", "value": 123} for choices, or {"value": 65, "unit": "UNIT_METER_SQUARE"} for measurements.
    # we want one clean cell out of it.
    if isinstance(value, dict):
        if "translated" in value:
            return value["translated"]
        if "value" in value:
            return value["value"]
        return json.dumps(value, ensure_ascii=False)
    return value


# --- explicit persistence allowlist -----------------------------------------
# The scraper NEVER writes a field that is not on this list. Contacts, phone
# numbers, the seller's name and every other control the API returns are dropped
# at collection time. Listing ids are stored only as a short non-reversible hash
# so a saved row can't be walked back to the live ad. Map and ad text stay
# because the model derives coarse features from them, and the raw file is
# private: gitignored, never shipped in the image, never committed to the repo.
FEATURE_FIELDS = [
    "Număr de camere",
    "Suprafață totală",
    "Etaj",
    "Număr de etaje",
    "Fond locativ",
    "Starea apartamentului",
    "Sector",
    "Încălzire autonomă",
    "Mobilat",
    "Ascensor",
    "Loc de parcare",
    "Harta",
    "Autorul anunțului",
    "Tip clădire",
    "Balcon/ lojie",
    "Fotografii",
    "Suprafață bucătărie",
    "Inălțimea tavanelor",
    "Terasă",
    "Aparat de aer condiționat",
    "Încălzire prin pardoseală",
    "Geamuri panoramice",
    "Textul anunțului",
]
# fields used only to filter down to "monthly rent in Chisinau"
FILTER_FIELDS = ["Tipul ofertei", "Regiune", "Localitate"]
ALLOWED_FIELDS = set(FEATURE_FIELDS + FILTER_FIELDS)


def listing_key(listing_id):
    # short, non-reversible id so we can dedupe/resume without persisting the
    # real 999.md listing id (which links straight back to the live ad).
    return hashlib.sha1(str(listing_id).encode("utf-8")).hexdigest()[:16]


def fetch_listing_details(listing_id):
    # download a single listing and transform it into a flat dict, keeping ONLY
    # the reviewed allowlist fields. the id becomes a non-reversible hash, and any
    # control not on the allowlist (contacts, phone, seller name, ...) is dropped
    # at collection time and never touches disk.
    data = gql(DETAIL_QUERY, {"i": {"id": str(listing_id)}})
    if data is None or data.get("advert") is None:
        return None

    row = {"listing_key": listing_key(listing_id)}

    for group in data["advert"].get("groups") or []:
        for control in group.get("controls") or []:
            name = control.get("title")

            if not name:
                continue

            raw_value = control.get("feature", {}).get("value")

            # price needs special care: the value is a dict that carries both
            # the amount and the currency, and listings mix EUR / MDL / USD.
            # losing the currency would wreck the model, so keep it explicitly.
            if name == "Preț" and isinstance(raw_value, dict):
                row["price_value"] = raw_value.get("value")
                row["price_unit"] = raw_value.get("unit")  # e.g. UNIT_EUR / UNIT_MDL
                continue

            # drop everything not explicitly reviewed and needed by the model
            if name not in ALLOWED_FIELDS:
                continue

            value = simplify_feature_value(raw_value)

            if value in (None, "", []):
                value = control.get("option_title")

            row[name] = value

    return row


def target_valid(row):
    # checking that the listing explicitly matches monthly rent in Chisinau
    offer = str(row.get("Tipul ofertei", "")).strip()
    loc = (str(row.get("Regiune", "")) + " " + str(row.get("Localitate", ""))).lower()

    is_rent = offer == "De închiriat lunar"
    is_chisinau = "chișinău" in loc or "chisinau" in loc

    return is_rent and is_chisinau


class CheckpointError(ValueError):
    """Checkpoint validation failed; never discard records to repair it implicitly."""


def _index_checkpoint(rows):
    rows_by_id = {}
    for row in rows:
        key = row.get("listing_key") if isinstance(row, dict) else None
        if not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{16}", key) is None:
            raise CheckpointError("Each listing_key must be 16 lowercase hexadecimal characters.")
        if key in rows_by_id:
            raise CheckpointError("Duplicate listing_key; no records were discarded.")
        rows_by_id[key] = row
    return rows_by_id


def _read_checkpoint(path):
    if path.is_symlink():
        raise CheckpointError("A checkpoint must not be a symlink.")
    previous_limit = csv.field_size_limit()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            # A valid cell cannot exceed its file; restore the process setting below.
            csv.field_size_limit(max(previous_limit, os.fstat(stream.fileno()).st_size))
            reader = csv.reader(stream, strict=True)
            columns = next(reader, [])
            if "listing_key" not in columns:
                raise CheckpointError(
                    "Checkpoint requires a listing_key column. Preserve the original and "
                    "review migration to a separate file before resuming."
                )
            if len(set(columns)) != len(columns) or any(not name for name in columns):
                raise CheckpointError("Checkpoint column names must be nonempty and unique.")
            return _index_checkpoint(dict(zip(columns, values, strict=True)) for values in reader)
    except FileNotFoundError:
        return {}
    except CheckpointError:
        raise
    except (OSError, UnicodeError, csv.Error, ValueError):
        raise CheckpointError(
            "Checkpoint is not a readable UTF-8 CSV; it was not modified."
        ) from None
    finally:
        csv.field_size_limit(previous_limit)


def load_checkpoint(path=None):
    path = Path(CSV_PATH if path is None else path)
    rows_by_id = _read_checkpoint(path)
    print("loaded", len(rows_by_id), "listings i already had", flush=True)
    return rows_by_id


def save_checkpoint(rows_by_id, path=None):
    """Validate and replace working state atomically; this is not dataset publication."""
    path = Path(CSV_PATH if path is None else path)
    indexed = _index_checkpoint(rows_by_id.values())
    if indexed.keys() != rows_by_id.keys():
        raise CheckpointError("Checkpoint mapping keys do not match their listing_key values.")
    if _read_checkpoint(path).keys() - indexed.keys():
        raise CheckpointError("Checkpoint save would drop existing records; replacement refused.")
    frame = pd.DataFrame(indexed.values()) if indexed else pd.DataFrame(columns=["listing_key"])
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8-sig", newline="") as stream:
            frame.to_csv(stream, index=False)
            stream.flush()
            os.fsync(stream.fileno())
        restored = _read_checkpoint(Path(temporary))
        if restored.keys() != indexed.keys():
            raise CheckpointError("Serialized checkpoint population differs; replacement refused.")
        columns = set(frame.columns)
        if any(row.keys() != columns for row in restored.values()):
            raise CheckpointError("Serialized checkpoint schema differs; replacement refused.")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(checkpoint_path=None):
    checkpoint_path = Path(CSV_PATH if checkpoint_path is None else checkpoint_path)
    rows_by_id = load_checkpoint(checkpoint_path)
    skip = 0

    while len(rows_by_id) < MAX_LISTINGS:
        total, ids = fetch_ids_on_page(skip=skip)
        # print("page skip=%d -> %d ids (api says %d total)" % (skip, len(ids), total), flush=True)

        if not ids:
            print("no more listings, stopping", flush=True)
            break

        kept = 0

        for listing_id in ids:
            sid = listing_key(listing_id)

            if sid in rows_by_id:
                rows_by_id[sid]["last_seen"] = TODAY
                continue

            try:
                row = fetch_listing_details(listing_id)

                if row is not None and target_valid(row):
                    row["first_seen"] = TODAY
                    row["last_seen"] = TODAY
                    rows_by_id[sid] = row
                    kept += 1
                else:
                    rows_by_id[sid] = {
                        "listing_key": sid,
                        "first_seen": TODAY,
                        "last_seen": TODAY,
                        "Tipul ofertei": "rejected",
                    }
            except Exception as e:
                print("skipped", sid, "-", e, flush=True)

            time.sleep(SLEEP)

        save_checkpoint(rows_by_id, checkpoint_path)
        print("kept %d this page | total %d" % (kept, len(rows_by_id)), flush=True)

        skip += PAGE_SIZE
        if skip >= total:
            print("reached end of results (%d)" % total, flush=True)
            break

    print("done. total chisinau rents: ", len(rows_by_id), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect or resume a compatible working checkpoint."
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path(CSV_PATH),
        help="Working CSV path (default: data/raw/listings.csv); incompatible files are rejected.",
    )
    try:
        main(parser.parse_args().checkpoint)
    except (CheckpointError, OSError) as error:
        parser.exit(1, f"Checkpoint error: {error}\n")
