"""Spark-primary inference with an explicitly selected sklearn backup."""
from functools import lru_cache
import math
from pathlib import Path
from ml.features import FEATURES, NUMERIC, CATEGORICAL
from ml.input_validation import normalize_inputs
from quickr.config import ROOT


@lru_cache(maxsize=2)
def _spark_model(path, version):
    from pyspark.ml import PipelineModel
    from quickr.spark_runtime import LOCK, get_spark
    with LOCK:
        get_spark()
        return PipelineModel.load(path)


def load_model(backend="spark"):
    if backend == "spark":
        directory = ROOT / "models/spark"
        if not (directory / "metrics.json").is_file():
            raise FileNotFoundError("Complete Spark model artifacts are missing. Train with .venv-ml/Scripts/python.exe ml/train_model.py")
        version = (directory / "metrics.json").stat().st_mtime_ns
        return {"backend":"spark", "model":_spark_model(str(directory / "pipeline"), version), "directory":directory}
    if backend == "sklearn":
        import joblib
        directory = ROOT / "models/sklearn_backup"
        return {"backend":"sklearn", "model":joblib.load(directory / "delivery_duration_pipeline.joblib"), "directory":directory}
    raise ValueError("Backend must be spark or sklearn")


def predict_duration(values, model=None):
    row = normalize_inputs(values)
    bundle = model if model is not None else load_model("spark")
    if bundle["backend"] == "spark":
        from pyspark.sql.types import StructType, StructField, DoubleType, StringType
        from quickr.spark_runtime import LOCK, get_spark
        schema = StructType([StructField(c,DoubleType(),True) for c in NUMERIC]
                            + [StructField(c,StringType(),True) for c in CATEGORICAL])
        # Explicit schema handles single-row requests with nullable numeric fields.
        with LOCK:
            frame = get_spark().createDataFrame([tuple(row[c] for c in FEATURES)],schema)
            results = bundle["model"].transform(frame).select("prediction").collect()
        if len(results) != 1:
            raise ValueError("Spark prediction did not retain exactly one input row")
        prediction = float(results[0].prediction)
    else:
        import pandas as pd
        prediction = float(bundle["model"].predict(pd.DataFrame([row],columns=FEATURES))[0])
    if not math.isfinite(prediction) or prediction <= 0:
        raise ValueError("Model returned an invalid duration")
    return prediction
