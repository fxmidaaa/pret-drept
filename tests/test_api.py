from fastapi.testclient import TestClient

import predict
from api import app

client = TestClient(app)

# a perfectly normal flat - the same example as in predict.py
GOOD_FLAT = {
    "rooms": 2,
    "area": 55,
    "floor": 3,
    "total_floors": 9,
    "sector": "centru",
    "author": "persoană fizică",
    "building_fund": "construcţii noi",
    "condition": "euroreparație",
    "autonomous_heating": 1,
    "furnished": 1,
    "elevator": 1,
    "parking": 0,
    "price": 700,
}

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_home_serves_the_site():
    r = client.get('/')
    assert r.status_code == 200
    assert "overpriced" in r.text

def test_options_has_the_dropdown_values():
    r = client.get('/options')
    assert r.status_code == 200
    opts = r.json()
    assert "centru" in opts["sector"]
    assert "secundar" in opts["building_fund"]
    assert "agenție" in opts["author"]
    # sector/author are never legitimately unknown - they must not be offered
    assert "necunoscut" not in opts["sector"]
    assert "necunoscut" not in opts["author"]

def test_predict_rejects_missing_author():
    flat = {k: v for k, v in GOOD_FLAT.items() if k != "author"}
    r = client.post("/predict", json=flat)
    assert r.status_code == 422

def test_drivers_never_show_absent_or_unset_features():
    # the explanation must only mention what the flat actually has: no "necunoscut"
    # category and no amenity the user left unchecked.
    flat = {**GOOD_FLAT, "air_conditioning": 0, "terrace": 0}
    data = client.post("/predict", json=flat).json()
    feats = [d["feature"] for d in data["drivers"]]
    assert not any("necunoscut" in f for f in feats)
    assert not any("air conditioning" in f for f in feats)
    assert not any("terrace" in f for f in feats)

def test_predict_a_normal_flat():
    r = client.post("/predict", json=GOOD_FLAT)
    assert r.status_code == 200
    data = r.json()
    # a 2-room in Centru cannot fairly rent for 50 or for 50000 EUR
    assert 200 < data["fair_price"] < 5000
    assert data["verdict"] in ("overpriced", "fair price", "good deal")
    assert 1 <= len(data["drivers"]) <= 5

def test_predict_without_asking_price_gives_no_verdict():
    flat = {k: v for k, v in GOOD_FLAT.items() if k != "price"}
    r = client.post("/predict", json=flat)
    assert r.status_code == 200
    assert "verdict" not in r.json()


def test_predict_rejects_negative_area():
    r = client.post("/predict", json={**GOOD_FLAT, "area": -5})
    assert r.status_code == 422

def test_predict_rejects_absurd_rooms():
    r = client.post("/predict", json={**GOOD_FLAT, "rooms": 100})
    assert r.status_code == 422

def test_predict_rejects_unknown_sector():
    # an unknown category would silently one-hot to all zeros -> nonsense
    # prediction. the api must refuse it instead.
    r = client.post("/predict", json={**GOOD_FLAT, "sector": "london"})
    assert r.status_code == 422

def test_sector_is_case_insensitive():
    r = client.post("/predict", json={**GOOD_FLAT, "sector": "Centru"})
    assert r.status_code == 200


def test_feature_dict_matches_the_model():
    # guards against building a feature under the wrong key (say "dist_center"
    # instead of "dist_to_center"): the vectorizer silently drops unknown keys
    # and the real feature falls back to a median default, so nothing crashes
    # and the bug is invisible. here the keys must match the model exactly.
    from features import latlon_to_km
    bund = predict.get_bundle()
    x = predict.build_features(dict(GOOD_FLAT), bund)
    assert set(x) == set(bund["features"])
    assert all(v is not None for v in x.values())
    # and the distance must really come from the coordinates, not from a default
    assert x["dist_to_center"] == latlon_to_km(x["lat"], x["lon"])

def test_golden_prediction_directly():
    # calling predict.run directly (no http): the flags get derived, the price
    # is sane, and the answer explains itself
    result = predict.run(dict(GOOD_FLAT))
    assert 200 < result["fair_price"] < 5000
    assert result["listed_price"] == 700
    assert "deviation_pct" in result

def test_bundle_ships_no_row_level_data():
    # privacy gate: the published model must contain only aggregates, never a
    # per-listing coordinate, price, id, or raw text. if any of these keys ever
    # comes back, the artifact is leaking training rows and must not ship.
    bund = predict.get_bundle()
    forbidden = {
        "knn_points", "knn_ppm_values", "listings", "raw", "coords",
        "lat_values", "lon_values", "ids", "text", "urls",
    }
    present = forbidden & set(bund)
    assert not present, f"forbidden row-level keys in bundle: {present}"

    # the market-rate aggregate must be scalars keyed by coarse cell/sector,
    # not arrays of individual rows
    for value in bund["grid_ppm"].values():
        assert isinstance(value, float)
    for value in bund["sector_ppm"].values():
        assert isinstance(value, float)
    assert isinstance(bund["global_ppm"], float)
