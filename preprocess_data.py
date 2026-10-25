"""Reproducible Phase 2 cleaning. Run: .venv/Scripts/python.exe preprocess_data.py.

Only pandas and its existing numpy dependency are needed. The raw CSV is read-only.
Missing numerical predictors remain nullable so later training can fit imputers
on the training split, without leaking validation/test distribution information.
"""

from pathlib import Path
import hashlib

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data/raw/food_delivery.csv"
OUTPUT = ROOT / "data/processed/quickr_clean.csv"
REPORT = ROOT / "reports/data_cleaning.md"
TOKENS = {"", "nan", "null", "none", "na", "n/a", "<na>", "nat"}
# A deliberately generous screening assumption for local food delivery.
# Do not infer this limit from duration_min or change coordinate signs to fit it.
MAX_LOCAL_DISTANCE_KM = 100.0
RENAME = {
    "ID": "order_id", "Delivery_person_ID": "delivery_person_id",
    "Delivery_person_Age": "delivery_person_age",
    "Delivery_person_Ratings": "delivery_person_rating",
    "Restaurant_latitude": "restaurant_latitude",
    "Restaurant_longitude": "restaurant_longitude",
    "Delivery_location_latitude": "delivery_latitude",
    "Delivery_location_longitude": "delivery_longitude",
    "Order_Date": "order_date", "Time_Orderd": "order_time",
    "Time_Order_picked": "pickup_time", "Weatherconditions": "weather",
    "Road_traffic_density": "traffic", "Vehicle_condition": "vehicle_condition",
    "Type_of_order": "order_type", "Type_of_vehicle": "vehicle_type",
    "multiple_deliveries": "multiple_deliveries", "Festival": "festival",
    "City": "city", "Time_taken(min)": "duration_min",
}
CATEGORIES = ["weather", "traffic", "city", "vehicle_type", "festival", "order_type"]
COORDINATES = ["restaurant_latitude", "restaurant_longitude",
               "delivery_latitude", "delivery_longitude"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(frame):
    return "\n```text\n" + frame.to_string() + "\n```\n"


def haversine(frame):
    """Great-circle distance in km, using mean Earth radius 6371.0088 km."""
    lat1, lon1, lat2, lon2 = [
        np.radians(frame[column].to_numpy(dtype=float, na_value=np.nan))
        for column in COORDINATES
    ]
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return pd.Series(2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1))),
                     index=frame.index)


