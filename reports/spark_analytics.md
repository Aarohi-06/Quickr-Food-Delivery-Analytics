# Quickr - PySpark RDD MapReduce Analytics

## Purpose and execution

PySpark partitions records and computes aggregates through RDD transformations and actions. CSV parsing uses Spark's reader; the core analytics use real Python RDD operations, with no pandas or SQL groupby.

Spark/PySpark: 3.5.7; Java: 1.8.0_202; Python: 3.11.17. Master: `local[2]`; cached record RDD partitions: 2; valid-duration RDD partitions: 2; reduceByKey partitions: 2.

This is local execution with two worker threads on one Windows computer, not a distributed cluster. Spark UI is disabled; workers use the active virtual environment and the driver binds to loopback. Open `notebooks/Quickr_PySpark_Analysis.ipynb`, select the Python 3.11 .venv-spark kernel and Run All. The separate Python 3.11 environment contains PySpark/Py4J and Jupyter execution dependencies; the original Phase 1/2 environment is retained.

## Input schema

CSV fields are read as nullable strings, then required numeric values are parsed explicitly in RDD transformations. Original column names:

```text
order_id
delivery_person_id
delivery_person_age
delivery_person_rating
restaurant_latitude
restaurant_longitude
delivery_latitude
delivery_longitude
order_date
order_time
pickup_time
weather
traffic
vehicle_condition
order_type
vehicle_type
multiple_deliveries
festival
city
duration_min
delivery_person_age_invalid
delivery_person_rating_invalid
multiple_deliveries_invalid
vehicle_condition_invalid
age_review_flag
order_hour
pickup_hour
order_day_of_week
order_month
distance_km
delivery_person_age_missing
delivery_person_rating_missing
multiple_deliveries_missing
vehicle_condition_missing
order_date_missing
order_time_missing
pickup_time_missing
```

## MapReduce model

Each grouped average maps a record to `(category, (duration, 1))`. `reduceByKey` combines partial `(sum, count)` pairs across partitions; a final `map` divides the duration sum by its positive count. For illustration only, two same-category durations 20 and 30 map to `(category, (20, 1))` and `(category, (30, 1))`, reduce to `(50, 2)`, then yield 25 minutes. These example numbers are not dataset findings.

Transformations: `map`, `filter`, `repartition`, `reduceByKey`; `cache` avoids repeatedly loading records. Actions: `count`, `reduce`, and `collect`. Only small aggregate results are collected to the driver.

## Actual overall findings

Total deliveries: **41,522**. Valid positive finite durations: **41,522**. Excluded from duration calculations: **0**. Average duration: **26.315447 minutes**.

**12,443 / 41,522 (29.967246%)** exceed 30 minutes. This is an analytical threshold, not actual lateness: no promised delivery deadline or service-level agreement is available.

## Average duration by traffic

Output: `data/analytics/traffic_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| high | 4046 | 110098.000000 | 27.211567 |
| jam | 12950 | 403892.000000 | 31.188571 |
| low | 14095 | 299953.000000 | 21.280809 |
| medium | 10023 | 267979.000000 | 26.736406 |
| unknown | 408 | 10748.000000 | 26.343137 |

## Average duration by weather

Output: `data/analytics/weather_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| cloudy | 6881 | 199078.000000 | 28.931551 |
| fog | 6962 | 201848.000000 | 28.992818 |
| sandstorms | 6853 | 177340.000000 | 25.877718 |
| stormy | 6932 | 179484.000000 | 25.892095 |
| sunny | 6682 | 146303.000000 | 21.895091 |
| unknown | 420 | 11082.000000 | 26.385714 |
| windy | 6792 | 177535.000000 | 26.138840 |

## Average duration by city

Output: `data/analytics/city_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| metropolitan | 31103 | 849853.000000 | 27.323827 |
| semi_urban | 147 | 7303.000000 | 49.680272 |
| unknown | 1097 | 24252.000000 | 22.107566 |
| urban | 9175 | 211262.000000 | 23.025831 |

## Average duration by vehicle type

Output: `data/analytics/vehicle_type_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| bicycle | 43 | 1116.000000 | 25.953488 |
| electric_scooter | 3404 | 83293.000000 | 24.469154 |
| motorcycle | 24197 | 668105.000000 | 27.611067 |
| scooter | 13878 | 340156.000000 | 24.510448 |

## Average duration by festival

