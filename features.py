import numpy as np
import json
import re

MDL_PER_EUR = 19.5
EUR_PER_USD = 0.92  # rough USD -> EUR, very few listings use USD
ROOMS_COL = "Număr de camere"
AREA_COL = "Suprafață totală"
FLOOR_COL = "Etaj"
TOTAL_FLOORS_COL = "Număr de etaje"
FUND_COL = "Fond locativ"
CONDITION_COL = "Starea apartamentului"
SECTOR_COL = "Sector"
HEATING_COL = "Încălzire autonomă"
FURNISHED_COL = "Mobilat"
ELEVATOR_COL = "Ascensor"
PARKING_COL = "Loc de parcare"
MAP_COL = "Harta"
AUTHOR_COL = "Autorul anunțului"
BUILDING_TYPE_COL = "Tip clădire"
BALCONY_COL = "Balcon/ lojie"
PHOTOS_COL = "Fotografii"
KITCHEN_COL = "Suprafață bucătărie"
CEILING_COL = "Inălțimea tavanelor"
TERRACE_COL = "Terasă"
AC_COL = "Aparat de aer condiționat"
FLOOR_HEATING_COL = "Încălzire prin pardoseală"
PANORAMIC_COL = "Geamuri panoramice"
TEXT_COL = "Textul anunțului"

# I turn each listing's gps coordinate into a distance-to-center in km. (Chisinau city centre)
CENTER_LAT, CENTER_LON = 47.0245, 28.8322 # piata marii adunari nationale 
LON_SCALE = 0.682   # cos(47 deg): 1 deg of longitude is shorter than 1 deg of latitude here

numerical = ["rooms", "area", "floor", "total_floors", "dist_to_center",
              "lat", "lon", "kitchen_area", "ceiling_height",
                "balcony_count", "photo_count"]
binary = ["autonomous_heating", "furnished", "elevator", "parking", "is_ground", "is_top",
          "air_conditioning", "floor_heating", "terrace", "panoramic_windows",
          "utilities_included"]
categorical = ["sector", "building_fund", "condition", "author", "building_type"]
FEATURES = numerical + binary + categorical

def floor_flags(floor, total_floors):
    # this rule lives here (and ONLY here) so that
    # training, predict.py and the api can never drift apart on what "ground" means
    is_ground = int(floor is not None and floor <= 1)
    is_top = int(floor is not None and total_floors is not None and floor >= total_floors)
    return is_ground, is_top

def parse_latlon(harta):
    # 'Harta' is a json string like {"lat": 47.03, "lon": 28.80}. Turn it into the
    # approximate distance in km from the city centre. Bad / missing coords -> None.
    try:
        h = json.loads(harta) if isinstance(harta, str) else {}
        lat, lon = h.get("lat"), h.get("lon")

    except Exception:
        return None, None
    
    if lat is None or lon is None:
        return None, None
    
    if not (46.9 < lat < 47.10 and 28.74 < lon < 28.95):
        return None, None
    return float(lat), float(lon)    
    
def latlon_to_km(lat, lon):
    dlat = lat - CENTER_LAT
    dlon = (lon - CENTER_LON) * LON_SCALE

    return float(np.sqrt(dlat ** 2 + dlon ** 2) * 111.0) # degrees into kilometers (thanks to geography in lyceum)

def distance_to_center(harta):
    lat, lon = parse_latlon(harta)
    if lat is None:
        return None
    return latlon_to_km(lat, lon)

def first_number(text):
    # pull the first number out of a value. "62" -> 62.0, "Apartament cu 3 camere" -> 3.0
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None
    m = re.search(r"\d+[.,]?\d*", str(text))
    if m is None:
        return None
    return float(m.group().replace(",", "."))

def clean_rooms(text):
    # "Apartament cu 1 camera", "Apartament cu 4 camere", or "O camera"
    n = first_number(text)
    if n is None:
        # "O camera" / "camera" has no digit - treat as a 1-room / studio
        if isinstance(text, str) and "camer" in text.lower():
            return 1.0
        return None
    return n

def clean_text(text):
    # for category columns: lowercase, trim, fill the empty ones
    if not isinstance(text, str):
        return "necunoscut"
    return text.strip().lower()

def to_flag(value):
    # the amenity columns come back as True (present in romanian) or NaN/False (absent)
    if value is True:
        return 1
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("true", "da", "1") else 0
    return 0

def clean_parking(value):
    # "Loc de parcare" is "Deschis"/"Subterana"/"Sub acoperis" when present (in romanian), NaN when not
    if isinstance(value, str) and value.strip() and value.strip().lower() != "nu":
        return 1
    return 0

