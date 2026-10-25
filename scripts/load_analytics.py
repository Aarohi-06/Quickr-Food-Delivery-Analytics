"""Load nine CSV snapshots using prepared, partition-scoped atomic batches."""
from pathlib import Path
import csv
import json
import math
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quickr.config import ANALYTICS, DATASET_ID, KEYSPACE, ROOT, TABLES
from quickr.database import connection


def read_csvs():
    """Validate every file before touching Cassandra."""
    result = {}
    for table, fields in TABLES.items():
        with (ANALYTICS / f"{table}.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(fields):
                raise ValueError(f"Unexpected CSV columns: {table}")
            rows = [{key: convert(row[key]) for key, convert in fields.items()} for row in reader]
        if not rows or any(isinstance(v, float) and not math.isfinite(v)
                           for row in rows for v in row.values()):
            raise ValueError(f"Empty or nonfinite summary: {table}")
        if table != "overall_summary":
            key = next(iter(fields))
            if len({row[key] for row in rows}) != len(rows):
                raise ValueError(f"Duplicate category keys: {table}")
        elif len(rows) != 1:
            raise ValueError("Expected one overall summary")
        result[table] = rows
    return result


def main():
    from cassandra.query import BatchStatement
    summaries = read_csvs()
    counts = {}
    with connection() as session:
        for table, rows in summaries.items():
            columns = ["dataset_id", *TABLES[table]]
            # The logged batch replaces one tiny partition atomically; repeated loads
            # neither duplicate keys nor retain stale categories. Other partitions stay intact.
            batch = BatchStatement()
            # Give inserts a later timestamp than the partition tombstone explicitly.
            timestamp = time.time_ns() // 1000
            delete_at = session.prepare(f"DELETE FROM {KEYSPACE}.{table} USING TIMESTAMP ? WHERE dataset_id = ?")
            insert_at = session.prepare(
                f"INSERT INTO {KEYSPACE}.{table} ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)}) USING TIMESTAMP ?")
            batch.add(delete_at, (timestamp, DATASET_ID))
            for row in rows:
                batch.add(insert_at, (DATASET_ID, *[row[c] for c in TABLES[table]], timestamp + 1))
            session.execute(batch)
            counts[table] = len(rows)
            print(f"{table}: {len(rows)} rows written")
    status = {"status": "loaded", "dataset_id": DATASET_ID, "rows_written": counts,
              "total_rows_written": sum(counts.values())}
    (ROOT / "reports/cassandra_load.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"Successfully wrote {sum(counts.values())} rows. Run verify_cassandra.py next.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
