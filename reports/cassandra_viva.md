# Quickr - Cassandra viva and demonstration

## What Cassandra is and why Quickr uses it

Apache Cassandra is a distributed, wide-column NoSQL database. It partitions data by a
partition key and can replicate it across nodes. Quickr stores the small, precomputed
PySpark analytical summaries so the dashboard can retrieve them using predictable CQL queries.
This local single-node academic setup demonstrates integration; it does not demonstrate
cluster scale, high availability or the throughput of a distributed deployment.

## Query-oriented schema

The separate keyspace is `quickr_bda`. `SimpleStrategy` with replication factor 1 is
appropriate only for this local exercise; no other keyspace is modified.

Nine analytics tables match the CSVs: `overall_summary`, `traffic_summary`,
`weather_summary`, `city_summary`, `vehicle_type_summary`, `festival_summary`,
`distance_band_summary`, `age_band_summary` and `order_type_summary`.

Every analytics table has `dataset_id` as its partition key. We currently use
`clean_v1` for one historical snapshot. Grouped tables use the actual category
(traffic, weather, city, vehicle_type, festival, distance_band, age_band or order_type)
as their clustering key. Together these columns form the primary key. They identify
one row uniquely and let us fetch all categories in a snapshot or one category.
The overall table has one row per dataset_id. Counts are bigint, means and sums are
double, and labels are text. This small partition design is deliberately for summary
tables; raw delivery events would require a different, bounded partitioning strategy.

`demo_operations` uses a separate text demo_id primary key. INSERT/UPDATE/DELETE
examples use only its disposable `viva_example` row, never real analytics.

## Cassandra versus MySQL

| Cassandra | MySQL |
|---|---|
| Distributed wide-column model | Relational tables |
| Schema organized around partitioned query patterns | Normalization and relational queries |
| No ordinary relational joins or foreign keys | Joins, foreign keys and relational constraints |
| Tunable consistency and partition-focused access | Transactional relational operations |
| CQL resembles SQL but has different restrictions | SQL supports broad relational operations |

Neither system is inherently best for every task. For these tiny summaries either
could work; Cassandra is included to demonstrate the Big Data storage workflow.
Replication factor 1 provides no redundant copy; this is not a fault-tolerant cluster.

## Python connection and safe loading

The `cassandra-driver` package connects to 127.0.0.1:9042. The reusable context manager
in `quickr/database.py` bounds connection time and always shuts down its cluster.
Queries bind values through prepared statements. Table identifiers come only from
the fixed project allowlist. There is no SQL-string interpolation of user values.

`scripts/init_cassandra.py` applies `cassandra/schema.cql` with CREATE IF NOT EXISTS.
The loader validates all nine CSV headers and types before connecting. For each tiny
snapshot partition it uses a logged batch to delete the previous partition and insert
its replacement. Explicit insert timestamps are later than the delete timestamp.
This prevents both duplicates and stale category rows on repeated loads. Each table's
replacement is atomic; replacement across all nine tables is not a single transaction.
Avoid concurrent loaders and run verification after loading. The loader only replaces
the project's clean_v1 partitions. It does not modify unrelated data or keyspaces.

The verifier fetches partitions and compares every count and value with the CSVs.
A successful write is not assumed from a connection alone.

## Demonstration sequence

1. In an Administrator terminal start the already-installed server with `cassandra`.
2. From a second terminal connect with `cqlsh 127.0.0.1 9042`.
3. In the workspace run initialization, loading and verification using README commands.
4. Open `cassandra/demo_queries.cql` and execute the queries in cqlsh.
5. Explain `WHERE dataset_id = 'clean_v1' AND traffic = 'jam'`: the first condition
   selects a partition, the second selects a clustering key. No ALLOW FILTERING is needed.
6. Demonstrate the disposable demo row's insert, update, read and delete.
7. Open the dashboard's Cassandra page and explain that it reads stored historical
   summaries, not live operational deliveries.

`DESCRIBE` is a cqlsh command. The Python initializer sends only CQL schema statements,
not cqlsh-specific DESCRIBE commands. The full-table SELECT example is safe here only
because this academic table holds a handful of summary records.

## PySpark to Cassandra workflow

Raw CSV -> pandas validation/cleaning -> cleaned CSV -> PySpark RDD map/reduceByKey
aggregations -> nine aggregate CSVs -> prepared Cassandra writes -> partition-key CQL
reads -> Streamlit/Plotly. Cassandra stores the aggregate outputs; it does not train
the Random Forest or replace the PySpark calculation.

## Actual execution status

The installed commands were found at C:/cassandra/bin/cassandra.ps1 and cqlsh.bat.
No Docker or new server was installed. Port 9042 did not accept a connection.
Initialization, loading and verification were attempted, including outside the sandbox,
and each reported TimeoutError: timed out with exit code 1. No rows were inserted by
this run. There are 39 validated CSV rows ready to load, not 39 verified database rows.
The schema and demo queries still require validation against the user's running server.
