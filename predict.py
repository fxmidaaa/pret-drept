import numpy as np
import joblib
import os
import shap

from features import floor_flags, latlon_to_km, LON_SCALE, categorical

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.joblib')

# to optimize prediction time and not to use for every single prediction model loading, i use 
# a container dictionary that holds everything i need to make a prediction. 
# it is loaded once from model.joblib and reused for every prediction
_bundle = None

def get_bundle():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)

        # shap explainer for my xgboost model, explains one prediction at a time
        _bundle['explainer'] = shap.TreeExplainer(_bundle['model'])

        meta = _bundle.get('meta', {})
        if meta:
            print(f'loaded model trained {meta.get("trained_at")} '
                  f'on {meta.get("n_listings")} listings '
                  f'(val RMSE {meta.get('rmse_eur')} EUR, MAPE {meta.get('mape_pct')}%)')
    return _bundle

def known_values(column):
    # the category values the model was actually trained on
    # for example, known_values("sector"). the API uses this for the dropdowns and 
    # for rejecting requests with categories the model has never seen.

    dv = get_bundle()['dv']
    return sorted(
        n.split('=', 1)[1] for n in dv.get_feature_names_out()
        if n.startswith(column + '=')
    )

def knn_ppm_at(bundle, lat, lon, k=15):
    points = bundle['knn_points']
    diameter2 = (points[:, 0] - lat) ** 2 + (points[:, 1] - lon * LON_SCALE) ** 2
    idx = np.argsort(diameter2)[:k]
    return float(np.median(bundle['knn_ppm_values'][idx]))

def nice_name(raw_name):
    # dictvectorizer makes names like 'sector=centru' or 'area'
    # i will make them a bit nicer to read in the explanation
    return raw_name.replace('=', ': ').replace('_', ' ')

def run(apartment):
    bund = get_bundle()
    dv = bund['dv']
    listed_price = apartment.get('price')

    # keep only the columns the model knows, turn into the vectorizer format
    x_dict = {f: apartment.get(f) for f in bund['features']}

    # derive the ground/top floor flags if the caller didn't send them -
    # the rule lives in features.floor_flags so it can't drift from training

    if x_dict.get("is_ground") is None or x_dict.get("is_top") is None:
        is_ground, is_top = floor_flags(apartment.get("floor"), apartment.get("total_floors"))
        x_dict["is_ground"], x_dict["is_top"] = is_ground, is_top

    if x_dict.get("lat") is None or x_dict.get("lon") is None:
        sector = str(apartment.get("sector", "")).strip().lower()
        x_dict["lat"], x_dict["lon"] = bund["sector_latlon"].get(sector, bund["median_latlon"])

    if x_dict.get("dist_center") is None:
        x_dict["dist_center"] = latlon_to_km(x_dict["lat"], x_dict["lon"])
    if x_dict.get("knn_ppm") is None:
        x_dict["knn_ppm"] = knn_ppm_at(bund, x_dict["lat"], x_dict["lon"])

    for feature, value in x_dict.items():
        if value is None:
            if feature in bund["numeric_defaults"]:
                x_dict[feature] = bund["numeric_defaults"][feature]
            elif feature in categorical:
                x_dict[feature] = "necunoscut"
            else:
                x_dict[feature] = 0

    X = dv.transform([x_dict])

    fair_price = float(np.expm1(bund['model'].predict(X)[0]))

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

    drivers = []
    for name, val in zip(names, shap_values):
        if abs(val) > 0.001:
            drivers.append((nice_name(name), float(val)))

    # sort by how much they moved the price (biggest first)
    drivers.sort(key=lambda x: abs(x[1]), reverse=True)

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
        "building_fund": "construcţii noi",
        "condition": "euroreparație",
        "price": 700,
    }

    from pprint import pprint
    pprint(run(example))