Output: `data/analytics/festival_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| no | 40495 | 1053353.000000 | 26.011927 |
| unknown | 215 | 2401.000000 | 11.167442 |
| yes | 812 | 36916.000000 | 45.463054 |

## Average duration by distance band

Output: `data/analytics/distance_band_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| [0,5) km | 11187 | 248182.000000 | 22.184857 |
| [10,15) km | 11183 | 333716.000000 | 29.841366 |
| [15,20) km | 6186 | 184945.000000 | 29.897349 |
| [20,+) km | 1779 | 52987.000000 | 29.784711 |
| [5,10) km | 11187 | 272840.000000 | 24.389023 |

## Average duration by age band

Output: `data/analytics/age_band_summary.csv`.

| Category | Deliveries | Total duration (min) | Average (min) |
|---|---:|---:|---:|
| 18-24 | 9905 | 228044.000000 | 23.023120 |
| 25-34 | 19901 | 523594.000000 | 26.309934 |
| 35-44 | 10191 | 300890.000000 | 29.525071 |
| 45_plus | 24 | 539.000000 | 22.458333 |
| under_18_review | 25 | 640.000000 | 25.600000 |
| unknown | 1476 | 38963.000000 | 26.397696 |

## Delivery counts by order type

| Order type | Deliveries |
|---|---:|
| buffet | 10265 |
| drinks | 10348 |
| meal | 10398 |
| snack | 10511 |

## Null handling, bands and limitations

Missing categories are grouped as unknown. Missing/invalid age or distance uses an unknown band, retaining a valid-duration delivery in each denominator. Distance bands are [0,5), [5,10), [10,15), [15,20), [20,+) km; age bands are under 18 (review), 18-24, 25-34, 35-44, 45+, and unknown. Grouped means use only valid positive finite durations; order-type counts use all records. Groups with no records are absent, never divided by zero.

These are descriptive associations, not causal effects. Small categories can have unstable averages. Cleaning exclusions and unknown inputs affect representativeness. Haversine distance is straight-line, not road distance. CSV exports use the Python standard library after collecting small summaries; this avoids requiring Hadoop native writers on Windows.

## Environment and verification

Initial installation stalled without output and was stopped; a retry downloaded and installed PySpark successfully. The first Spark run failed with `[PATH_NOT_FOUND]` because the file URI encoded workspace spaces as `%20`; using a forward-slash Windows path fixed it. The existing HADOOP_HOME pointed to C:/hadoop/bin, producing a missing C:/hadoop/bin/bin warning. The notebook verifies winutils.exe and corrects HADOOP_HOME to its parent for this process only. SPARK_HOME is set explicitly to avoid Windows launcher Python discovery with spaces.

Python 3.12 runs then failed with `Python worker exited unexpectedly (crashed)` caused by `java.io.EOFException`, even outside the sandbox. This matches [SPARK-53759](https://issues.apache.org/jira/browse/SPARK-53759). A fresh Python 3.11 virtual environment was created using an available interpreter, without importing any previous project code. An offline package-cache attempt hit `[Errno 13] Permission denied`; installation was retried with approved access. Python 3.11 pip then reported `SSL: CERTIFICATE_VERIFY_FAILED`. A binary-only public PySpark download also reported no matching distribution (PySpark is distributed as source). The successfully built local PySpark wheel and a Py4J wheel downloaded through the working Python 3.12 pip were staged in `.spark-packages` and installed offline into `.venv-spark`, without disabling TLS checks. Historical failures are preserved in spark_execution.log, spark_execution_retry.log and spark_execution_unrestricted.log. The final run is spark_execution_final.log.

Installed PySpark 3.5.7 and its Py4J dependency. Java 8u202 was already installed. Java 8 versions before 8u371 are deprecated for Spark 3.5; a current Java 17 installation is preferable for future work. See [Apache Spark requirements](https://spark.apache.org/docs/3.5.7/).

Remaining environment messages in the successful run: the Windows launcher printed `The system cannot find the path specified` before Spark started; the source of that shell message is unresolved. In the earlier script run optional psutil was absent, so Spark warns about reduced memory-spill monitoring. After verified outputs and Spark shutdown, `ERROR: Access denied` was printed; its exact cleanup operation is unresolved. The process nevertheless exited with code 0. These messages are retained in the final execution log; no result failures or incomplete aggregate outputs were observed.

All actions completed. Exported CSV counts and grouped averages were read back and checked; each grouping reconciles with the overall duration count and sum. Raw and cleaned CSV hashes are unchanged. No dedicated test suite or later project phases were implemented.

## Notebook implementation

The primary implementation is notebooks/Quickr_PySpark_Analysis.ipynb. All analysis code is contained in its labeled cells; no external analytics script is imported. Saved cell outputs come from notebook execution. Use the Python 3.11 .venv-spark interpreter in VS Code and Run All. The earlier standalone spark_analytics.py has been replaced. Earlier log messages in the environment section are historical; the executed notebook outputs record this run.
