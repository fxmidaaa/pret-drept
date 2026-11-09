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
import fcntl
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from mlops.files import atomic_output, sha256, write_json

GRAPHQL_URL = "https://999.md/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept-Language": "ro,ru;q=0.9,en;q=0.8",
}

SUBCATEGORY_RENT = 1404 # the "apartamente/camere" subcategory

SNAPSHOTS_DIR = Path(__file__).resolve().parent / "data" / "raw" / "snapshots"
RUN_ID_FORMAT = "%Y-%m-%dT%H%M%S.%fZ"

PAGE_SIZE = 50 # how many ids per search page
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

class CollectionError(RuntimeError):
    """The crawl stopped before the snapshot could be finalized."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def gql(query, variables):
    payload = {"query": query, "variables": variables}
    for attempt in range(3):
        try:
            response = requests.post(
                GRAPHQL_URL, headers=HEADERS, json=payload, timeout=25
            )
            if response.status_code == 429:
                raise CollectionError("999.md rate limited this crawl. Resume later.")
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == 2:
                raise CollectionError(
                    "999.md request failed after three attempts."
                ) from exc
            time.sleep(3)
        else:
            break

    if not isinstance(result, dict) or result.get("errors"):
        raise CollectionError("999.md returned a GraphQL error.")
    data = result.get("data")
    if not isinstance(data, dict):
        raise CollectionError("999.md returned an invalid response.")
    return data


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
    try:
        search_results = data["searchAds"]
        total = search_results["count"]
        ids = [ad["id"] for ad in search_results["ads"]]
    except (KeyError, TypeError) as exc:
        raise CollectionError("999.md returned an invalid search page.") from exc
    if type(total) is not int or total < 0 or any(ad_id is None for ad_id in ids):
        raise CollectionError("999.md returned an invalid search count or ad ID.")
    if not ids and skip < total:
        raise CollectionError(
            "999.md returned an empty page before the end of results."
        )
    return total, ids


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
# Only reviewed controls are persisted. The listing key is a stable pseudonym.
# Keep raw snapshots private because maps, photos and ad text can identify listings.
FEATURE_FIELDS = [
    "Număr de camere", "Suprafață totală", "Etaj", "Număr de etaje",
    "Fond locativ", "Starea apartamentului", "Sector", "Încălzire autonomă",
    "Mobilat", "Ascensor", "Loc de parcare", "Harta", "Autorul anunțului",
    "Tip clădire", "Balcon/ lojie", "Fotografii", "Suprafață bucătărie",
    "Inălțimea tavanelor", "Terasă", "Aparat de aer condiționat",
    "Încălzire prin pardoseală", "Geamuri panoramice", "Textul anunțului",
]
# fields used only to filter down to "monthly rent in Chisinau"
FILTER_FIELDS = ["Tipul ofertei", "Regiune", "Localitate"]
ALLOWED_FIELDS = set(FEATURE_FIELDS + FILTER_FIELDS)
CSV_FIELDS = [
    "listing_key",
    "observed_at",
    "price_value",
    "price_unit",
    *FEATURE_FIELDS,
    *FILTER_FIELDS,
]


def listing_key(listing_id):
    return hashlib.sha1(str(listing_id).encode("utf-8")).hexdigest()[:16]


def fetch_listing_details(listing_id):
    data = gql(DETAIL_QUERY, {"i": {"id": str(listing_id)}})
    advert = data.get("advert")
    if "advert" not in data or (advert is not None and not isinstance(advert, dict)):
        raise CollectionError("999.md returned invalid ad details.")
    if advert is None:
        return None

    row = {"listing_key": listing_key(listing_id), "observed_at": utc_now()}

    for group in (advert.get("groups") or []):
        for control in (group.get("controls") or []):
            name = control.get("title")

            if not name:
                continue

            raw_value = (control.get("feature") or {}).get("value")

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

    is_rent = (offer == "De închiriat lunar")
    is_chisinau = ("chișinău" in loc or "chisinau" in loc)

    return is_rent and is_chisinau

def collect_snapshot(directory: Path, limit: int | None) -> None:
    manifest_path = directory / "snapshot.json"
    if manifest_path.exists():
        raise CollectionError("This snapshot is already complete.")

    checkpoint_path = directory / "checkpoint.json"
    if limit is None:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    else:
        checkpoint = {
            "status": "partial",
            "started_at": utc_now(),
            "limit": limit,
            "next_skip": 0,
            "stop_reason": None,
            "rows": {},
            "excluded": {},
        }
        write_json(checkpoint_path, checkpoint)

    rows = checkpoint["rows"]
    excluded = checkpoint["excluded"]
    limit = checkpoint["limit"]
    while checkpoint["stop_reason"] is None:
        skip = checkpoint["next_skip"]
        try:
            total, ids = fetch_ids_on_page(skip)
            for listing_id in ids:
                if len(rows) + len(excluded) >= limit:
                    break
                key = listing_key(listing_id)
                if key in rows or key in excluded:
                    continue

                row = fetch_listing_details(listing_id)
                if row is None:
                    excluded[key] = "unavailable"
                elif target_valid(row):
                    rows[key] = row
                else:
                    excluded[key] = "outside_scope"
                time.sleep(SLEEP)
        except (CollectionError, KeyboardInterrupt):
            # Keep completed details and retry this search page on resume.
            write_json(checkpoint_path, checkpoint)
            raise

        checkpoint["next_skip"] += PAGE_SIZE
        if len(rows) + len(excluded) >= limit:
            checkpoint["stop_reason"] = "limit_reached"
        elif checkpoint["next_skip"] >= total:
            checkpoint["stop_reason"] = "end_of_results"
        if checkpoint["stop_reason"] is not None:
            checkpoint["finished_at"] = utc_now()
        write_json(checkpoint_path, checkpoint)
        print(
            f"Checked {len(rows) + len(excluded)} ads, saved {len(rows)}.", flush=True
        )

    csv_path = directory / "listings.csv"
    with (
        atomic_output(csv_path) as temporary,
        temporary.open("w", encoding="utf-8-sig", newline="") as stream,
    ):
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(
            sorted(
                rows.values(), key=lambda row: (row["observed_at"], row["listing_key"])
            )
        )

    # The final manifest is the completion marker. Write it after the CSV.
    write_json(
        manifest_path,
        {
            "run_id": directory.name,
            "source": GRAPHQL_URL,
            "status": "complete",
            "started_at": checkpoint["started_at"],
            "finished_at": checkpoint["finished_at"],
            "stop_reason": checkpoint["stop_reason"],
            "limit": limit,
            "checked_ads": len(rows) + len(excluded),
            "saved_rows": len(rows),
            "outside_scope_ads": sum(
                reason == "outside_scope" for reason in excluded.values()
            ),
            "unavailable_ads": sum(
                reason == "unavailable" for reason in excluded.values()
            ),
            "csv_sha256": sha256(csv_path),
        },
    )
    checkpoint_path.unlink(missing_ok=True)
    print(f"Saved {len(rows)} rows to {csv_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect a private, dated 999.md snapshot."
    )
    options = parser.add_mutually_exclusive_group()
    options.add_argument(
        "--limit", type=int, help=f"Cap unique ads checked (default {MAX_LISTINGS})."
    )
    options.add_argument(
        "--resume", metavar="RUN_ID", help="Resume an incomplete snapshot."
    )
    args = parser.parse_args()

    limit = None
    run_id = args.resume
    if run_id is not None:
        try:
            datetime.strptime(run_id, RUN_ID_FORMAT)
        except ValueError:
            parser.error("--resume takes the UTC run directory name.")
    else:
        limit = args.limit if args.limit is not None else MAX_LISTINGS
        if not 1 <= limit <= MAX_LISTINGS:
            parser.error(f"--limit must be between 1 and {MAX_LISTINGS}.")
        run_id = datetime.now(UTC).strftime(RUN_ID_FORMAT)

    directory = SNAPSHOTS_DIR / run_id
    try:
        if limit is not None:
            directory.mkdir(mode=0o700, parents=True)
        print(f"Snapshot directory {directory}", flush=True)
        with (directory / ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CollectionError(
                    "This snapshot is already being collected."
                ) from None
            collect_snapshot(directory, limit)
    except KeyboardInterrupt:
        parser.exit(130, f"Collection interrupted. Resume with --resume {run_id}.\n")
    except (OSError, CollectionError, ValueError) as exc:
        parser.exit(1, f"Collection stopped. {exc}\n")


if __name__ == "__main__":
    main()