def main():
    source_hash = sha256(SOURCE)
    phase1_paths = [ROOT / "explore_data.py", ROOT / "reports/dataset_exploration.md"]
    phase1_hashes = {path: sha256(path) for path in phase1_paths}
    raw = pd.read_csv(SOURCE, dtype="string", keep_default_na=False)
    if set(raw.columns) != set(RENAME):
        raise ValueError("Unexpected CSV schema; review columns before preprocessing.")
    df = raw.rename(columns=RENAME).copy()
    for column in df:
        df[column] = df[column].str.strip()
    df["weather"] = df["weather"].str.replace(r"(?i)^conditions\s+", "", regex=True)
    for column in df:
        df[column] = df[column].mask(df[column].str.lower().isin(TOKENS))
    before_missing = df.isna().sum()
    category_sources = {c: df[c].copy() for c in CATEGORIES}
    for column in CATEGORIES:
        df[column] = (df[column].str.lower().str.replace(r"[\s-]+", "_", regex=True))
    df["city"] = df["city"].replace({"metropolitian": "metropolitan"})

    # Keep identifiers for traceability, but do not treat them as numeric features.
    parse_failures = {}
    numeric = COORDINATES + ["delivery_person_age", "delivery_person_rating",
                            "vehicle_condition", "multiple_deliveries"]
    for column in numeric:
        parsed = pd.to_numeric(df[column], errors="coerce").astype("Float64")
        parse_failures[column] = int((df[column].notna() & parsed.isna()).sum())
        df[column] = parsed.mask(~np.isfinite(parsed.fillna(np.nan)))
    target_text = df["duration_min"]
    df["duration_min"] = pd.to_numeric(target_text.str.extract(
        r"^\(min\)\s*(\d+(?:\.\d+)?)$", expand=False), errors="coerce").astype("Float64")
    parse_failures["duration_min"] = int((target_text.notna() & df["duration_min"].isna()).sum())

    # Ages 15 and 50 are unusual here, not proof of errors. No adult-only
    # employment rule is assumed. Only impossible/implausible human ages are null.
    invalid_counts = {}
    rules = {
        "delivery_person_age": lambda s: (s <= 0) | (s > 120) | (s % 1 != 0),
        # The rating scale is an explicit project assumption, pending source confirmation.
        "delivery_person_rating": lambda s: (s < 0) | (s > 5),
        "multiple_deliveries": lambda s: (s < 0) | (s % 1 != 0),
        # Condition is an undocumented ordinal code: don't impose a guessed upper bound.
        "vehicle_condition": lambda s: (s < 0) | (s % 1 != 0),
    }
    for column, rule in rules.items():
        invalid = rule(df[column]).fillna(False)
        invalid_counts[column] = int(invalid.sum())
        df[column + "_invalid"] = invalid.astype("Int64")
        df.loc[invalid, column] = pd.NA
    df["age_review_flag"] = ((df["delivery_person_age"] < 18)
                             | (df["delivery_person_age"] > 80)).fillna(False).astype("Int64")
    for column in ["delivery_person_age", "vehicle_condition", "multiple_deliveries"]:
        df[column] = df[column].astype("Int64")

    # Parse times independently; do not attach a made-up date or infer a missing time.
    date_text = df["order_date"].copy()
    df["order_date"] = pd.to_datetime(date_text, format="%d-%m-%Y", errors="coerce")
    parse_failures["order_date"] = int((date_text.notna() & df["order_date"].isna()).sum())
    for column in ["order_time", "pickup_time"]:
        text = df[column].copy()
        parsed = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
        parse_failures[column] = int((text.notna() & parsed.isna()).sum())
        df[column] = parsed.dt.strftime("%H:%M:%S").astype("string")
        df[column.replace("_time", "_hour")] = parsed.dt.hour.astype("Int64")
    df["order_day_of_week"] = df["order_date"].dt.day_of_week.astype("Int64")
    df["order_month"] = df["order_date"].dt.month.astype("Int64")

    # Explicit route checks. A zero component is legal globally; reject only
    # the (0, 0) endpoint pair, which is a clear placeholder in this dataset.
    invalid_gps = df[COORDINATES].isna().any(axis=1)
    for column in COORDINATES:
        limit = 90 if "latitude" in column else 180
        invalid_gps |= df[column].abs().gt(limit).fillna(True)
    zero_endpoint = ((df["restaurant_latitude"].eq(0) & df["restaurant_longitude"].eq(0))
                     | (df["delivery_latitude"].eq(0) & df["delivery_longitude"].eq(0))).fillna(False)
    df["distance_km"] = haversine(df)
    long_route = df["distance_km"].gt(MAX_LOCAL_DISTANCE_KM).fillna(False)
    negative_route = df[COORDINATES].lt(0).any(axis=1)
    route_audit = pd.Series({
        "missing_or_out_of_range_GPS": int(invalid_gps.sum()),
        "zero_endpoint_pair": int(zero_endpoint.sum()),
        "distance_over_100_km_including_other_GPS_issues": int(long_route.sum()),
        "routes_with_negative_coordinate": int(negative_route.sum()),
        "negative_routes_over_100_km": int((negative_route & long_route).sum()),
    })
    # Sequential counts are disjoint, so they reconcile exactly with output size.
    keep = pd.Series(True, index=df.index)
    removals = {}
    reasons = {
        "Missing, nonfinite or nonpositive target": df["duration_min"].isna() | ~np.isfinite(df["duration_min"].fillna(np.nan)) | df["duration_min"].le(0),
        "Missing/out-of-range GPS": invalid_gps,
        "Zero endpoint pair": zero_endpoint,
        "Route over 100 km after previous checks": long_route,
    }
    for reason, bad in reasons.items():
        bad = bad.fillna(True)
        removals[reason] = int((keep & bad).sum())
        keep &= ~bad
    df = df.loc[keep].copy()
    if df.empty:
        raise ValueError("No usable routes remain; inspect input and validation rules.")

    # An explicit unknown category is honest imputation without inventing labels.
    # Numerical and time values remain null, with indicators for future models.
    before_imputation = df.isna().sum()
    imputation_counts = {}
    for column in CATEGORIES:
        imputation_counts[column] = int(df[column].isna().sum())
        df[column] = df[column].fillna("unknown")
    for column in ["delivery_person_age", "delivery_person_rating", "multiple_deliveries",
                   "vehicle_condition", "order_date", "order_time", "pickup_time"]:
        df[column + "_missing"] = df[column].isna().astype("Int64")

    # Verify both in-memory results and the actual serialized output.
    assert len(raw) - sum(removals.values()) == len(df)
    assert df["duration_min"].gt(0).all()
    assert df["distance_km"].between(0, MAX_LOCAL_DISTANCE_KM).all()
    assert np.isfinite(df["distance_km"]).all()
    assert not df[CATEGORIES].isna().any().any()
    assert sha256(SOURCE) == source_hash, "Original CSV changed."
    assert all(sha256(path) == digest for path, digest in phase1_hashes.items())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False, date_format="%Y-%m-%d", na_rep="")
    saved = pd.read_csv(OUTPUT)
    assert saved.shape == df.shape
    assert saved.isna().sum().to_dict() == df.isna().sum().to_dict()
    assert np.allclose(saved["distance_km"], df["distance_km"])
    assert np.allclose(saved["duration_min"], df["duration_min"].astype(float))

    missing_report = pd.DataFrame({
        "source_missing_after_placeholder_detection": before_missing,
        "retained_rows_before_category_imputation": before_imputation,
        "final_missing": df.isna().sum(),
    }).fillna(0).astype(int)
    category_report = []
    for column in CATEGORIES:
        mapping = pd.DataFrame({"source": category_sources[column], "standardized":
            category_sources[column].str.lower().str.replace(r"[\s-]+", "_", regex=True)})
        if column == "city":
            mapping["standardized"] = mapping["standardized"].replace({"metropolitian": "metropolitan"})
        mapping = mapping.fillna("unknown").drop_duplicates()
        category_report += [f"### {column}\n", table(mapping),
                            "Final frequencies:\n", table(df[column].value_counts())]
    report = [
        "# Quickr - Data Cleaning and Preprocessing\n",
        "Run `.venv/Scripts/python.exe preprocess_data.py` from the workspace. "
        "Paths resolve relative to the script, so other working directories also work.\n",
        f"Original: **{len(raw):,} rows, {len(raw.columns)} columns**. "
        f"Cleaned: **{len(df):,} rows, {len(df.columns)} columns**. "
        f"Removed: **{sum(removals.values()):,} rows**.\n",
        "## Records removed (sequential, non-overlapping reasons)\n", table(pd.Series(removals)),
        "No rows are removed for optional feature missingness, unusual ages or invalid ratings. "
        f"Exact source duplicates: {int(raw.duplicated().sum())}; none are silently dropped.\n",
        "## GPS investigation\n", table(route_audit),
        "Both endpoints must have finite coordinates in legal latitude/longitude ranges, "
        "and neither endpoint may be (0, 0). Negative coordinates are not intrinsically invalid. "
        "In this source, negative-coordinate routes are thousands of kilometres long, "
        "so they fail the separate 100 km local-delivery screening assumption. "
        "No coordinates are sign-corrected, guessed or imputed. This threshold is a "
        "project assumption, not a verified business service boundary.\n",
        "Retained Haversine distance (km):\n", table(df["distance_km"].describe()),
        "## Transformations and validation\n",
        "All text is trimmed; case-insensitive missing tokens are converted to proper nulls. "
        "Weather's `conditions ` prefix is removed before detecting missingness. "
        "Column names use snake_case; `Time_taken(min)` is replaced by numeric `duration_min`. "
        "Haversine uses mean Earth radius 6371.0088 km with numerical clipping.\n",
        "Nonmissing parse failures:\n", table(pd.Series(parse_failures)),
        "Invalid numeric values set to null (full source):\n", table(pd.Series(invalid_counts)),
        "Ages must be integral and in (0, 120]. Ages below 18 or above 80 get a review flag "
        "but are retained: there is no confirmed adult-only source policy. "
        "Ratings outside [0, 5] are nulled under an explicit five-point-scale assumption; "
        "valid low ratings are retained. Counts and condition codes must be nonnegative "
        "integers; condition code 3 is retained because its codebook is unavailable. "
        "Invalid-value and missing-value indicators preserve provenance.\n",
        f"Retained age review flags: {int(df['age_review_flag'].sum())}.\n",
        "Dates parse as day-month-year and export as ISO dates. Time values parse as HH:MM:SS "
        "and export as validated time-only strings, not timestamps with dummy dates. "
        "Hour, weekday (Monday=0) and month features are derived only from observed dates/times. "
        "No missing timestamps or midnight rollover dates are invented.\n",
        "## Missing values before and after\n",
        "Source counts include padded placeholders and `conditions NaN`. "
        "The middle column separates row filtering/validation from categorical imputation. "
        "Derived columns have no source missingness count (shown as zero).\n", table(missing_report),
        "Categories imputed as `unknown` in retained rows:\n", table(pd.Series(imputation_counts)),
        "No medians or modes are learned on the complete dataset. Missing numeric inputs and "
        "dates/times remain nullable with missing indicators; future ML must fit numeric "
        "imputers on its training partition only. Neither duration nor target-based grouping "
        "is used to fill any input. CSV nulls are empty fields.\n",
        "## Standardized categories\n",
        "All listed categories use lowercase with spaces/hyphens replaced by underscores. "
        "`Metropolitian` becomes `metropolitan`; weather mapping below starts after prefix removal.\n",
        *category_report,
        "## Final schema\n",
        "These are pandas pipeline types. CSV does not store types; downstream readers must "
        "explicitly parse order_date, nullable integers and HH:MM:SS time strings.\n",
        table(df.dtypes),
        "## Remaining limitations\n",
        "- Numeric and time nulls intentionally remain; this is a clean, typed feature table, "
        "not a dense model matrix. Some estimators will require training-only imputation.\n"
        "- Confirm the assumed rating scale and local-delivery distance threshold with the source owner.\n"
        "- Straight-line distance underestimates road distance and does not include road routing.\n"
        "- No timezone or pickup date is supplied; pickup timestamps and elapsed preparation time are not inferred.\n"
        "- The city column is a settlement category, not the actual city name. Condition codes lack definitions.\n"
        "- Missing categories use unknown rather than an invented majority category.\n"
        "- Before ML, define the prediction moment: pickup_time, multiple_deliveries, ratings and "
        "other features may be unavailable then. Exclude identifiers and assess temporal/person leakage.\n",
        "## Verification\n",
        "Execution and CSV read-back checks passed: dimensions, missing counts, positive targets, "
        "finite in-range distances and distance/target round-trips. Raw CSV and both Phase 1 "
        "files have unchanged SHA-256 fingerprints. No new dependencies were needed.\n",
        f"Raw SHA-256: `{source_hash}`\n",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Original: {raw.shape}; cleaned: {df.shape}; removed: {sum(removals.values())}")
    print(pd.Series(removals).to_string())
    print("Remaining missing values:\n" + df.isna().sum()[df.isna().any()].to_string())
    print(f"Verified output: {OUTPUT}\nReport: {REPORT}\nSource and Phase 1 unchanged.")


if __name__ == "__main__":
    main()
