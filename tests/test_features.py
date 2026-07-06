import numpy as np
import pandas as pd 

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import features

from features import (
    floor_flags, parse_latlon, latlon_to_km, first_number, clean_rooms,
    clean_text, to_flag, clean_parking, clean_balcony, clean_photos,
    clean_kitchen, clean_ceiling, condition_from_text, utilities_from_text,
    clean_price, clean_data, knn_market_rate
)

def test_first_number():
    assert first_number("62") == 62.0
    assert first_number("Apartament cu 3 camere") == 3.0
    assert first_number("3,5") == 3.5
    assert first_number(None) is None
    assert first_number(float("nan")) is None
    assert first_number("fara numar") is None

def test_clean_rooms():
    assert clean_rooms("Apartament cu 2 camere") == 2.0
    assert clean_rooms("O cameră") == 1.0
    assert clean_rooms(None) is None

def test_clean_text():
    assert clean_text("  Centru ") == "centru"
    assert clean_text(float("nan")) == "necunoscut"
    assert clean_text(None) == "necunoscut"

def test_to_flag():
    assert to_flag(True) == 1
    assert to_flag("Da") == 1
    assert to_flag(False) == 0
    assert to_flag(float("nan")) == 0
    assert to_flag(None) == 0

def test_clean_parking():
    assert clean_parking("Subterană") == 1
    assert clean_parking("Deschis") == 1
    assert clean_parking("Nu") == 0
    assert clean_parking(float("nan")) == 0

def test_clean_balcony():
    assert clean_balcony("2") == 2
    assert clean_balcony("4 și mai multe") == 4   # capped at 4
    assert clean_balcony("Nu") == 0
    assert clean_balcony(None) == 0

# --- ceiling height: same value, three different units ---

def test_clean_ceiling_units():
    assert clean_ceiling("3") == 3.0
    assert clean_ceiling("28") == 2.8
    assert clean_ceiling("280") == 2.8
    assert clean_ceiling("2.7") == 2.7

def test_clean_ceiling_garbage():
    assert clean_ceiling("5") is None
    assert clean_ceiling("100") is None
    assert clean_ceiling("0") is None
    assert clean_ceiling(None) is None

# -- gps --

def test_parse_latlon():
    lat, lon = parse_latlon('{"lat": 47.02, "lon": 28.83}')
    assert lat == 47.02 and lon == 28.83

def test_parse_latlon_rejects_bad_input():
    # coordinates outside chisinau are someone's typo, not a listing on the moon
    assert parse_latlon('{"lat": 48.0, "lon": 28.83}') == (None, None)
    assert parse_latlon("not json at all") == (None, None)
    assert parse_latlon(float("nan")) == (None, None)
    assert parse_latlon('{"lat": 47.02}') == (None, None)

def test_latlon_to_km():
    # the centre is 0 km from the centre
    assert latlon_to_km(features.CENTER_LAT, features.CENTER_LON) == 0.0
    # ~1 degree of latitude is ~111 km, so 0.01 deg should be ~1.1 km
    d = latlon_to_km(features.CENTER_LAT + 0.01, features.CENTER_LON)
    assert math.isclose(d, 1.11, rel_tol=0.01)

# --- floor flags ---

def test_floor_flags():
    assert floor_flags(1, 9) == (1, 0)
    assert floor_flags(9, 9) == (0, 1)
    assert floor_flags(1, 1) == (1, 1)
    assert floor_flags(3, 9) == (0, 0)
    assert floor_flags(None, 9) == (0, 0) # unknown floor -> assume neither
    assert floor_flags(3, None) == (0, 0)

# --- reading the ad text (romanian and russian) ---

def test_condition_from_text():
    assert condition_from_text("Apartament superb cu euroreparație!") == "euroreparație"
    assert condition_from_text("Сдается квартира, свежий евроремонт") == "euroreparație"
    assert condition_from_text("varianta alba, bloc nou") == "variantă albă"
    assert condition_from_text("apartament la pret bun") is None
    assert condition_from_text(float("nan")) is None

def test_utilities_from_text():
    assert utilities_from_text("300 euro, comunale incluse") == 1
    assert utilities_from_text("аренда, все включено") == 1
    # "+ comunale" means utilities are ON TOP of the rent - must NOT match
    assert utilities_from_text("chirie 300 euro + comunale") == 0
    assert utilities_from_text(float("nan")) == 0

# --- price: usd/mdl -> eur ---

def test_clean_price():
    assert clean_price({"price_value": 500, "price_unit": "UNIT_EUR"}) == 500.0
    # 9750 MDL / 19.5 = exactly 500 EUR
    assert clean_price({"price_value": 9750, "price_unit": "UNIT_MDL"}) == 500.0
    assert clean_price({"price_value": 100, "price_unit": "UNIT_USD"}) == 92.0
    assert clean_price({"price_value": None, "price_unit": "UNIT_EUR"}) is None
    assert clean_price({"price_value": float("nan"), "price_unit": "UNIT_EUR"}) is None