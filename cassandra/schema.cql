-- Quickr local academic schema. Does not touch unrelated keyspaces.

CREATE KEYSPACE IF NOT EXISTS quickr_bda WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS quickr_bda.traffic_summary (
    dataset_id text,
    traffic text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), traffic)
);

CREATE TABLE IF NOT EXISTS quickr_bda.weather_summary (
    dataset_id text,
    weather text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), weather)
);

CREATE TABLE IF NOT EXISTS quickr_bda.city_summary (
    dataset_id text,
    city text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), city)
);

CREATE TABLE IF NOT EXISTS quickr_bda.vehicle_type_summary (
    dataset_id text,
    vehicle_type text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), vehicle_type)
);

CREATE TABLE IF NOT EXISTS quickr_bda.festival_summary (
    dataset_id text,
    festival text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), festival)
);

CREATE TABLE IF NOT EXISTS quickr_bda.distance_band_summary (
    dataset_id text,
    distance_band text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), distance_band)
);

CREATE TABLE IF NOT EXISTS quickr_bda.age_band_summary (
    dataset_id text,
    age_band text,
    delivery_count bigint,
    total_duration_min double,
    average_duration_min double,
    PRIMARY KEY ((dataset_id), age_band)
);

CREATE TABLE IF NOT EXISTS quickr_bda.order_type_summary (
    dataset_id text,
    order_type text,
    delivery_count bigint,
    PRIMARY KEY ((dataset_id), order_type)
);

CREATE TABLE IF NOT EXISTS quickr_bda.overall_summary (
    dataset_id text,
    total_deliveries bigint,
    valid_duration_deliveries bigint,
    excluded_invalid_duration bigint,
    total_duration_min double,
    average_duration_min double,
    analytical_threshold_min bigint,
    deliveries_exceeding_threshold bigint,
    percent_exceeding_threshold double,
    PRIMARY KEY (dataset_id)
);

CREATE TABLE IF NOT EXISTS quickr_bda.demo_operations (demo_id text PRIMARY KEY, note text);
