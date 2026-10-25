"""Initialize only the project's quickr_bda keyspace, never other keyspaces."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quickr.config import ROOT
from quickr.database import connection


def main():
    schema = (ROOT / "cassandra/schema.cql").read_text(encoding="utf-8")
    schema = "\n".join(line for line in schema.splitlines() if not line.lstrip().startswith("--"))
    with connection(use_keyspace=False) as session:
        for statement in schema.split(";"):
            if statement.strip():
                session.execute(statement)
    print("Initialized quickr_bda keyspace and its tables successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
