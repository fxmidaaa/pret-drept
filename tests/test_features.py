import numpy as np
import pandas as pd 
import pytest

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import features

from features import (
    floor_flags, parse_latlon, latlon_to_km, first_number, clean_rooms,
    clean_text, to_flag, clean_parking, clean_balcony, clean_photos,
    clean_kitchen, clean_ceiling, condition_from_text, utilities_from_text,
    lux_from_text, bathrooms_from_text, clean_price, clean_data,
    build_ppm_grid, ppm_from_grid, trim_ppm_outliers, trim_knn_outliers,
    impute_medians
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

def test_lux_from_text():
    assert lux_from_text("Penthouse spațios cu jacuzzi") == 1
    assert lux_from_text("Amplasat în bloc de clasă Premium") == 1
    assert lux_from_text("квартира люкс с сауной") == 1
    assert lux_from_text("apartament obișnuit lângă parc") == 0
    assert lux_from_text(float("nan")) == 0

def test_bathrooms_from_text():
    assert bathrooms_from_text("2 dormitoare, 2 blocuri sanitare, antreu") == 2.0
    assert bathrooms_from_text("гостиная, 3 санузла") == 3.0
    # no mention of bathrooms -> assume the usual one
    assert bathrooms_from_text("apartament frumos in centru") == 1.0
    assert bathrooms_from_text(None) == 1.0

# --- price: usd/mdl -> eur ---

def test_clean_price():
    assert clean_price({"price_value": 500, "price_unit": "UNIT_EUR"}) == 500.0
    # 9750 MDL / 19.5 = exactly 500 EUR
    assert clean_price({"price_value": 9750, "price_unit": "UNIT_MDL"}) == 500.0
    assert clean_price({"price_value": 100, "price_unit": "UNIT_USD"}) == 92.0
    assert clean_price({"price_value": None, "price_unit": "UNIT_EUR"}) is None
    assert clean_price({"price_value": float("nan"), "price_unit": "UNIT_EUR"}) is None

# --- clean_data end to end
# a tiny fake scrape with known problems in it, and we check that each problem gets handled:
# the duplicate, missing area, ...

def make_listing(**overrides):
    row = {
        "price_value": 500, "price_unit": "UNIT_EUR",
        features.ROOMS_COL: "Apartament cu 2 camere",
        features.AREA_COL: "50",
        features.FLOOR_COL: "3",
        features.TOTAL_FLOORS_COL: "9",
        features.MAP_COL: '{"lat": 47.02, "lon": 28.83}',
        features.KITCHEN_COL: "10",
        features.CEILING_COL: "2.8",
        features.BALCONY_COL: "1",
        features.PHOTOS_COL: "a.jpg,b.jpg",
        features.HEATING_COL: True,
        features.FURNISHED_COL: True,
        features.ELEVATOR_COL: True,
        features.PARKING_COL: None,
        features.AC_COL: None,
        features.FLOOR_HEATING_COL: None,
        features.TERRACE_COL: None,
        features.PANORAMIC_COL: None,
        features.TEXT_COL: "apartament frumos in centru",
        features.SECTOR_COL: "Centru",
        features.FUND_COL: "Construcţii noi",
        features.CONDITION_COL: "Euroreparație",
        features.AUTHOR_COL: "Agenție",
        features.BUILDING_TYPE_COL: "Bloc nou",
    }
    row.update(overrides)
    return row

def test_clean_data():
    rows = [
        make_listing(), # just a normal rent
        make_listing(), # exact duplicate of the first
        make_listing(**{features.AREA_COL: None}), # should be dropped if no area
        make_listing(price_value=5),
        make_listing(price_value=14040, price_unit='UNIT_MDL', **{features.AREA_COL: '60'}),
        make_listing(**{features.CONDITION_COL: None,
                        features.TEXT_COL: "квартира с евроремонтом",
                        features.AREA_COL: "41.7", "price_value": 500})
    ]

    rows[0]["price_value"] = 600
    rows[1]["price_value"] = 600
    rows[5]["price_value"] = 500.4 # 500.4 / 41.7 = 12.0

    df = clean_data(pd.DataFrame(rows))

    assert len(df) == 3

    # checking if mdl -> eur (14040 mdl -> 720 eur)
    assert any(math.isclose(p, 720.0) for p in df['price'])


@pytest.mark.parametrize("unit", [None, "", "UNIT_UNKNOWN", "EUR", 1, ["UNIT_EUR"]])
def test_price_requires_a_supported_currency(unit):
    assert clean_price({"price_value": 500, "price_unit": unit}) is None


@pytest.mark.parametrize(
    "value",
    [
        True,
        [],
        {},
        "invalid",
        "NaN",
        "Infinity",
        float("inf"),
        -500,
        0,
        pytest.param(10**400, id="oversized-integer"),
    ],
)
def test_price_requires_a_positive_finite_number(value):
    assert clean_price({"price_value": value, "price_unit": "UNIT_EUR"}) is None


@pytest.mark.parametrize(
    "value, expected",
    [
        ("-55", -55.0),
        ("−55", -55.0),
        ("- 55 m²", -55.0),
        ("-.5", -0.5),
        ("+3,5", 3.5),
        ("-1e2", -100.0),
        (-55, -55.0),
    ],
)
def test_numeric_extraction_preserves_sign(value, expected):
    assert first_number(value) == expected


@pytest.mark.parametrize("value", [True, [55], {"value": 55}, float("inf"), "1e309"])
def test_numeric_extraction_rejects_unsupported_or_nonfinite_values(value):
    assert first_number(value) is None


@pytest.mark.parametrize(
    "value",
    [
        '{"lat":"47.02","lon":"28.83"}',
        '{"lat":true,"lon":28.83}',
        '{"lat":47.02,"lon":Infinity}',
        "[]",
        "null",
    ],
)
def test_coordinate_representation_rejection_does_not_raise(value):
    assert parse_latlon(value) == (None, None)


def test_negative_optional_measurements_are_not_made_positive():
    assert clean_kitchen("-10") is None
    assert clean_ceiling("-2.8") is None
    assert clean_balcony("-2") == 0


def test_clean_data_reports_aggregate_normalization_and_exclusion_reasons():
    rows = [
        make_listing(),
        make_listing(price_unit="SYNTHETIC_PRIVATE_UNIT"),
        make_listing(price_value="SYNTHETIC_PRIVATE_AMOUNT"),
        make_listing(**{features.AREA_COL: "-55"}),
        make_listing(price_value=600, **{features.MAP_COL: '{"lat":"47.02","lon":"28.83"}'}),
        make_listing(price_value=700, **{features.ROOMS_COL: "-2"}),
        make_listing(),
        make_listing(**{features.SECTOR_COL: None}),
        make_listing(**{features.AREA_COL: None}),
        make_listing(price_value=50),
        make_listing(price_value=1000, price_unit="UNIT_USD"),
    ]
    original = pd.DataFrame(rows)
    before = original.copy(deep=True)
    diagnostics = {"previous": "stale"}
    cleaned = clean_data(original, diagnostics=diagnostics)
    pd.testing.assert_frame_equal(original, before)
    assert sorted(cleaned["price"]) == [500, 600, 920]
    assert cleaned.loc[4, ["lat", "lon", "dist_to_center"]].isna().all()
    assert diagnostics == {
        "input_rows": 11,
        "field_issues": {
            "unsupported_currency": 1,
            "invalid_price": 1,
            "missing_or_invalid_coordinates": 1,
        },
        "excluded_rows": {
            "missing_sector_or_author": 1,
            "missing_required_fields": 3,
            "duplicate": 1,
            "price_out_of_range": 1,
            "area_out_of_range": 1,
            "rooms_out_of_range": 1,
        },
        "output_rows": 3,
    }
    pd.testing.assert_frame_equal(cleaned, clean_data(original))


def test_clean_data_accepts_an_empty_frame_with_the_source_columns():
    empty = pd.DataFrame(columns=make_listing())
    diagnostics = {}
    assert clean_data(empty, diagnostics=diagnostics).empty
    assert diagnostics["input_rows"] == diagnostics["output_rows"] == 0
    assert sum(diagnostics["field_issues"].values()) == 0
    assert sum(diagnostics["excluded_rows"].values()) == 0


def test_missing_currency_column_excludes_rows_and_reports_the_reason():
    source = pd.DataFrame([make_listing()]).drop(columns="price_unit")
    diagnostics = {}
    assert clean_data(source, diagnostics=diagnostics).empty
    assert diagnostics["field_issues"]["unsupported_currency"] == 1
    assert diagnostics["excluded_rows"]["missing_required_fields"] == 1


def test_failed_normalization_preserves_the_previous_report():
    source = pd.DataFrame([make_listing()]).drop(columns=features.AREA_COL)
    diagnostics = {"previous_report": 1}
    with pytest.raises(KeyError):
        clean_data(source, diagnostics=diagnostics)
    assert diagnostics == {"previous_report": 1}


def test_training_entry_point_prints_safe_normalization_counts(tmp_path, monkeypatch, capsys):
    import json

    import train

    rows = pd.DataFrame([make_listing(), make_listing(price_unit="SYNTHETIC_PRIVATE_UNIT")])
    monkeypatch.setattr(train.pd, "read_csv", lambda path: rows)
    monkeypatch.setattr(train, "BASE", str(tmp_path))

    class ReachedSplit(Exception):
        pass

    def stop_before_fitting(cleaned, **kwargs):
        assert list(cleaned["price"]) == [500]
        raise ReachedSplit

    monkeypatch.setattr(train, "train_test_split", stop_before_fitting)
    with pytest.raises(ReachedSplit):
        train.main()
    output = capsys.readouterr().out
    prefix = "normalization diagnostics: "
    line = next(line for line in output.splitlines() if line.startswith(prefix))
    report = json.loads(line.removeprefix(prefix))
    assert report["field_issues"]["unsupported_currency"] == 1
    assert report["input_rows"] == 2 and report["output_rows"] == 1
    assert "SYNTHETIC_PRIVATE_UNIT" not in output
    assert not (tmp_path / "model.joblib").exists()


# --- outlier trimming and imputation (fit on train, reuse on val) ---


def test_trim_ppm_outliers_reuses_train_bounds():
    # 100 ordinary flats + one absurdly expensive one: fitting must drop the
    # extremes, and a second dataframe must be judged by the SAME bounds
    # (not its own), otherwise validation rows leak into the decision.
    train = pd.DataFrame({"price": [500.0] * 100 + [5000.0], "area": [50.0] * 101})
    trimmed, bounds = trim_ppm_outliers(train)
    assert len(trimmed) < len(train)

    val = pd.DataFrame({"price": [500.0, 5000.0], "area": [50.0, 50.0]})
    val_trimmed, _ = trim_ppm_outliers(val, bounds)
    assert list(val_trimmed["price"]) == [500.0]

def test_trim_knn_outliers():
    # 10 EUR/m2 next to 10 EUR/m2 neighbors stays; asking 4x the neighborhood
    # rate (or a fifth of it) is not a market price and must go
    df = pd.DataFrame({
        "price": [500.0, 2000.0, 100.0],
        "area": [50.0, 50.0, 50.0],
        "knn_ppm": [10.0, 10.0, 10.0],
    })
    out = trim_knn_outliers(df)
    assert list(out["price"]) == [500.0]

def test_impute_medians_reuses_train_medians():
    cols = ["floor", "total_floors", "dist_to_center",
            "lat", "lon", "kitchen_area", "ceiling_height"]
    train = pd.DataFrame({c: [1.0, 3.0, np.nan] for c in cols})
    train_filled, medians = impute_medians(train)
    assert not train_filled.isna().any().any()
    assert medians["floor"] == 2.0  # median of 1 and 3

    # a validation row with a hole gets the TRAIN median, not its own
    val = pd.DataFrame({c: [np.nan] for c in cols})
    val_filled, _ = impute_medians(val, medians)
    assert val_filled["floor"].iloc[0] == 2.0

# --- market rate as a coarse grid aggregate ---

def ppm_df(lats, lons, ppms, sectors=None, area=50.0):
    n = len(lats)
    return pd.DataFrame({
        "lat": lats,
        "lon": lons,
        "sector": sectors if sectors is not None else ["centru"] * n,
        "area": [area] * n,
        "price": [p * area for p in ppms],
    })

def test_build_ppm_grid_only_keeps_big_groups():
    # 20 flats in one ~1 km cell (kept) + 3 flats far away (dropped: < min_group).
    # the aggregate must expose the dense cell only, never the sparse one.
    df = ppm_df(
        lats=[47.02] * 20 + [47.08, 47.08, 47.08],
        lons=[28.83] * 20 + [28.90, 28.90, 28.90],
        ppms=[10.0] * 20 + [99.0, 99.0, 99.0],
    )
    grid_ppm, sector_ppm, global_ppm = build_ppm_grid(df, min_group=15)
    assert len(grid_ppm) == 1                     # only the dense cell survives
    assert list(grid_ppm.values())[0] == 10.0     # median of the dense cell
    assert 99.0 not in grid_ppm.values()          # the sparse cell is not published

def test_ppm_from_grid_falls_back_cell_then_sector_then_global():
    grid_ppm = {(47.02, 28.83): 10.0}
    sector_ppm = {"centru": 12.0}
    global_ppm = 15.0
    # a known cell -> cell median
    assert ppm_from_grid(grid_ppm, sector_ppm, global_ppm, 47.02, 28.83, "centru") == 10.0
    # unknown cell but known sector -> sector median
    assert ppm_from_grid(grid_ppm, sector_ppm, global_ppm, 46.95, 28.99, "centru") == 12.0
    # no coords, unknown sector -> global median
    assert ppm_from_grid(grid_ppm, sector_ppm, global_ppm, None, None, "necunoscut") == 15.0
