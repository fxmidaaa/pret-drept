import numpy as np
import joblib
import shap

from features import floor_flags, latlon_to_km, LON_SCALE, categorical

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")