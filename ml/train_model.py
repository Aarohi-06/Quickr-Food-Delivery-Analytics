"""Primary Spark ML training entrypoint. Run with .venv-ml/Scripts/python.exe.

The original sklearn implementation is recoverable in ml/sklearn_train_model.py.
No original model artifacts are overwritten. An existing Spark pipeline is not overwritten.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.features import NUMERIC, CATEGORICAL, FEATURES
from ml.spark_features import stages, INDICATORS
from quickr.config import ROOT
from quickr.spark_runtime import get_spark, shutdown


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    from pyspark.ml import Pipeline, PipelineModel
    from pyspark.ml.regression import RandomForestRegressor
    from pyspark.ml.evaluation import RegressionEvaluator
    from pyspark.sql import functions as F
    started = time.perf_counter()
    output = ROOT / "models/spark"
    if (output / "pipeline").exists():
        raise FileExistsError("Spark pipeline already exists; preserve it before intentionally retraining.")
    source = ROOT / "data/processed/quickr_clean.csv"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Reconstruct the exact prior evaluation membership, after verifying all keys.
    with source.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    ids = [r["order_id"] for r in source_rows]
    if any(not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError("Source order IDs are missing or nonunique; exact split reconstruction rejected.")
    test_path = ROOT / "models/sklearn_backup/test_predictions.csv"
    with test_path.open(newline="", encoding="utf-8") as handle:
        old_test = list(csv.DictReader(handle))
    test_ids = [r["order_id"] for r in old_test]
    if len(test_ids) != len(set(test_ids)) or not set(test_ids).issubset(ids):
        raise ValueError("Prior test IDs are nonunique or not covered by source.")
    baseline = json.loads((ROOT / "models/sklearn_backup/metrics.json").read_text())
    if baseline["source_sha256"] != digest or len(test_ids) != baseline["test_rows"] or len(ids) != baseline["total_rows"]:
        raise ValueError("Source fingerprint or split counts differ from the baseline.")
    by_id = {r["order_id"]: r for r in source_rows}
    if any(float(by_id[r["order_id"]]["duration_min"]) != float(r["actual_duration_min"]) for r in old_test):
        raise ValueError("Test targets differ from baseline records.")
    test_id_set = set(test_ids)
    training_median = statistics.median(float(r["duration_min"]) for r in source_rows if r["order_id"] not in test_id_set)
    baseline_mae = sum(abs(float(r["actual_duration_min"])-training_median) for r in old_test)/len(old_test)
    connector = (ROOT / ".spark-packages/spark-cassandra-connector-assembly_2.12-3.5.1.jar").as_uri()
    os.environ["PYSPARK_SUBMIT_ARGS"] = os.environ.get(
        "PYSPARK_SUBMIT_ARGS", "--driver-memory 2g pyspark-shell").replace(
            "pyspark-shell", f'--jars "{connector}" pyspark-shell')
    spark = get_spark()
    df = (spark.read.format("org.apache.spark.sql.cassandra")
          .options(keyspace="quickr_bda", table="cleaned_delivery_records",
                   **{"spark.cassandra.connection.host": "127.0.0.1",
                      "spark.cassandra.connection.port": "9042"}).load()
          .select(*[F.col(c).cast("string").alias(c) for c in source_rows[0]]))
    df = df.withColumn("duration_min", F.col("duration_min").cast("double"))
    membership = spark.read.option("header", True).csv(test_path.as_posix()).select("order_id")
    train = df.join(membership, "order_id", "left_anti").select("order_id", *FEATURES, "duration_min").cache()
    test = df.join(membership, "order_id", "left_semi").select("order_id", *FEATURES, "duration_min").cache()
    train_count, test_count = train.count(), test.count()
    assert train_count == baseline["train_rows"] and test_count == baseline["test_rows"]
    print(f"Verified exact baseline split: {train_count} train / {test_count} test", flush=True)
    forest = RandomForestRegressor(labelCol="duration_min", featuresCol="features", numTrees=150,
        maxDepth=18, minInstancesPerNode=3, seed=42, featureSubsetStrategy="all", maxBins=32,
        bootstrap=True, subsamplingRate=1.0)
    print("Training Spark Random Forest (150 trees, depth 18)...", flush=True)
    model = Pipeline(stages=stages() + [forest]).fit(train)
    predictions = model.transform(test).cache()
    metrics = {name + ("_min" if name != "r2" else ""): RegressionEvaluator(
        labelCol="duration_min", predictionCol="prediction", metricName=name).evaluate(predictions)
        for name in ["mae", "rmse", "r2"]}
    output.mkdir(parents=True, exist_ok=True)
    model.write().save(str(output / "pipeline"))
    loaded = PipelineModel.load(str(output / "pipeline"))
    sample = test.orderBy("order_id").limit(8).cache()
    expected = model.transform(sample).select("order_id", "prediction").orderBy("order_id").collect()
    actual = loaded.transform(sample).select("order_id", "prediction").orderBy("order_id").collect()
    assert all(a.order_id == b.order_id and math.isclose(a.prediction,b.prediction,abs_tol=1e-9)
               for a,b in zip(expected,actual)) and len(expected)==len(actual)==8
    metrics.update(backend="spark", spark_version=spark.version, train_rows=train_count,
                   test_rows=test_count, total_rows=len(ids), random_state=42, test_fraction=0.2,
                   split_method="exact preserved sklearn test order-ID membership", source_sha256=digest,
                   baseline_mae_min=baseline_mae, elapsed_seconds=time.perf_counter()-started)
    metadata = {"backend":"spark", "target":"duration_min", "feature_order":FEATURES,
                "numeric_features":NUMERIC, "categorical_features":CATEGORICAL,
                "missing_indicator_features":INDICATORS, "category_values":{},
                "numeric_training_medians":{}, "parameters":{"numTrees":150,"maxDepth":18,"minInstancesPerNode":3,"seed":42,"featureSubsetStrategy":"all","maxBins":32}}
    # Imputer and indexer information comes from the FITTED training-only stages.
    surrogate = model.stages[1].surrogateDF.first().asDict()
    metadata["numeric_training_medians"] = {c:float(surrogate[c+"_value"]) for c in NUMERIC}
    for c,indexer in zip(CATEGORICAL,model.stages[2:2+len(CATEGORICAL)]):
        metadata["category_values"][c]=list(indexer.labels)
    for filename,value in [("metrics.json",metrics),("feature_info.json",metadata)]:
        (output/filename).write_text(json.dumps(value,indent=2),encoding="utf-8")
    rows = [dict(order_id=r.order_id, actual_duration_min=r.duration_min,
                 predicted_duration_min=r.prediction, residual_min=r.duration_min-r.prediction)
            for r in predictions.select("order_id","duration_min","prediction").orderBy("order_id").collect()]
    write_csv(output/"test_predictions.csv", ["order_id","actual_duration_min","predicted_duration_min","residual_min"],rows)
    vector_meta=predictions.schema["features"].metadata["ml_attr"]["attrs"]
    names={a["idx"]:a["name"] for group in vector_meta.values() for a in group}
    weights=model.stages[-1].featureImportances.toArray()
    importance=sorted([{"feature":names.get(i,f"feature_{i}"),"importance":float(v)} for i,v in enumerate(weights)],key=lambda r:r["importance"],reverse=True)
    write_csv(output/"feature_importance.csv",["feature","importance"],importance)
    write_csv(output/"split_membership.csv",["order_id","split"],
              [{"order_id":key,"split":"test" if key in test_id_set else "train"} for key in ids])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    print(json.dumps(metrics,indent=2),flush=True)
    print("PASS: complete Spark pipeline saved and reloaded; eight predictions matched.",flush=True)
    predictions.unpersist(); sample.unpersist(); train.unpersist(); test.unpersist()


if __name__ == "__main__":
    try:
        main()
    finally:
        shutdown()
