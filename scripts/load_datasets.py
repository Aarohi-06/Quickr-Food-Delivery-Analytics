"""Load and verify the two existing CSV snapshots; no analytics/model writes."""
import argparse
import csv
from datetime import date
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quickr.config import KEYSPACE, ROOT
from quickr.database import connection

DATASETS = {
    "original_delivery_records": ROOT / "data/raw/food_delivery.csv",
    "cleaned_delivery_records": ROOT / "data/processed/quickr_clean.csv",
}
NULLS = {"", "nan", "null", "none", "na", "n/a", "<na>", "nat"}


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def read_source(table, path, types):
    """Validate every value before any database write; retain text verbatim."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; see README dataset storage instructions.")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        if columns != list(types):
            raise ValueError(f"Unexpected CSV columns in {path}")
        rows = []
        for number, row in enumerate(reader, 1):
            values = [number]
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV record {number} in {path}")
            for column, kind in types.items():
                value = row[column]
                try:
                    if value.strip().lower() in NULLS:
                        value = None
                    elif kind == "double":
                        value = float(value)
                        if not math.isfinite(value):
                            raise ValueError("Nonfinite number")
                    elif kind == "int":
                        value = int(value)
                    elif kind == "date":
                        value = date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(f"{path}, record {number}, {column}: {value!r}") from exc
                values.append(value)
            rows.append(tuple(values))
    print(f"{table}: validated {len(rows):,} source records", flush=True)
    return columns, rows


def schema_definitions():
    schema = (ROOT / "cassandra/dataset_schema.cql").read_text(encoding="utf-8")
    schema = "\n".join(line for line in schema.splitlines() if not line.startswith("--"))
    definitions = {}
    for statement in schema.split(";"):
        if not statement.strip():
            continue
        table = statement.split("quickr_bda.", 1)[1].split()[0]
        types = {}
        for line in statement.splitlines():
            if line.strip().startswith('"'):
                name, kind = line.strip().rstrip(",").rsplit(" ", 1)
                types[name[1:-1]] = kind
        definitions[table] = (statement, types)
    return definitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Read and compare without writes")
    args = parser.parse_args()
    definitions = schema_definitions()
    sources = {table: read_source(table, path, definitions[table][1])
               for table, path in DATASETS.items()}
    from cassandra.concurrent import execute_concurrent_with_args

    with connection() as session:
        # Snapshot existing small tables to verify that their schema/data stay intact.
        existing = [r.table_name for r in session.execute(
            "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s", (KEYSPACE,))
            if r.table_name not in DATASETS]
        def snapshot():
            return {table: set(session.execute(f"SELECT * FROM {KEYSPACE}.{quoted(table)}"))
                    for table in existing}
        before = snapshot()
        for table, (columns, rows) in sources.items():
            target = f"{KEYSPACE}.{table}"
            names = ["source_row_number", *columns]
            if not args.verify_only:
                session.execute(definitions[table][0])
                insert = session.prepare(
                    f"INSERT INTO {target} ({', '.join(map(quoted, names))}) "
                    f"VALUES ({', '.join('?' for _ in names)})")
                for start in range(0, len(rows), 1000):
                    chunk = rows[start:start + 1000]
                    results = execute_concurrent_with_args(
                        session, insert, chunk, concurrency=32, raise_on_first_error=False)
                    errors = [(start + i + 1, str(result))
                              for i, (success, result) in enumerate(results) if not success]
                    if errors:
                        raise RuntimeError(f"{table}: insertion errors (record, error): {errors}")
                    print(f"{table}: inserted {min(start + 1000, len(rows)):,}/{len(rows):,}", flush=True)
            # A paged full read verifies every column and detects extra/missing keys.
            found = set()
            for actual in session.execute(f"SELECT {', '.join(map(quoted, names))} FROM {target}"):
                number = actual[0]
                if not 1 <= number <= len(rows) or number in found:
                    raise ValueError(f"Unexpected/duplicate source row in {table}: {number}")
                expected = rows[number - 1]
                for name, wanted, value in zip(names, expected, actual):
                    equal = (str(value) == wanted.isoformat() if isinstance(wanted, date)
                             else value == wanted)
                    if not equal:
                        raise ValueError(f"Mismatch {table}, source row {number}, column {name}")
                found.add(number)
            if len(found) != len(rows):
                raise ValueError(f"{table}: stored {len(found)}, expected {len(rows)}")
            print(f"VERIFIED {target}: {len(found):,} records; all columns match source", flush=True)
            print("Sample:", session.execute(f"SELECT * FROM {target} LIMIT 1").one(), flush=True)
        if before != snapshot():
            raise RuntimeError("Existing table contents changed during loading/verification")
        print(f"Verified {len(existing)} existing tables unchanged.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