def clean_balcony(value):
    # "Balcon/ lojie" is "1"/"2"/"3"/"4 si mai multe"/"Nu"/NaN -> a count
    n = first_number(value)
    if n is None:
        return 0 # "Nu" or not specified
    return min(n, 4.0)

def clean_photos(value):
    if not isinstance(value, str):
        return 0
    return value.count(".jpg") + value.count(".png") + value.count(".webp")

def clean_kitchen(value):
    # kitchen area in m2; only ~10% of listings fill it, and some put 0 for "unknown"
    v = first_number(value)
    if v is None or not (3 <= v <= 60):
        return None
    return v

def clean_ceiling(value):
    # ceiling height. people type it in whatever unit they feel like:
    # "3" (m), "28" (dm??!), "280" (cm). normalize everything to meters.
    v = first_number(value)
    if v is None or v <= 0:
        return None
    if 2 <= v <= 4.5:
        return v
    if 20 <= v <= 45:
        return v / 10
    if 200 <= v <= 450:
        return v / 100
    return None

# people often write the condition in the ad text even when the structured field
# is empty (~1/3 of listings). ads come in romanian AND russian, so both.
# order matters: the first pattern that matches wins.
CONDITION_PATTERNS = [
    ("euroreparație", ["eurorepara", "euro repara", "евроремонт"]),
    ("design individual", ["design individual", "дизайнерск"]),
    ("dat în exploatare", ["dat în exploatare", "dat in exploatare", "сдан в эксплуатацию"]),
    ("variantă albă", ["variantă albă", "varianta alba", "белый вариант", "белом варианте"]),
    ("are nevoie de reparație", ["nevoie de repara", "necesită repara", "требует ремонта"]),
    ("fără reparație", ["fără repara", "fara repara", "без ремонта"]),
    ("reparație cosmetică", ["cosmetic", "косметическ"]),
]

def condition_from_text(text):
    if not isinstance(text, str):
        return None
    t = text.lower()
    for condition, keys in CONDITION_PATTERNS:
        if any(k in t for k in keys):
            return condition
    return None

# "utilities included in the rent" is invisible in the structured fields but is a
# known source of price noise. conservative keywords only - "+ comunale" usually
# means the OPPOSITE (utilities on top), so it's not in the list.
UTILITIES_KEYS = ["comunale incluse", "inclusiv comunale", "incluse comunale",
                  "totul inclus", "toate incluse",
                  "коммунальные включены", "включая коммунальные", "все включено"]

def utilities_from_text(text):
    if not isinstance(text, str):
        return 0
    t = text.lower()
    return int(any(k in t for k in UTILITIES_KEYS))

def clean_price(row):
    # building the monthly rent in EUR from the value + its current unit
    value = row.get("price_value")

    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    
    value = float(value)
    unit = str(row.get("price_unit", ""))

    if unit == "UNIT_MDL":
        return value / MDL_PER_EUR
    
    if unit == "UNIT_USD":
        return value * EUR_PER_USD
    return value

