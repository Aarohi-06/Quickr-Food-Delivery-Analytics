"""Train a reproducible, leakage-conscious Random Forest regression pipeline."""
from pathlib import Path
import hashlib
import json
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from ml.features import NUMERIC, CATEGORICAL, FEATURES
from quickr.config import ROOT


def main():
    source = ROOT / "data/processed/quickr_clean.csv"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    df = pd.read_csv(source)
    if not set(FEATURES + ["duration_min"]).issubset(df):
        raise ValueError("Missing required model columns")
    X = df[FEATURES].copy()
    for column in NUMERIC:
        X[column] = pd.to_numeric(X[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    for column in CATEGORICAL:
        X[column] = X[column].fillna(np.nan)
    y = pd.to_numeric(df["duration_min"], errors="coerce")
    if not (np.isfinite(y) & y.gt(0)).all():
        raise ValueError("Target must be finite and positive in every cleaned record")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    preprocess = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CATEGORICAL),
    ])
    model = Pipeline([
        ("preprocess", preprocess),
        ("regressor", RandomForestRegressor(n_estimators=150, max_depth=18,
             min_samples_leaf=3, random_state=42, n_jobs=2)),
    ])
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    baseline = DummyRegressor(strategy="median").fit(np.zeros((len(y_train), 1)), y_train)
    baseline_prediction = baseline.predict(np.zeros((len(y_test), 1)))
    metrics = {
        "mae_min": float(mean_absolute_error(y_test, predicted)),
        "rmse_min": float(np.sqrt(mean_squared_error(y_test, predicted))),
        "r2": float(r2_score(y_test, predicted)),
        "baseline_mae_min": float(mean_absolute_error(y_test, baseline_prediction)),
        "train_rows": len(X_train), "test_rows": len(X_test), "total_rows": len(df),
        "random_state": 42, "test_fraction": 0.2,
        "python_version": platform.python_version(), "sklearn_version": sklearn.__version__,
        "source_sha256": digest,
    }
    metadata = {
        "target": "duration_min", "prediction_moment": "courier assignment, before pickup",
        "numeric_features": NUMERIC, "categorical_features": CATEGORICAL,
        "feature_order": FEATURES,
        "category_values": {c: sorted(X_train[c].dropna().unique().tolist()) for c in CATEGORICAL},
        "numeric_training_medians": {c: float(X_train[c].median()) for c in NUMERIC},
        "excluded": ["order_id", "delivery_person_id", "pickup_time", "pickup_hour",
                     "multiple_deliveries", "duration_min"],
    }
    models = ROOT / "models"
    models.mkdir(exist_ok=True)
    joblib.dump(model, models / "delivery_duration_pipeline.joblib", compress=3)
    for filename, value in [("metrics.json", metrics), ("feature_info.json", metadata)]:
        (models / filename).write_text(json.dumps(value, indent=2), encoding="utf-8")
    pd.DataFrame({"order_id": df.loc[y_test.index, "order_id"],
                  "actual_duration_min": y_test, "predicted_duration_min": predicted,
                  "residual_min": y_test - predicted}).to_csv(models / "test_predictions.csv", index=False)
    transformed = model.named_steps["preprocess"].get_feature_names_out()
    importance = pd.DataFrame({"feature": transformed,
        "importance": model.named_steps["regressor"].feature_importances_}).sort_values("importance", ascending=False)
    importance.to_csv(models / "feature_importance.csv", index=False)
    restored = joblib.load(models / "delivery_duration_pipeline.joblib")
    assert np.allclose(restored.predict(X_test.head(5)), predicted[:5])
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    report = f"""# Quickr - Delivery Duration Model

Random Forest regression predicts duration_min in minutes. Prediction moment: courier assignment before pickup.
The 80/20 random split uses random_state=42: {len(X_train):,} train rows and {len(X_test):,} held-out rows.

## Actual held-out results

- MAE: {metrics['mae_min']:.6f} minutes
- RMSE: {metrics['rmse_min']:.6f} minutes
- R-squared: {metrics['r2']:.6f}
- Training-median baseline MAE: {metrics['baseline_mae_min']:.6f} minutes

## Features and preprocessing

Numeric: {', '.join(NUMERIC)}.
Categorical: {', '.join(CATEGORICAL)}.
Numeric median imputation (with missing indicators), categorical constant unknown imputation,
and one-hot encoding with unknown-category handling are inside the fitted sklearn Pipeline.
Every learned preprocessing value is fitted only on the training split.
The Random Forest has 150 trees, maximum depth 18, minimum leaf size 3, random_state 42, and two workers.
Identifiers, pickup timestamps, original target strings, and realized multiple-delivery counts
are excluded from model inputs. Test order IDs are saved only for evaluation traceability.
Traffic/weather, courier age/rating/vehicle, settlement category and festival status are assumed
available at dispatch. Confirm that assumption before production use.

## Artifacts and verification

models/delivery_duration_pipeline.joblib contains preprocessing and regressor together.
models/metrics.json, feature_info.json, test_predictions.csv and feature_importance.csv contain
actual evaluation results and feature details. Reloaded model predictions match in-memory predictions.
Source SHA-256: {digest}. Python {platform.python_version()}, sklearn {sklearn.__version__}.

## Limitations

This is a random held-out evaluation, not temporal validation or independent-courier validation.
Repeated couriers/restaurants may occur in both splits. Test metrics can therefore be optimistic
for future dates or new locations. Small, historical, geographically filtered data limits generalization.
Distance is Haversine rather than road distance. Duration's exact business start/end definition is
not documented. Estimates are not lateness predictions: no promised deadline exists.
One-hot unknown values are safely encoded but predictions outside training coverage are unreliable.
Feature importance is impurity-based and is not causal evidence. Load only trusted joblib files.
"""
    (ROOT / "reports/ml_model.md").write_text(report, encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print("Saved model and evaluation artifacts; reload check passed.")


if __name__ == "__main__":
    main()
