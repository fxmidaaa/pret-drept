# The data from 999.md comes with romanian column names and mixed value types
# (numbers, text labels, True/None booleans). Before training I turn it into clean
# numbers and categories. I keep this in its own file so train.py and predict.py
# use exactly the same columns - otherwise the model would get confused.

import numpy as np
import json
import re

MDL_PER_EUR = 19.5
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

# I turn each listing's gps coordinate into a distance-to-center in km. (Chisinau city centre)
CENTER_LAT, CENTER_LON = 47.0245, 28.8322 # piata marii adunari nationale 
LON_SCALE = 0.682   # cos(47 deg): 1 deg of longitude is shorter than 1 deg of latitude here

numerical = ["rooms", "area", "floor", "total_floors", "dist_center"]
binary = ["autonomous_heating", "furnished", "elevator", "parking", "is_ground", "is_top"]
categorical = ["sector", "building_fund", "condition"]
features = numerical + binary + categorical

def distance_to_center(harta):
    # 'Harta' is a json string like {"lat": 47.03, "lon": 28.80}. Turn it into the
    # approximate distance in km from the city centre. Bad / missing coords -> None.
    try:
        h = json.loads(harta) if isinstance(harta, str) else {}
        lat, lon = h.get("lat"), h.get("lon")

    except Exception:
        return None
    
    if lat is None or lon is None:
        return None
    
    if not (46.9 < lat < 47.1 and 28.74 < lon < 28.95):
        return None
    
    dlat = lat - CENTER_LAT
    dlon = lon - CENTER_LON

    return float(np.sqrt(dlat ** 2 + dlon ** 2) * 111.0) # degrees into kilometers (thanks to geography in lyceum)

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
        return value * 0.92 # roughly USD to EUR, very few of these
    return value      