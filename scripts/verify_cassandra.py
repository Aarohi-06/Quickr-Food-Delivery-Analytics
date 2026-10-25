"""Compare database row counts AND values against the actual nine CSVs."""
from pathlib import Path
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quickr.config import DATASET_ID, ROOT
from quickr.database import connection, read_summary
from scripts.load_analytics import read_csvs


def main():
    expected = read_csvs()
    checks = {}
    with connection() as session:
        for table, source in expected.items():
            actual = read_summary(session, table)
            assert len(actual) == len(source), f"Row count mismatch: {table}"
            key = None if table == "overall_summary" else next(iter(source[0]))
            for wanted in source:
                matching = [row for row in actual if key is None or row[key] == wanted[key]]
                assert len(matching) == 1, f"Missing/duplicate key in {table}"
                for column, value in wanted.items():
                    found = matching[0][column]
                    assert (math.isclose(found, value) if isinstance(value, float)
                            else found == value), f"Value mismatch {table}.{column}"
            checks[table] = {"rows": len(actual), "sample": actual[0]}
            print(table, len(actual), "rows verified; sample:", actual[0])
    status = {"status": "verified", "dataset_id": DATASET_ID, "tables": checks}
    (ROOT / "reports/cassandra_verification.json").write_text(json.dumps(status, indent=2), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
