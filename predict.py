import argparse
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from features import binary, categorical, floor_flags, latlon_to_km, ppm_from_grid

BINARY_SET = set(binary)
# real model inputs that just aren't meaningful to show as a "driver": raw
# coordinates, a listing-quality proxy, and distance (redundant with sector).
DRIVER_HIDDEN = {"lat", "lon", "photo_count", "dist_to_center"}
# friendlier labels for a few opaque feature names
DRIVER_LABELS = {"knn_ppm": "nearby rents", "lux": "premium finishes"}

MODEL_PATH = Path(__file__).resolve().with_name("model.joblib")


class ModelUnavailableError(RuntimeError):
    pass


def load_bundle(path: Path) -> dict:
    """Load a trusted local bundle. Joblib may execute code during deserialization."""
    try:
        return joblib.load(path)
    except OSError as exc:
        raise ModelUnavailableError(
            f"Cannot read {path}. Run the demo pipeline and set PRET_DREPT_MODEL "
            "to a readable trusted model.joblib."
        ) from exc


@lru_cache(maxsize=1)
def _serving_bundle(path: Path) -> dict:
    bundle = load_bundle(path)
    # Evaluation uses the same fitted bundle without initializing explanations.
    import shap

    bundle["explainer"] = shap.TreeExplainer(bundle["model"])
    return bundle


def get_bundle() -> dict:
    path = Path(os.environ.get("PRET_DREPT_MODEL", MODEL_PATH)).expanduser().resolve()
    return _serving_bundle(path)


def known_values(column):
    # the category values the model was actually trained on
    # for example, known_values("sector"). the API uses this for the dropdowns and 
    # for rejecting requests with categories the model has never seen.

    dv = get_bundle()['dv']
    return sorted(
        n.split('=', 1)[1] for n in dv.get_feature_names_out()
        if n.startswith(column + '=')
    )

def nice_name(raw_name):
    # dictvectorizer makes names like 'sector=centru' or 'area'
    # i will make them a bit nicer to read in the explanation
    return raw_name.replace('=', ': ').replace('_', ' ')

def driver_label(raw_name):
    base = raw_name.split('=', 1)[0]
    if '=' not in raw_name and base in DRIVER_LABELS:
        return DRIVER_LABELS[base]
    return nice_name(raw_name)

def build_features(apartment: dict, bund: dict) -> dict:
    values = {name: apartment.get(name) for name in bund["features"]}
    for name, value in values.items():
        if isinstance(value, (float, np.floating)) and np.isnan(value):
            values[name] = None

    if values.get("is_ground") is None or values.get("is_top") is None:
        values["is_ground"], values["is_top"] = floor_flags(
            values.get("floor"), values.get("total_floors")
        )

    # July bundles can still use coordinates and a fitted market grid.
    if "lat" in values and (values["lat"] is None or values["lon"] is None):
        sector = str(apartment.get("sector", "")).strip().lower()
        values["lat"], values["lon"] = bund["sector_latlon"].get(sector, bund["median_latlon"])
    if "dist_to_center" in values and values["dist_to_center"] is None:
        values["dist_to_center"] = latlon_to_km(values["lat"], values["lon"])
    if "knn_ppm" in values and values["knn_ppm"] is None:
        values["knn_ppm"] = ppm_from_grid(
            bund["grid_ppm"],
            bund["sector_ppm"],
            bund["global_ppm"],
            values["lat"],
            values["lon"],
            apartment.get("sector"),
        )

    for name, value in values.items():
        if value is None:
            fallback = "necunoscut" if name in categorical else 0
            values[name] = bund["numeric_defaults"].get(name, fallback)
    return values


def model_matrix(apartments: list[dict], bundle: dict) -> np.ndarray:
    return bundle["dv"].transform([build_features(apartment, bundle) for apartment in apartments])


def predict_eur(matrix: np.ndarray, bundle: dict) -> np.ndarray:
    predictions = np.expm1(bundle["model"].predict(matrix))
    if not (np.isfinite(predictions) & (predictions > 0)).all():
        raise ValueError("The model returned an invalid monthly rent.")
    return predictions


def run(apartment):
    bund = get_bundle()
    dv = bund["dv"]
    listed_price = apartment.get("price")
    X = model_matrix([apartment], bund)
    fair_price = float(predict_eur(X, bund)[0])

    result = {'fair_price': round(fair_price), 'listed_price': listed_price}

    if listed_price:
        deviation = (listed_price - fair_price) / fair_price * 100
        result["deviation_pct"] = round(deviation, 1)
        if deviation > 15:
            result["verdict"] = "overpriced"
        elif deviation < -15:
            result["verdict"] = "good deal"
        else:
            result["verdict"] = "fair price"

    shap_values = bund["explainer"].shap_values(X)[0]
    names = dv.get_feature_names_out()
    row = X[0]  # the encoded feature values, aligned with names/shap_values

    drivers = []
    for name, val, present in zip(names, shap_values, row):
        if abs(val) <= 0.001:
            continue
        base = name.split('=', 1)[0]
        if base in DRIVER_HIDDEN:
            continue
        # for a one-hot category, only explain the value the flat actually has;
        # for a yes/no, only explain it when it's present. otherwise the
        # box fills with things the user never entered ("author: necunoscut") or
        # the confusing zero side of a one-hot ("building fund: new build lowers
        # rent" when they picked secondary).
        if ('=' in name or base in BINARY_SET) and present != 1:
            continue
        drivers.append((driver_label(name), float(val)))

    # sort by how much they moved the price (biggest first)
    drivers.sort(key=lambda d: abs(d[1]), reverse=True)

    result["drivers"] = [
        {"feature": n, "effect": "raises price" if v > 0 else "lowers price"}
        for n, v in drivers[:5]
    ]
    return result

if __name__ == "__main__":
    example = {
        "rooms": 2,
        "area": 55,
        "floor": 3,
        "total_floors": 9,
        "autonomous_heating": 1,
        "furnished": 1,
        "elevator": 1,
        "parking": 0,
        "sector": "centru",
        "author": "persoană fizică",
        "building_fund": "construcţii noi",
        "condition": "euroreparație",
        "price": 700,
    }

    parser = argparse.ArgumentParser(description="Predict monthly asking rent for one apartment.")
    parser.add_argument("--model", type=Path, help="Trusted local model.joblib.")
    args = parser.parse_args()
    if args.model is not None:
        os.environ["PRET_DREPT_MODEL"] = str(args.model)
    try:
        print(json.dumps(run(example), indent=2, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, ModelUnavailableError) as exc:
        parser.exit(2, f"Prediction failed. {exc}\n")