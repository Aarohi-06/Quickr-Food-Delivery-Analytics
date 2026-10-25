"""Inputs assumed known when a courier is assigned, before pickup."""
NUMERIC = ["distance_km", "delivery_person_age", "delivery_person_rating",
           "vehicle_condition", "order_hour", "order_day_of_week"]
CATEGORICAL = ["traffic", "weather", "city", "vehicle_type", "festival", "order_type"]
FEATURES = NUMERIC + CATEGORICAL
