"""Bounded local Cassandra connections; no implicit schema/data writes."""
from contextlib import contextmanager
import socket

from quickr.config import DATASET_ID, KEYSPACE, TABLES


@contextmanager
def connection(use_keyspace=True):
    """Close the cluster even when a connection/query fails (also used by Streamlit)."""
    cluster = None
    try:
        with socket.create_connection(("127.0.0.1", 9042), timeout=2):
            pass
        from cassandra.cluster import Cluster
        cluster = Cluster(["127.0.0.1"], port=9042, connect_timeout=5,
                          control_connection_timeout=5)
        session = cluster.connect(KEYSPACE if use_keyspace else None)
        session.default_timeout = 10
        yield session
    except Exception as exc:
        raise RuntimeError(
            f"Cassandra operation failed at 127.0.0.1:9042: {type(exc).__name__}: {exc}. "
            "Start the installed Cassandra manually in an Administrator terminal, "
            "then run the initialization and loader commands in README.md."
        ) from exc
    finally:
        if cluster is not None:
            cluster.shutdown()


def read_summary(session, table):
    """Read one bounded historical-summary partition using a prepared statement."""
    if table not in TABLES:
        raise ValueError("Unknown summary table")
    statement = session.prepare(f"SELECT * FROM {KEYSPACE}.{table} WHERE dataset_id = ?")
    return [dict(row._asdict()) for row in session.execute(statement, (DATASET_ID,))]
