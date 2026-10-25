# Quickr - Presentation Guide

## Before the demonstration

1. Open the BDA LA workspace and README.md. Use .venv-app for the application; preserve
   the .venv-spark kernel for the notebook.
2. Start the installed Cassandra manually in an Administrator terminal with `cassandra`.
   Wait until `cqlsh 127.0.0.1 9042` connects. No Docker is needed.
3. Run init_cassandra.py, load_analytics.py and verify_cassandra.py using the exact README
   commands. Expect 39 aggregate rows only after successful loading and verification.
   Current development status: connection timed out, 0 inserted by this run. Do not
   describe database integration as executed until these commands succeed.
4. Launch the dashboard with `.\.venv-app\Scripts\python.exe -m streamlit run app/app.py --server.address 127.0.0.1`.

## Short demonstration (about 8 minutes)

1. **Problem and architecture (1 minute):** Explain raw data -> pandas cleaning -> PySpark
   RDD analytics -> aggregate CSVs -> Cassandra; cleaned data separately trains the model.
2. **Dataset quality (1 minute):** Show Data Quality. Explain 45,593 raw records, 41,522
   retained, 4,071 route exclusions, unknown categories and preserved missing timestamps.
3. **MapReduce (1 minute):** Open the executed notebook. Show `(category, (duration, 1))`,
   `reduceByKey` addition, and `sum/count`. Mention local[2], two partitions, no real cluster.
4. **Analytics (1 minute):** Show traffic and distance charts. Explain group denominators,
   historical snapshots, 26.32-minute overall mean and
   29.97% exceeding 30 minutes. Do not call that lateness.
5. **Cassandra (2 minutes):** In cqlsh use cassandra/demo_queries.cql. Describe the keyspace
   and traffic_summary table, query clean_v1/jam, then demonstrate disposable demo row
   insert/update/delete. Open the database dashboard page and distinguish stored snapshots
   from live delivery events. If Cassandra is unreachable, show the graceful error and
   implemented queries honestly rather than presenting CSVs as database results.
6. **Prediction and evaluation (2 minutes):** Submit dispatch-time inputs, explain an
   estimate rather than a guarantee. Show held-out MAE 3.196 min, RMSE
   4.008 min and R-squared 0.8193. Compare baseline MAE
   7.651 min. Explain train-only imputation and random-split limitations.

## Viva talking points

- **Why PySpark on a small dataset?** To demonstrate partitioned RDD transformations and
  MapReduce. The local demonstration is not proof of a need for cluster infrastructure.
- **Why sum/count instead of mean-of-means?** Group sizes differ; sum/count preserves
  the correct record-weighted mean.
- **What is the Cassandra partition key?** dataset_id. Category is a clustering key;
  together they identify one summary row. Queries use partition-key filtering.
- **Why no ALLOW FILTERING?** Tables match known access patterns and keys.
- **Why prepared statements?** Bind values safely and reuse parsed query plans.
- **Can I rerun the loader?** Yes. It replaces each project's tiny snapshot partition,
  using later insert timestamps than the partition delete. No duplicates or stale groups.
- **What happens when Cassandra stops?** The database page displays an unavailable state;
  CSV analytics and the saved-model prediction page continue working.
- **Where is leakage avoided?** Preprocessing is fitted inside the pipeline on training
  rows only. Identifiers, pickup time, target derivatives and realized multiple deliveries
  are excluded from the model inputs.
- **What is R-squared?** Held-out variance explained relative to a constant prediction;
  it is not classification accuracy and does not mean predictions are exact.
- **Why not call a 31-minute delivery late?** There is no promised deadline in the data.
- **What remains unproven?** Cassandra execution while the server is unreachable,
  future-date generalization, road-distance effects, confirmed duration semantics and
  distributed production-scale performance.

Read reports/cassandra_viva.md for deeper database explanations and README.md for commands.