def clean_data(df):
    # cleans raw scraped 999 dataframe and returns a ready one for the model
    df = df.copy()

    # --- NUMERICAL FEATURES --- 

    df["price"] = df.apply(clean_price, axis=1)

    df['rooms'] = df[ROOMS_COL].apply(clean_rooms)
    df['area'] = df[AREA_COL].apply(first_number)
    df['floor'] = df[FLOOR_COL].apply(first_number)
    df['total_floors'] = df[TOTAL_FLOORS_COL].apply(first_number)

    latlon = [parse_latlon(h) for h in df[MAP_COL]]
    df["lat"] = np.array([p[0] if p[0] is not None else np.nan for p in latlon], dtype = float)
    df["lon"] = np.array([p[1] if p[1] is not None else np.nan for p in latlon], dtype=float)
    df["dist_to_center"] = np.array(
        [latlon_to_km(p[0], p[1]) if p[0] is not None else np.nan for p in latlon], dtype=float
    )

    df["kitchen_area"] = df[KITCHEN_COL].apply(clean_kitchen)
    df["ceiling_height"] = df[CEILING_COL].apply(clean_ceiling)
    df["balcony_count"] = df[BALCONY_COL].apply(clean_balcony)
    df["photo_count"] = df[PHOTOS_COL].apply(clean_photos)

    # --- BINARY FEATURES --- 
    df["autonomous_heating"] = df[HEATING_COL].apply(to_flag)
    df["furnished"] = df[FURNISHED_COL].apply(to_flag)
    df["elevator"] = df[ELEVATOR_COL].apply(to_flag)
    df["parking"] = df[PARKING_COL].apply(clean_parking)
    df["air_conditioning"] = df[AC_COL].apply(to_flag)
    df["floor_heating"] = df[FLOOR_HEATING_COL].apply(to_flag)
    df["terrace"] = df[TERRACE_COL].apply(to_flag)
    df["panoramic_windows"] = df[PANORAMIC_COL].apply(to_flag)
    df["utilities_included"] = df[TEXT_COL].apply(utilities_from_text)

    # --- CATEGORICAL FEATURES ---
    df["sector"] = df[SECTOR_COL].apply(clean_text)
    df["building_fund"] = df[FUND_COL].apply(clean_text) # new vs secundar 
    df["condition"] = df[CONDITION_COL].apply(clean_text)
    df["author"] = df[AUTHOR_COL].apply(clean_text) # agency / personal property / dezvoltator
    df["building_type"] = df[BUILDING_TYPE_COL].apply(clean_text)

    # ~1/3 of listings with empty condiftion field but describe it in the ad.
    # ad text ("euroreparatie", "евроремонт"...). recover what we can from there.
    blank = df["condition"] == "necunoscut"
    from_text = df.loc[blank, TEXT_COL].apply(condition_from_text)
    df.loc[blank, "condition"] = from_text.fillna("necunoscut")

    # drop rows that lack the most important features
    df = df.dropna(subset=["price", "area", "rooms"])

    # drop duplicated listings. a lot of apartments are reposted with another ad.
    # if one copy lands in train and another in validation, the model gets graded on flats
    # it has already seen and the metrics look better than they really are.
    # same key attributes + same price = same flat, i assume. 
    df = df.drop_duplicates(
        subset=["sector", "rooms", "area", "floor", "total_floors", "price"]
    )

    # remove obvious outliers (typos, daily-rate leftovers, bad areas)
    # the price cap is 3000 EUR/month on purpose: this model is for the mass
    # segment. the ~3% luxury tail above that is rare, wildly heterogeneous and
    # wrecks every squared metric while telling us nothing about ordinary flats.
    df = df[(df["price"] >= 100) & (df["price"] <= 3000)] # in euros
    df = df[(df["area"] >= 10) & (df["area"] <= 400)]
    df = df[(df["rooms"] >= 1) & (df["rooms"] <= 6)]

    # two cheap derived flags, computed by the shared rule above
    flags = [floor_flags(f, t) for f, t in zip(df["floor"], df["total_floors"])]
    df["is_ground"] = [g for g, _ in flags]
    df["is_top"] = [t for _, t in flags]

    return df

# the columns whose missing values get filled with a median. the medians are FIT
# on the training split only and then reused everywhere else - fitting them on
# the full dataset would leak validation rows into the training features.
IMPUTE_COLS = ["floor", "total_floors", "dist_to_center",
               "lat", "lon", "kitchen_area", "ceiling_height"]

def trim_ppm_outliers(df, bounds=None):
    # drop the worst 1% on each end of "rent-per-m2". these are almost always some data issues.
    # i.e, wrong area, prices includes utilities and etc.
    # this step alone is one of the biggest R^2 improvements i found so far.
    # pass bounds=None to fit them (train split), or reuse train bounds for validation
    # so that validation rows never decide which training rows survive.
    ppm = df["price"] / df["area"]
    if bounds is None:
        bounds = (float(ppm.quantile(0.01)), float(ppm.quantile(0.99)))
    lo, hi = bounds
    return df[(ppm >= lo) & (ppm <= hi)], bounds

def impute_medians(df, medians=None):
    # fill missing numerics with medians. pass medians=None to fit them (train
    # split), or reuse the train medians for validation / new data.
    df = df.copy()
    if medians is None:
        medians = {c: float(df[c].median()) for c in IMPUTE_COLS}
    for column, median in medians.items():
        df[column] = df[column].fillna(median)
    return df, medians

def knn_market_rate(df_fit, df_target, k=15, exclude_self = False):
    # "what do the neighbors charge?"
    # median eur/m2 among the k nearest listings of df_fit for every df_target row.
    # this is what we basically do when judge a price - look around.

    from sklearn.neighbors import NearestNeighbors
    pts_fit = np.column_stack([df_fit["lat"].values, df_fit["lon"].values * LON_SCALE])
    ppm_fit = (df_fit["price"] / df_fit["area"]).values
    pts_target = np.column_stack([df_target["lat"].values, df_target["lon"].values * LON_SCALE])

    n = min(k + (1 if exclude_self else 0), len(df_fit))
    nn = NearestNeighbors(n_neighbors=n)
    nn.fit(pts_fit)
    _, idx = nn.kneighbors(pts_target)
    if exclude_self:
        idx = idx[:, 1:]
    return np.median(ppm_fit[idx], axis=1)