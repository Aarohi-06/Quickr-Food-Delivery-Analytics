# Quickr - Delivery Duration Model

Random Forest regression predicts duration_min in minutes. Prediction moment: courier assignment before pickup.
The 80/20 random split uses random_state=42: 33,217 train rows and 8,305 held-out rows.

## Actual held-out results

- MAE: 3.195730 minutes
- RMSE: 4.007556 minutes
- R-squared: 0.819306
- Training-median baseline MAE: 7.651415 minutes

## Features and preprocessing

Numeric: distance_km, delivery_person_age, delivery_person_rating, vehicle_condition, order_hour, order_day_of_week.
Categorical: traffic, weather, city, vehicle_type, festival, order_type.
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
Source SHA-256: 18ea2ac699e82e5edc47c34196bb2490ff9ab06728a9f81f467170bf38e3f5e7. Python 3.11.17, sklearn 1.7.2.

## Limitations

This is a random held-out evaluation, not temporal validation or independent-courier validation.
Repeated couriers/restaurants may occur in both splits. Test metrics can therefore be optimistic
for future dates or new locations. Small, historical, geographically filtered data limits generalization.
Distance is Haversine rather than road distance. Duration's exact business start/end definition is
not documented. Estimates are not lateness predictions: no promised deadline exists.
One-hot unknown values are safely encoded but predictions outside training coverage are unreliable.
Feature importance is impurity-based and is not causal evidence. Load only trusted joblib files.
