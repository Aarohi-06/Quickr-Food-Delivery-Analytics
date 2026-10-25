"""Shared validated inference for the app and command-line checks."""
import math
import joblib
import pandas as pd
from ml.features import NUMERIC, CATEGORICAL, FEATURES
from quickr.config import ROOT


def load_model():
    path = ROOT / "models/delivery_duration_pipeline.joblib"
    if not path.is_file():
        raise FileNotFoundError("Train the model first: .venv-app/Scripts/python.exe ml/train_model.py")
    return joblib.load(path)


def predict_duration(values, model=None):
    """Return minutes. None numerical inputs use the training-fitted imputer."""
    absent = set(FEATURES) - set(values)
    if absent:
        raise ValueError(f"Missing inputs: {sorted(absent)}")
    bounds = {"distance_km": (0, 100), "delivery_person_age": (1, 120),
              "delivery_person_rating": (0, 5), "vehicle_condition": (0, None),
              "order_hour": (0, 23), "order_day_of_week": (0, 6)}
    row = {}
    for name in NUMERIC:
        value = values[name]
        if value is None:
            row[name] = float("nan")
            continue
        number = float(value)
        low, high = bounds[name]
        if not math.isfinite(number) or number < low or (high is not None and number > high):
            raise ValueError(f"Invalid {name}: {value}")
        if name in {"delivery_person_age", "vehicle_condition", "order_hour", "order_day_of_week"} and not number.is_integer():
            raise ValueError(f"{name} must be an integer")
        row[name] = number
    for name in CATEGORICAL:
        value = values[name]
        row[name] = str(value).strip().lower() if value is not None and str(value).strip() else "unknown"
    model = model if model is not None else load_model()
    prediction = float(model.predict(pd.DataFrame([row], columns=FEATURES))[0])
    if not math.isfinite(prediction) or prediction <= 0:
        raise ValueError("Model returned an invalid duration")
    return prediction
