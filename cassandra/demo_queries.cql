-- Start installed Cassandra manually in an Administrator terminal: cassandra
-- In another terminal: cqlsh 127.0.0.1 9042
-- After Python initialization/loading, run these in cqlsh or SOURCE this file.
DESCRIBE KEYSPACES;
USE quickr_bda;
DESCRIBE TABLES;
DESCRIBE TABLE traffic_summary;

-- Small summary table only; never use an unbounded scan on a large raw-data table.
SELECT * FROM traffic_summary;
SELECT * FROM overall_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM traffic_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM traffic_summary WHERE dataset_id = 'clean_v1' AND traffic = 'jam';
SELECT * FROM weather_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM weather_summary WHERE dataset_id = 'clean_v1' AND weather = 'sunny';
SELECT * FROM festival_summary WHERE dataset_id = 'clean_v1' AND festival = 'yes';
SELECT * FROM distance_band_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM distance_band_summary WHERE dataset_id = 'clean_v1' AND distance_band = '[0,5) km';
SELECT * FROM city_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM vehicle_type_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM age_band_summary WHERE dataset_id = 'clean_v1';
SELECT * FROM order_type_summary WHERE dataset_id = 'clean_v1';
SELECT COUNT(*) FROM traffic_summary WHERE dataset_id = 'clean_v1';

-- Disposable demonstration record only; analytical results remain untouched.
INSERT INTO demo_operations (demo_id, note) VALUES ('viva_example', 'Initial demo note');
SELECT * FROM demo_operations WHERE demo_id = 'viva_example';
UPDATE demo_operations SET note = 'Updated demo note' WHERE demo_id = 'viva_example';
SELECT * FROM demo_operations WHERE demo_id = 'viva_example';
DELETE FROM demo_operations WHERE demo_id = 'viva_example';
SELECT * FROM demo_operations WHERE demo_id = 'viva_example';
