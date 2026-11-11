"""Shared bundle loading, feature transformation and rent prediction."""

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
            f"Cannot read {path}. Run dvc repro and set PRET_DREPT_MODEL "
            "to a readable trusted model.joblib."
        ) from exc


@lru_cache(maxsize=1)
def _serving_bundle(path: Path) -> dict:
    bundle = load_bundle(path)
    # Evaluation uses the same fitted bundle without initializing explanations.
    import shap

    bundle["explainer"] = shap.TreeExplainer(bundle["model"])
    return bundle


def configured_model_path() -> Path:
    return Path(os.environ.get("PRET_DREPT_MODEL", MODEL_PATH))


def get_bundle() -> dict:
    return _serving_bundle(configured_model_path().expanduser().resolve())


def known_values(column: str) -> list[str]:
    """Fitted categories for the API's dropdowns and input validation."""
    vectorizer = get_bundle()["dv"]
    return sorted(
        name.split("=", 1)[1]
        for name in vectorizer.get_feature_names_out()
        if name.startswith(column + "=")
    )


def driver_label(raw_name: str) -> str:
    base = raw_name.split("=", 1)[0]
    if "=" not in raw_name and base in DRIVER_LABELS:
        return DRIVER_LABELS[base]
    return raw_name.replace("=", ": ").replace("_", " ")


def build_features(apartment: dict, bundle: dict) -> dict:
    values = {name: apartment.get(name) for name in bundle["features"]}
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
        values["lat"], values["lon"] = bundle["sector_latlon"].get(
            sector, bundle["median_latlon"]
        )
    if "dist_to_center" in values and values["dist_to_center"] is None:
        values["dist_to_center"] = latlon_to_km(values["lat"], values["lon"])
    if "knn_ppm" in values and values["knn_ppm"] is None:
        values["knn_ppm"] = ppm_from_grid(
            bundle["grid_ppm"],
            bundle["sector_ppm"],
            bundle["global_ppm"],
            values["lat"],
            values["lon"],
            apartment.get("sector"),
        )

    for name, value in values.items():
        if value is None:
            fallback = "necunoscut" if name in categorical else 0
            values[name] = bundle["numeric_defaults"].get(name, fallback)
    return values


def model_matrix(apartments: list[dict], bundle: dict) -> np.ndarray:
    return bundle["dv"].transform(
        [build_features(apartment, bundle) for apartment in apartments]
    )


def predict_eur(matrix: np.ndarray, bundle: dict) -> np.ndarray:
    predictions = np.expm1(bundle["model"].predict(matrix))
    if not (np.isfinite(predictions) & (predictions > 0)).all():
        raise ValueError("The model returned an invalid monthly rent.")
    return predictions


def prediction_drivers(matrix: np.ndarray, bundle: dict) -> list[dict]:
    """Describe the five strongest visible features present in this apartment."""
    shap_values = bundle["explainer"].shap_values(matrix)[0]
    names = bundle["dv"].get_feature_names_out()
    row = matrix[0]
    drivers = []
    for name, effect, present in zip(names, shap_values, row):
        if abs(effect) <= 0.001:
            continue
        base = name.split("=", 1)[0]
        if base in DRIVER_HIDDEN:
            continue
        # Explain only the categories and amenities present in this apartment.
        if ("=" in name or base in BINARY_SET) and present != 1:
            continue
        drivers.append((driver_label(name), float(effect)))

    # sort by how much they moved the price (biggest first)
    drivers.sort(key=lambda d: abs(d[1]), reverse=True)

    return [
        {"feature": name, "effect": "raises price" if effect > 0 else "lowers price"}
        for name, effect in drivers[:5]
    ]


def run(apartment: dict) -> dict:
    bundle = get_bundle()
    matrix = model_matrix([apartment], bundle)
    fair_price = float(predict_eur(matrix, bundle)[0])
    listed_price = apartment.get("price")
    result = {"fair_price": round(fair_price), "listed_price": listed_price}

    if listed_price:
        deviation = (listed_price - fair_price) / fair_price * 100
        result["deviation_pct"] = round(deviation, 1)
        if deviation > 15:
            result["verdict"] = "overpriced"
        elif deviation < -15:
            result["verdict"] = "good deal"
        else:
            result["verdict"] = "fair price"

    result["drivers"] = prediction_drivers(matrix, bundle)
    return result


def main() -> None:
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

    parser = argparse.ArgumentParser(
        description="Predict monthly asking rent for one apartment."
    )
    parser.add_argument("--model", type=Path, help="Trusted local model.joblib.")
    args = parser.parse_args()
    if args.model is not None:
        os.environ["PRET_DREPT_MODEL"] = str(args.model)
    try:
        print(json.dumps(run(example), indent=2, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, ModelUnavailableError) as exc:
        parser.exit(2, f"Prediction failed. {exc}\n")


if __name__ == "__main__":
    main()
