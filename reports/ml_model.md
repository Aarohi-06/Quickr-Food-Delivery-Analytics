# Quickr - Spark MLlib Random Forest Model

## Primary implementation and preserved baseline

Primary backend: pyspark.ml.regression.RandomForestRegressor (Spark 3.5.7).
Target: duration_min. Prediction moment: courier assignment, before pickup.
The old sklearn pipeline, metrics, metadata, predictions and importance remain intact
at their original paths and are also copied under models/sklearn_backup, with fingerprints.
Original training and inference source: ml/sklearn_train_model.py and ml/sklearn_predict.py.

## Verified, paired evaluation

Source IDs and saved baseline test IDs were checked for missingness, uniqueness and
coverage. The source SHA-256 matches the preserved baseline; every held-out ID's target
matches the saved baseline actual duration. Exact membership is reused: 33,217
training and 8,305 held-out deliveries. This is the prior 80/20 split from
random_state=42, not a newly sampled Spark randomSplit. IDs identify split membership
only and are excluded from model inputs.

| Backend | MAE (minutes) | RMSE (minutes) | R-squared |
|---|---:|---:|---:|
| PySpark MLlib primary | 3.213796 | 4.058517 | 0.814682 |
| Preserved sklearn fallback | 3.195730 | 4.007556 | 0.819306 |

Training-median constant predictor MAE: 7.651415 minutes, recomputed
from the same training/held-out membership. Spark MAE is 0.018066
minutes higher than sklearn. This migration demonstrates Spark ML integration, not an
accuracy improvement. The scores are regression metrics, not classification accuracy.

## Feature processing and leakage prevention

Numeric: distance_km, delivery_person_age, delivery_person_rating, vehicle_condition, order_hour, order_day_of_week.
Categorical: traffic, weather, city, vehicle_type, festival, order_type.
Missingness indicators: delivery_person_age, delivery_person_rating, order_hour.

The persisted pipeline contains SQLTransformer normalization (trim/lowercase/categories,
finite numeric casts and missing indicators), exact-quantile median Imputer,
training-fitted StringIndexer stages with keep behavior, OneHotEncoder with keep behavior
and dropLast=False, VectorAssembler, and the Random Forest. All learned stages fit only
training rows. Missing/unseen categories retain a prediction row. Unknown categories
get reserved buckets, so the encoded layout differs from sklearn's ignore behavior.
Imputed values and vocabularies for the app are read from the fitted training stages.
No Python UDF or external preprocessing code is required to reload the pipeline.

Parameters: numTrees=150, maxDepth=18, minInstancesPerNode=3, seed=42,
featureSubsetStrategy=all, maxBins=32, bootstrap=True, subsamplingRate=1.0.
All initially requested forest parameters were retained. Spark's discretized splits,
encoding and random sampling differ from sklearn, so predictions need not match.
Identifiers, pickup time/hour, multiple_deliveries and target-derived values are not inputs.

## Artifacts and execution

models/spark/pipeline is the complete persisted Spark PipelineModel. Adjacent files:
metrics.json, feature_info.json, test_predictions.csv, feature_importance.csv and
split_membership.csv. Metrics came from Spark RegressionEvaluator. Importance is
impurity-based, mapped to assembled feature metadata; it does not establish causation.
A saved model was reloaded and eight predictions matched the in-memory fitted pipeline.
Training/evaluation/persistence took 689.1 seconds in the successful run.
The trainer refuses to overwrite an existing Spark pipeline; preserve/version it first.

Run training in a fresh terminal only when no Spark pipeline already exists:

```powershell
$env:PYSPARK_SUBMIT_ARGS='--driver-memory 4g pyspark-shell'
.\.venv-ml\Scripts\python.exe ml/train_model.py
```

The app uses .venv-ml and lazily initializes one local[2] Spark session on its prediction
page. It caches the loaded PipelineModel by artifact version and serializes inference
through a reentrant lock. Other pages do not initialize Spark. Missing numeric values
use the training-fitted imputer, with unchanged input validation shared by both backends.
The explicit fallback checkbox loads the preserved sklearn pipeline and switches all
metrics, form metadata and diagnostic artifacts together. No automatic silent fallback.

## Environment and limitations

Python 3.11; PySpark 3.5.7; NumPy 1.26.4; SciPy 1.12.0; PyArrow 12.0.1;
Streamlit 1.50.0; pandas 2.3.3; sklearn 1.7.2 for fallback only.
Original app and notebook environments are untouched. Spark ML is isolated in .venv-ml.
Java remains the existing 8u202; no system Java or Cassandra configuration was changed.

Early tiny-pipeline startup/save/reload/prediction passed. Full training first failed on
a missing Windows Temp shuffle file, then on GC overhead in the default 1 GiB heap.
The successful run used workspace-local shuffle storage and a 4 GiB driver heap.
Inference defaults to 2 GiB unless explicitly overridden before JVM startup.
A nonfatal Windows launcher path message remains documented in logs.

The data and metrics are historical. A random paired split can share couriers and
restaurants across partitions and does not validate future dates/new locations.
Haversine distance is not road distance. Rating-scale/GPS screening assumptions remain.
Feature availability at dispatch must be confirmed before operational deployment.
No promised deadline is present: predictions estimate duration, not actual lateness.
Local Spark is not a distributed cluster. Multiple simultaneous web requests are
serialized, not a throughput-oriented inference service. Restart the app if its JVM
fails; the explicit sklearn fallback remains available. Never load untrusted model files.

## Streamlit integration verification

Spark initialized within the Streamlit script thread and served normal, missing and
unseen-category inputs. Repeated predictions reused one session; fallback metrics
matched the selected backend. Full model cold loading took several minutes, and the
measured input checks took about 29-39 seconds per request in the 2 GiB configuration.
These are material demonstration limitations; pre-open the page or use the explicitly
labeled sklearn fallback when fast responses matter. See reports/spark_ml_migration.md
and reports/spark_ml_inference_verification.json for actual evidence.
