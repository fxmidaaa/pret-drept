import json
import math
import re
from collections import Counter
from numbers import Real

import numpy as np

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
                "balcony_count", "photo_count", "bathrooms"]
binary = ["autonomous_heating", "furnished", "elevator", "parking", "is_ground", "is_top",
          "air_conditioning", "floor_heating", "terrace", "panoramic_windows",
          "utilities_included", "lux"]
categorical = ["sector", "building_fund", "condition", "author", "building_type"]
FEATURES = numerical + binary + categorical

def floor_flags(floor, total_floors):
    # this rule lives here (and ONLY here) so that
    # training, predict.py and the api can never drift apart on what "ground" means
    is_ground = int(floor is not None and floor <= 1)
    is_top = int(floor is not None and total_floors is not None and floor >= total_floors)
    return is_ground, is_top

def parse_latlon(harta):
    # Decode numeric coordinates from the source JSON using the existing city bounds.
    try:
        h = json.loads(harta) if isinstance(harta, str) else {}
    except (ValueError, RecursionError):
        return None, None
    if not isinstance(h, dict):
        return None, None
    lat, lon = h.get("lat"), h.get("lon")
    if type(lat) not in (int, float) or type(lon) not in (int, float):
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
    """Extract a finite signed number, with decimal commas and optional exponent."""
    if not isinstance(text, str):
        return _finite_number(text)
    m = re.search(
        r"([+-]?)\s*((?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?)",
        text.replace("−", "-"),
    )
    if m is None:
        return None
    return _finite_number(m.group(1) + m.group(2).replace(",", "."))


