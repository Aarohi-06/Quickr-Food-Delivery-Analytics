"""Project paths and the query-oriented analytics table definitions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYTICS = ROOT / "data/analytics"
KEYSPACE = "quickr_bda"
DATASET_ID = "clean_v1"
# Table/column identifiers are fixed here, never accepted from user SQL input.
GROUPS = {
    "traffic_summary": "traffic", "weather_summary": "weather",
    "city_summary": "city", "vehicle_type_summary": "vehicle_type",
    "festival_summary": "festival", "distance_band_summary": "distance_band",
    "age_band_summary": "age_band",
}
TABLES = {
    **{name: {category: str, "delivery_count": int, "total_duration_min": float,
              "average_duration_min": float} for name, category in GROUPS.items()},
    "order_type_summary": {"order_type": str, "delivery_count": int},
    "overall_summary": {
        "total_deliveries": int, "valid_duration_deliveries": int,
        "excluded_invalid_duration": int, "total_duration_min": float,
        "average_duration_min": float, "analytical_threshold_min": int,
        "deliveries_exceeding_threshold": int, "percent_exceeding_threshold": float,
    },
}
