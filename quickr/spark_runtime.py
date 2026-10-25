"""One lazy, process-local Spark session, shared by training and inference."""
import atexit
import os
from pathlib import Path
import sys
import threading

LOCK = threading.RLock()
_session = None
START_COUNT = 0


def get_spark():
    global _session, START_COUNT
    with LOCK:
        if _session is not None:
            return _session
        if os.name == "nt" and sys.version_info >= (3, 12):
            raise RuntimeError("Spark ML requires the project's Python 3.11 .venv-ml environment.")
        import pyspark
        from pyspark.sql import SparkSession
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        os.environ["SPARK_HOME"] = str(Path(pyspark.__file__).resolve().parent)
        os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
        # Set before JVM launch; includes room for the 150-tree model and transforms.
        os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--driver-memory 2g pyspark-shell")
        hadoop = Path(os.environ.get("HADOOP_HOME", "__missing__"))
        if hadoop.name.lower() == "bin" and (hadoop / "winutils.exe").is_file():
            os.environ["HADOOP_HOME"] = str(hadoop.parent)
        scratch = Path(__file__).resolve().parents[1] / ".spark-local"
        scratch.mkdir(exist_ok=True)
        _session = (SparkSession.builder.master("local[2]").appName("Quickr-Spark-ML")
                    .config("spark.ui.enabled", "false")
                    .config("spark.driver.host", "127.0.0.1")
                    .config("spark.driver.bindAddress", "127.0.0.1")
                    .config("spark.sql.shuffle.partitions", "2")
                    .config("spark.local.dir", str(scratch))
                    .config("spark.default.parallelism", "2").getOrCreate())
        _session.sparkContext.setLogLevel("WARN")
        START_COUNT += 1
        return _session


def shutdown():
    global _session
    with LOCK:
        if _session is not None:
            _session.stop()
            _session = None


atexit.register(shutdown)
