"""Existing inference validation, shared unchanged by both backends."""
import math
from ml.features import FEATURES, NUMERIC, CATEGORICAL

def normalize_inputs(values):
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
    return row
