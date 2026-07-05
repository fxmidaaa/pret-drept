import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib

from datetime import date
import os

from features import clean_data, knn_market_rate, FEATURES, numerical, LON_SCALE

BASE = os.path.dirname(os.path.abspath(__file__))

def rmse(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

def main():
    # load and clean the data (999.md monthly rent)
    df = pd.read_csv(os.path.join(BASE, "data", "raw", "listings.csv"))
    print("raw rows:", len(df))
    df = clean_data(df)
    print("rows after cleaning:", len(df))

    # split the data into train and validation first:
    # the knn feature must look only at train, or the data will leak
    df_train, df_val = train_test_split(df, test_size=0.2, random_state=42)
    df_train, df_val = df_train.copy(), df_val.copy()

    df_train['knn_ppm'] = knn_market_rate(df_train, df_train, exclude_self=True)
    df_val['knn_ppm'] = knn_market_rate(df_train, df_val)
    features = FEATURES + ['knn_ppm']

    y_train = np.log1p(df_train['price'].values)
    y_val = np.log1p(df_val['price'].values)

    dicts_train = df_train[features].to_dict(orient='records')
    dicts_val = df_val[features].to_dict(orient='records')

    # one-hot encoding using dicts
    dv = DictVectorizer(sparse=False)
    X_train = dv.fit_transform(dicts_train)
    X_val = dv.transform(dicts_val)

    linreg = LinearRegression()
    linreg.fit(X_train, y_train)
    base_pred = np.expm1(linreg.predict(X_val))
    print('linear regression RMSE: ')
    print(round(rmse(np.expm1(y_val), base_pred)), "EUR")

    # to understand why exactly these hyperparameters, check model_comparison.ipynb.
    model = XGBRegressor(
        n_estimators = 600,
        max_depth = 6,
        learning_rate = 0.05,
        subsample = 0.83,
        colsample_bytree = 0.77,
        min_child_weight = 7
    )

    model.fit(X_train, y_train)
    pred = np.expm1(model.predict(X_val))
    true = np.expm1(y_val)
    mape = np.mean(np.abs((true - pred) / true)) * 100

    print("RMSE:", round(rmse(true, pred)), "EUR")
    print("MAE:", round(mean_absolute_error(true, pred)), "EUR")
    print("MAPE:", round(mape, 1), "%")
    print("R2:", round(r2_score(true, pred), 3))

    # R2 in log space too: the euro-space R2 is dominated by the expensive tail,
    # the log-space one weighs every listing more equally
    print("  R2 (log-space):", round(r2_score(y_val, model.predict(X_val)), 3))

    # 8. save the vectorizer + model together so predict.py can use them.
    #    also save the median distance-to-centre per sector + overall, so the app can
    #    fill in dist_center from the chosen sector (a user won't type gps coordinates).
    #    meta records when/on what/how well this model was trained - model.joblib
    #    gets overwritten on every retrain, so without this there is no way to tell
    #    which model you are actually serving.
    #    the bundle also carries everything predict.py needs to fill in features a
    #    web user can't type: typical coordinates per sector, the training listings'
    #    coordinates + EUR/m2 (for the knn feature), and median defaults for the
    #    numeric fields nobody fills in by hand (photo count, ceiling height, blablabla).
    sector_dist = df.groupby("sector")["dist_to_center"].median().to_dict()
    sector_latlon = {s: [float(g["lat"].median()), 
                         float(g["lon"].median())]
                     for s, g in df.groupby("sector")} 
    joblib.dump({
        "dv": dv,
        "model": model,
        "features": features,
        "sector_dist": sector_dist,
        "median_dist": float(df["dist_to_center"].median()),
        "sector_latlon": sector_latlon,
        "median_latlon": [float(df["lat"].median()), float(df["lon"].median())],
        "numeric_defaults": {c: float(df_train[c].median()) for c in numerical},
        "knn_points": np.column_stack([df_train["lat"].values,
                                       df_train["lon"].values * LON_SCALE]),
        "knn_ppm_values": (df_train["price"] / df_train["area"]).values,
        "meta": {
            "trained_at": date.today().isoformat(),
            "n_listings": len(df),
            "rmse_eur": round(rmse(true, pred)),
            "mae_eur": round(mean_absolute_error(true, pred)),
            "mape_pct": round(mape, 1),
            "r2": round(r2_score(true, pred), 3),
        },
    }, os.path.join(BASE, 'model.joblib'))
    print('saved model to model.joblib')


if __name__ == "__main__":
    main()