def _finite_number(value):
    """Convert supported numeric values and strings to a finite float."""
    if isinstance(value, bool) or not isinstance(value, (Real, str)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None

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
    if n is None or n < 0:
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

# the structured fields can't tell a premium flat from an ordinary one - both say
# "euroreparație". but the ads can: penthouses, jacuzzis, "clasa premium" and so on.
# without this the model prices every big centru flat at the neighborhood average.
LUX_KEYS = ["premium", "penthouse", "de lux", "люкс", "exclusiv", "jacuzzi",
            "джакузи", "saun", "саун", "smart home", "клубн", "мансард", "mansard"]

def lux_from_text(text):
    if not isinstance(text, str):
        return 0
    t = text.lower()
    return int(any(k in t for k in LUX_KEYS))

def bathrooms_from_text(text):
    # "2 blocuri sanitare" / "3 санузла" -> 2.0 / 3.0. a second bathroom is one of
    # the strongest premium signals an ad can carry. no mention -> assume 1.
    if not isinstance(text, str):
        return 1.0
    m = re.search(r"(\d)\s*(?:blocuri sanitare|санузл)", text.lower())
    if m is None:
        return 1.0
    return min(float(m.group(1)), 4.0)

def clean_price(row):
    return _normalize_price(row.get("price_value"), row.get("price_unit"))[0]


def _normalize_price(value, unit):
    if not isinstance(unit, str) or unit not in ("UNIT_EUR", "UNIT_MDL", "UNIT_USD"):
        return None, "unsupported_currency"
    value = _finite_number(value)
    if value is None or value <= 0:
        return None, "invalid_price"
    if unit == "UNIT_MDL":
        return value / MDL_PER_EUR, None
    if unit == "UNIT_USD":
        return value * EUR_PER_USD, None
    return value, None

def clean_data(df, *, diagnostics=None):
    """Normalize source rows and replace optional diagnostic counts on success."""
    df = df.copy()
    input_rows = len(df)
    exclusions = {}

    # --- NUMERICAL FEATURES --- 

    values = df.get("price_value", [None] * len(df))
    units = df.get("price_unit", [None] * len(df))
    prices = [_normalize_price(value, unit) for value, unit in zip(values, units, strict=True)]
    df["price"] = [value for value, _ in prices]
    field_issues = dict(Counter(reason for _, reason in prices if reason is not None))

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
    field_issues["missing_or_invalid_coordinates"] = int(df["lat"].isna().sum())

    df["kitchen_area"] = df[KITCHEN_COL].apply(clean_kitchen)
    df["ceiling_height"] = df[CEILING_COL].apply(clean_ceiling)
    df["balcony_count"] = df[BALCONY_COL].apply(clean_balcony)
    df["photo_count"] = df[PHOTOS_COL].apply(clean_photos)
    df["bathrooms"] = df[TEXT_COL].apply(bathrooms_from_text)

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
    df["lux"] = df[TEXT_COL].apply(lux_from_text)

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

    before = len(df)
    df = df[(df["sector"] != "necunoscut") & (df["author"] != "necunoscut")]
    exclusions["missing_sector_or_author"] = before - len(df)

    # drop rows that lack the most important features
    before = len(df)
    df = df.dropna(subset=["price", "area", "rooms"])
    exclusions["missing_required_fields"] = before - len(df)

    # drop duplicated listings. a lot of apartments are reposted with another ad.
    # if one copy lands in train and another in validation, the model gets graded on flats
    # it has already seen and the metrics look better than they really are.
    # same key attributes + same price = same flat, i assume. 
    before = len(df)
    df = df.drop_duplicates(
        subset=["sector", "rooms", "area", "floor", "total_floors", "price"]
    )
    exclusions["duplicate"] = before - len(df)

    # remove obvious outliers (typos, daily-rate leftovers, bad areas)
    # the price cap is 2000 EUR/month on purpose: this model is for the mass
    # segment. the ~4% above it are premium flats whose price lives in things no
    # structured field captures (the residential complex, the finishes, the view),
    # so the model can only underprice them - and squared metrics then report
    # little else. pricing them is out of scope, and the README says so.
    for field, lower, upper in (("price", 100, 2000), ("area", 10, 400), ("rooms", 1, 6)):
        before = len(df)
        df = df[df[field].between(lower, upper)]
        exclusions[f"{field}_out_of_range"] = before - len(df)

    # two cheap derived flags, computed by the shared rule above
    flags = [floor_flags(f, t) for f, t in zip(df["floor"], df["total_floors"])]
    df["is_ground"] = [g for g, _ in flags]
    df["is_top"] = [t for _, t in flags]

    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(
            input_rows=input_rows,
            field_issues=field_issues,
            excluded_rows=exclusions,
            output_rows=len(df),
        )
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

def trim_knn_outliers(df, lo=0.5, hi=2.0):
    # drop listings asking under half or over double their own neighborhood's
    # going rate (the knn_ppm column, which must already be computed). those are
    # mostly aspirational asks and mislabeled ads, not the market - and the app's
    # whole job is to FLAG such listings, not to learn the market from them.
    # the thresholds are fixed constants, nothing is fitted, so train and
    # validation get exactly the same rule and nothing can leak.
    ratio = (df["price"] / df["area"]) / df["knn_ppm"]
    return df[(ratio >= lo) & (ratio <= hi)]

def impute_medians(df, medians=None):
    # fill missing numerics with medians. pass medians=None to fit them (train
    # split), or reuse the train medians for validation / new data.
    df = df.copy()
    if medians is None:
        medians = {c: float(df[c].median()) for c in IMPUTE_COLS}
    for column, median in medians.items():
        df[column] = df[column].fillna(median)
    return df, medians

# --- local market rate as a COARSE AGGREGATE ---------------------------------
# The market-rate lookup uses group medians instead of explicit per-row
# coordinate/rent tables. Grid/sector maps apply a minimum group size; the global
# fallback does not. This limits stored detail but is not a disclosure-risk proof.
GRID_PREC = 2          # decimals to round lat/lon to -> ~1 km cells
GRID_MIN_GROUP = 15    # default minimum for grid/sector rent maps only

def grid_key(lat, lon):
    return (round(float(lat), GRID_PREC), round(float(lon), GRID_PREC))

def _has_coords(lat, lon):
    return (lat is not None and lon is not None
            and not (np.isnan(lat) or np.isnan(lon)))

def build_ppm_grid(df, min_group=GRID_MIN_GROUP):
    # Returns grid/sector median EUR/m2 maps filtered by min_group, plus an
    # unguarded global median fallback. No group memberships/counts are returned.
    ppm = (df["price"] / df["area"]).values
    global_ppm = float(np.median(ppm))

    grid_vals, sector_vals = {}, {}
    for p, lat, lon, sec in zip(ppm, df["lat"], df["lon"], df["sector"]):
        if _has_coords(lat, lon):
            grid_vals.setdefault(grid_key(lat, lon), []).append(p)
        sector_vals.setdefault(sec, []).append(p)

    grid_ppm = {k: float(np.median(v)) for k, v in grid_vals.items()
                if len(v) >= min_group}
    sector_ppm = {k: float(np.median(v)) for k, v in sector_vals.items()
                  if len(v) >= min_group}
    return grid_ppm, sector_ppm, global_ppm

def ppm_from_grid(grid_ppm, sector_ppm, global_ppm, lat, lon, sector):
    # cell median -> sector median -> global median. same rule at train and serve.
    if _has_coords(lat, lon):
        cell = grid_key(lat, lon)
        if cell in grid_ppm:
            return grid_ppm[cell]
    if sector is not None:
        s = str(sector).strip().lower()
        if s in sector_ppm:
            return sector_ppm[s]
    return global_ppm

def assign_ppm(df, grid_ppm, sector_ppm, global_ppm):
    # the knn_ppm feature value for every row, from the coarse aggregate only
    return np.array([
        ppm_from_grid(grid_ppm, sector_ppm, global_ppm, lat, lon, sec)
        for lat, lon, sec in zip(df["lat"], df["lon"], df["sector"])
    ])
