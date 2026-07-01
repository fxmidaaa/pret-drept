# Scrapes apartment "long-term rent" listings for Chisinau from 999.md.
#
# 999.md is a Next.js site that loads listings with javascript, so plain
# requests + BeautifulSoup on the HTML does NOT work (the html is just an
# empty shell). BUT the site talks to a public GraphQL API at
#   https://999.md/graphql
# and that API returns everything as clean JSON - already parsed: price,
# area, rooms, floor, sector, heating type, etc. No html parsing needed.

import requests
import pandas as pd
import os
import json
import time

GRAPHQL_URL = "https://999.md/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept-Language": "ro,ru;q=0.9,en;q=0.8",
}

SUBCATEGORY_RENT = 1404 # the "apartamente/camere" subcategory
CSV_PATH = "data/raw/listings.csv"
PAGE_SIZE = 50 # how many ids per search page
MAX_LISTINGS = 6000 
SLEEP = 1.0  # delay between API calls


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
            "hideDuplicates": True, # 999 collapses agency reports for us
            "filters": SEARCH_FILTERS, # monthly rent + chisinau
            "pagination": {"skip": skip, "limit": PAGE_SIZE}
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

def fetch_listing_details(listing_id):
    # download a single listing and transforms into a flat dict. keys are romanian field names just 
    data = gql(DETAIL_QUERY, {"i": 
                              {"id": str(listing_id)}
                              })
    if data is None or data.get("advert") is None:
        return None
    
    row = {"id": listing_id}

    for group in (data["advert"].get("groups") or []):
        for control in (group.get("controls") or []):
            name = control.get("title")

            if not name:
                continue
            
            raw_value = control.get("feature", {}).get("value")

            # price needs special care: the value is a dict that carries both
            # the amount and the currency, and listings mix EUR / MDL / USD.
            # losing the currency would wreck the model, so keep it explicitly.

            if name == "Preț" and isinstance(raw_value, dict):
                row["price_value"] = raw_value.get("value")
                row["price_unit"] = raw_value.get("unit") # e.g. UNIT_EUR / UNIT_MDL

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

def load_checkpoint():
    # loads existing progress from the local CSV
    if os.path.exists(CSV_PATH):
        old_df = pd.read_csv(CSV_PATH)
        all_rows = old_df.to_dict(orient="records")
        seen_ids = set(str(x) for x in old_df["id"])
        print("loaded", len(all_rows), "listings i already had", flush=True)
    else:
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        all_rows, seen_ids = [], set()
        
    return all_rows, seen_ids

def save_checkpoint(all_rows):
    pd.DataFrame(all_rows).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")


def main():
    all_rows, seen_ids = load_checkpoint()
    skip = 0

    while len(all_rows) < MAX_LISTINGS:
        total, ids = fetch_ids_on_page(skip=skip)
        print("page skip=%d -> %d ids (api says %d total)" % (skip, len(ids), total), flush=True)

        if not ids:
            print("no more listings, stopping", flush=True)
            break
        
        kept = 0

        for listing_id in ids:
            if str(listing_id) in seen_ids:
                continue
            
            try:
                row = fetch_listing_details(listing_id)
                if row is not None and target_valid(row):
                    all_rows.append(row)
                    kept += 1
                seen_ids.add(str(listing_id))
            except Exception as e:
                print("skipped", listing_id, "-", e, flush=True)

            time.sleep(SLEEP)
        
        save_checkpoint(all_rows)
        print("kept %d this page | total %d" % (kept, len(all_rows)), flush=True)

        skip += PAGE_SIZE
        if skip >= total:
            print("reached end of results (%d)" % total, flush=True)
            break
        
        print('done. total chisinau rents: ', len(all_rows), flush=True)

if __name__ == "__main__":
    main()