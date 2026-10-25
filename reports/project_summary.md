# Quickr - Project Summary

## Aim and problem statement

Analyze historical food-delivery operations and estimate delivery duration from information
available at courier assignment. Operational records contain padded missing placeholders,
inconsistent categories, questionable GPS routes and nullable features. Quickr provides a
reproducible academic workflow from those source records to analytics, storage and prediction.

## Objectives

- Explore and validate the actual dataset without modifying the source.
- Demonstrate RDD MapReduce sums, counts and grouped averages in PySpark.
- Store query-oriented analytical snapshots in a dedicated Cassandra keyspace.
- Train and evaluate a leakage-conscious delivery-duration regression pipeline.
- Present actual analytics, predictions, quality information and database status in Streamlit.

## Methodology and implementation

1. Pandas exploration records literal placeholders and actual schema/statistics.
2. Cleaning trims text, normalizes categories, validates numerics/dates/times, extracts
   duration_min and calculates Haversine distance. It removes 3,640 zero-endpoint routes
   and 431 routes exceeding the documented local-delivery distance assumption of 100 km.
   Other missing values remain nullable or use unknown labels; unusual ages are flagged.
3. The executed notebook notebooks/Quickr_PySpark_Analysis.ipynb uses map, filter,
   reduceByKey, reduce, count and collect in local[2] mode with two RDD partitions.
   Grouped means combine (duration sum, count) rather than averaging subgroup averages.
4. Nine aggregate CSVs are mapped to nine Cassandra tables in quickr_bda. Snapshot ID
   clean_v1 is the partition key; category fields are clustering keys. Prepared statements
   and single-partition replacement batches support repeatable loading. A separate
   demo_operations table isolates viva insert/update/delete examples.
5. The Random Forest pipeline uses training-only numeric median imputation, categorical
   unknown imputation and one-hot encoding. Twelve dispatch-time input features exclude
   identifiers, pickup time and realized multiple-delivery counts. The model has 150
   trees, max_depth=18, min_samples_leaf=3 and random_state=42.
6. The six-page Streamlit dashboard uses Plotly and real CSV/model outputs. Only the
   database insights page requires Cassandra; it does not silently fall back to CSVs.

## Actual results

- Original dataset: 45,593 records. Cleaned: 41,522 records and 37 columns.
- Removed: 4,071 records for unusable delivery routes.
- Average duration: 26.315447 minutes.
- Exceeding the 30-minute analytical threshold: 12,443
  records (29.967246%). This is not actual lateness.
- Analytics exports: nine CSVs, 39 summary rows ready for Cassandra.
- Train/test counts: 33,217/8,305 using an 80/20 split with random_state=42.
- MAE: 3.195730 minutes. RMSE: 4.007556 minutes. R-squared: 0.819306.
- Training-median baseline MAE: 7.651415 minutes.
- Trained pipeline saved and reloaded; predictions matched in-memory results.
- All six app pages, eight analytics selections, inference button, nullable inference,
  invalid-input rejection and service-unavailable handling passed functional checks.
- Streamlit launched at http://127.0.0.1:8501; HTTP health endpoint returned 200 and ok.
- Cassandra connection timed out. Initialization, load and verification each exited 1,
  even outside the sandbox. Actual inserted rows from this run: 0. Database counts and
  CQL execution remain unverified until the installed server is started manually.

## Technologies

Python 3.11 app environment, pandas 2.3.3, scikit-learn 1.7.2, Cassandra driver 3.29.3,
Streamlit 1.50.0, Plotly 6.3.1 and joblib 1.5.2. The preserved Python 3.11 Spark/Jupyter
and Python 3.12 exploration environments remain separate. Full app versions are pinned
in requirements-app-lock.txt. No Docker or new Cassandra server was installed.

## Limitations and unfinished service verification

This is local Spark rather than a multi-machine cluster. Cassandra RF=1 is not redundant.
The data is historical; random train/test splits can share couriers and restaurants and
may overstate future or new-location performance. GPS screening and a five-point rating
scale are documented assumptions. Haversine is not road routing; duration business start
and end definitions need confirmation. Model inputs are assumed known at dispatch.
Unknowns and sparse groups limit comparisons. No promised deadlines exist, so neither
the analytical threshold nor the regression model measures actual lateness.

The one outstanding integration step is to start the existing Cassandra server and run
the three documented database commands, then execute the presentation CQL. Schema,
loader idempotence and queries are implemented but cannot be certified against a server
that is unreachable. Loader replacement is atomic per table partition, not across all nine
tables; avoid concurrent loads and always verify afterwards.

## Verification evidence

reports/ml_training.log, reports/functional_checks.log, reports/app_final_check.log,
reports/streamlit_server.log and reports/cassandra_*.log preserve actual execution.
reports/cassandra_status.json distinguishes rows ready to load from database rows.
Original and cleaned CSVs were not changed, and the PySpark notebook was preserved.
