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



# --- the two GraphQL queries we use -----------------------------------------

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
                print("  graphql error:", data["errors"][:1], flush=True)
                return None
            return data["data"]
        except Exception as e:
            print("  request failed, retrying...", e, flush=True)
            time.sleep(3)
    return None