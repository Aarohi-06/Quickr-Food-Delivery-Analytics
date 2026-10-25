# Quickr - Spark ML Migration and Verification

## Outcome

Spark MLlib is the primary delivery-duration predictor. The preserved sklearn model is
available only through the clearly labeled fallback checkbox. The three pages remain
Dashboard, Delivery Time Prediction, and Data & System Insights. No inference service
was introduced because embedded Spark passed the actual Streamlit integration checks.

## Actual paired evaluation

| Backend | MAE (min) | RMSE (min) | R-squared |
|---|---:|---:|---:|
| Spark primary | 3.213796 | 4.058517 | 0.814682 |
| sklearn preserved | 3.195730 | 4.007556 | 0.819306 |

The exact original test membership was reconstructed only after verifying unique source
and test IDs, source coverage, matching targets and matching source SHA-256. Train/test:
33,217/8,305. All learned preprocessing fits training rows only. All originally approved
forest parameters were kept: 150 trees, depth 18, minimum node/leaf size 3, seed 42 and
all features considered per split. Spark discretization/encoding differs from sklearn.
The slightly weaker Spark metrics are reported honestly; this is a technology migration.

## Environment and resource findings

Created .venv-ml using the existing Python 3.11 interpreter. Installed PySpark 3.5.7,
Py4J 0.10.9.7, NumPy 1.26.4, SciPy 1.12.0, PyArrow 12.0.1, plus the existing app
requirements (Streamlit 1.50.0, pandas 2.3.3, Plotly 6.3.1, sklearn 1.7.2, joblib
1.5.2 and Cassandra driver 3.29.3). Full installed dependencies: requirements-ml-lock.txt.
The working .venv-app and .venv-spark package sets were not changed.

A tiny Spark ML pipeline passed fit, save, reload and equal predictions. Cold Spark
startup in that small check took about 11 seconds. That does NOT measure full-model load.
The 150-tree model's cold loading inside Streamlit took several minutes in the later
2 GiB configuration; pre-open the prediction page before presenting.

Full training first failed creating a shuffle file in Windows Temp. A workspace-local
.spark-local directory was configured and execution retried outside the sandbox. The
retry then failed with java.lang.OutOfMemoryError: GC overhead limit exceeded under the
default 1 GiB heap. A third attempt with a 4 GiB driver heap completed training,
evaluation, persistence and reload in 689.1 seconds. No forest
parameters were reduced to disguise the failures. About 4 GiB Java working-set memory
was observed during training; other OS/app memory is additional.

Installing existing app dependencies initially selected PyArrow 26, whose NumPy-2
requirement conflicted with NumPy 1.26.4. Pinning PyArrow 12.0.1 resolved the import
failure. Final ML imports and pip dependency checks passed. No TLS checks were disabled.
System-wide Java and Cassandra were not modified. Java 8u202 remains an old/deprecated
Spark combination; Python 3.11 avoids the project's previous Python-3.12 worker issue.

## Inference verification

The integration check initialized Spark from inside the Streamlit script thread, not
before launching the app. It used the default --driver-memory 2g configuration (the
JVM reported approximately 1.78 GiB usable maximum heap under its collector).

- Primary form submission returned 29.5 minutes for the checked default form inputs.
- Normal input: 29.513525 minutes;
  measured request time 37.64 seconds.
- Missing age/rating/order-hour input: 25.719471
  minutes; measured request time 28.69 seconds.
- Unseen traffic/vehicle labels: 27.326104
  minutes; measured request time 38.86 seconds.
- Two further identical requests produced equal predictions. START_COUNT stayed 1
  throughout page reruns, normal/missing/unseen requests and backend switching.
- Negative distance was rejected by unchanged shared input validation.
- The Spark page displayed Spark MAE 3.214/RMSE 4.059/R-squared 0.8147.
- Selecting the fallback displayed its own prediction and MAE 3.196/RMSE 4.008/R-squared 0.8193.
- Dashboard rendered before Spark initialization, with START_COUNT=0. All eight analytics
  summaries passed checks with Spark unavailable. Data quality remained usable with
  both Spark and Cassandra deliberately simulated as unavailable.
- The existing app environment, with no PySpark installed, displayed the friendly primary
  unavailable state and the explicitly selected sklearn fallback worked.
- Actual Cassandra read-only dashboard access connected successfully. No schema, loader
  or mutation commands were executed during this migration.
- Streamlit launched from .venv-ml on 127.0.0.1:8502 and its health endpoint returned 200 ok.

The inference check took 410.6 seconds overall, including cold model
loading, several predictions, page changes and backend checks. These timings are measured
on this machine, not latency guarantees. Individual requests taking tens of seconds are
a material limitation: the sklearn fallback remains preferable when a quick demonstration
response matters. A separate persistent inference service could isolate lifecycle/failures
for future deployment, but would not by itself remove Spark job scheduling overhead.

## Preservation and remaining limitations

All original root model files match their stored SHA-256 fingerprints and copied backups.
The cleaned dataset, analytics notebook and Cassandra schema also match their fingerprints.
Analytics CSVs and database records were not changed. The prior ML report was backed up.
Code compiles and the isolated environment reports no broken dependencies.

A nonfatal Windows launcher path message and an access-denied message at Spark shutdown
remain in execution logs. The successful training/inference processes exited 0, and
persistence and result checks passed before shutdown. The failed runs remain recorded.
No model retraining was performed after the successful 4 GiB run.

This is local[2] Spark, not a distributed cluster. Prediction calls are serialized by a
shared lock and are not suitable for high-throughput serving. Spark failure recovery may
require restarting the app; the explicit fallback is kept usable. Random held-out
performance can be optimistic for future dates or new couriers/restaurants. Estimates
predict duration, not actual lateness, and straight-line distance is not road routing.

## Files created

- `quickr/spark_runtime.py`
- `ml/spark_features.py`
- `ml/input_validation.py`
- `ml/sklearn_train_model.py`
- `ml/sklearn_predict.py`
- `requirements-ml.txt`
- `requirements-ml-lock.txt`
- `models/sklearn_backup/`
- `models/spark/`
- `models/spark_smoke/`
- `reports/spark_ml_migration.md`
- `reports/spark_ml_inference_verification.json`
- `reports/spark_ml_compatibility.log`
- `reports/spark_ml_training.log`
- `reports/spark_ml_training_retry.log`
- `reports/spark_ml_training_4g.log`
- `reports/spark_ml_inference.log`
- `reports/spark_ml_streamlit_server.log`

## Files modified

- `ml/train_model.py`
- `ml/predict.py`
- `app/app.py`
- `launch_quickr.ps1`
- `README.md`
- `reports/ml_model.md`
- `.gitignore`

## Launch commands

Primary Spark app (port 8502 avoids the earlier app instance on 8501):

```powershell
.\.venv-ml\Scripts\python.exe -m streamlit run app/app.py --server.address 127.0.0.1 --server.port 8502
```

Original app environment remains a fallback-only launch:

```powershell
.\.venv-app\Scripts\python.exe -m streamlit run app/app.py
```

Then select Use scikit-learn fallback (preserved baseline). The PowerShell launcher
launch_quickr.ps1 now uses .venv-ml. Training commands and dependency recreation are
in README.md; training refuses to overwrite an existing saved Spark pipeline.
