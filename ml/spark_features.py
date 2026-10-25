"""Persistable Spark preprocessing shared by batch training and inference."""
from ml.features import NUMERIC, CATEGORICAL

INDICATORS = ["delivery_person_age", "delivery_person_rating", "order_hour"]


def stages():
    from pyspark.ml.feature import SQLTransformer, Imputer, StringIndexer, OneHotEncoder, VectorAssembler
    expressions = []
    for column in NUMERIC:
        # Inputs may be strings from CSV or doubles from the prediction schema.
        cast = f"CAST(`{column}` AS DOUBLE)"
        missing = f"({cast} IS NULL OR isnan({cast}) OR abs({cast}) = CAST('Infinity' AS DOUBLE))"
        expressions.append(f"CASE WHEN {missing} THEN NULL ELSE {cast} END AS `{column}_value`")
        if column in INDICATORS:
            expressions.append(f"CASE WHEN {missing} THEN 1.0 ELSE 0.0 END AS `{column}_missing_ml`")
    for column in CATEGORICAL:
        value = f"lower(trim(`{column}`))"
        expressions.append(f"CASE WHEN {value} IS NULL OR {value} IN ('', 'nan', 'null', 'none', 'na', 'n/a', '<na>') "
                           f"THEN 'unknown' ELSE regexp_replace({value}, '[ -]+', '_') END AS `{column}_normalized`")
    normalize = SQLTransformer(statement="SELECT *, " + ", ".join(expressions) + " FROM __THIS__")
    impute = Imputer(strategy="median", inputCols=[c + "_value" for c in NUMERIC],
                     outputCols=[c + "_imputed" for c in NUMERIC], relativeError=0.0)
    indexers = [StringIndexer(inputCol=c + "_normalized", outputCol=c + "_index",
                              handleInvalid="keep", stringOrderType="alphabetAsc") for c in CATEGORICAL]
    encode = OneHotEncoder(inputCols=[c + "_index" for c in CATEGORICAL],
                           outputCols=[c + "_encoded" for c in CATEGORICAL],
                           handleInvalid="keep", dropLast=False)
    assemble = VectorAssembler(inputCols=[c + "_imputed" for c in NUMERIC]
        + [c + "_missing_ml" for c in INDICATORS]
        + [c + "_encoded" for c in CATEGORICAL], outputCol="features", handleInvalid="error")
    return [normalize, impute, *indexers, encode, assemble]
