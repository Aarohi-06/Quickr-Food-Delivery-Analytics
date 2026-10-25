# Quickr - Data Cleaning and Preprocessing

Run `.venv/Scripts/python.exe preprocess_data.py` from the workspace. Paths resolve relative to the script, so other working directories also work.

Original: **45,593 rows, 20 columns**. Cleaned: **41,522 rows, 37 columns**. Removed: **4,071 rows**.

## Records removed (sequential, non-overlapping reasons)


```text
Missing, nonfinite or nonpositive target       0
Missing/out-of-range GPS                       0
Zero endpoint pair                          3640
Route over 100 km after previous checks      431
```

No rows are removed for optional feature missingness, unusual ages or invalid ratings. Exact source duplicates: 0; none are silently dropped.

## GPS investigation


```text
missing_or_out_of_range_GPS                           0
zero_endpoint_pair                                 3640
distance_over_100_km_including_other_GPS_issues     431
routes_with_negative_coordinate                     431
negative_routes_over_100_km                         431
```

Both endpoints must have finite coordinates in legal latitude/longitude ranges, and neither endpoint may be (0, 0). Negative coordinates are not intrinsically invalid. In this source, negative-coordinate routes are thousands of kilometres long, so they fail the separate 100 km local-delivery screening assumption. No coordinates are sign-corrected, guessed or imputed. This threshold is a project assumption, not a verified business service boundary.

Retained Haversine distance (km):


```text
count    41522.000000
mean         9.720142
std          5.603035
min          1.465069
25%          4.657661
50%          9.193034
75%         13.680939
max         20.969518
```

## Transformations and validation

All text is trimmed; case-insensitive missing tokens are converted to proper nulls. Weather's `conditions ` prefix is removed before detecting missingness. Column names use snake_case; `Time_taken(min)` is replaced by numeric `duration_min`. Haversine uses mean Earth radius 6371.0088 km with numerical clipping.

Nonmissing parse failures:


```text
restaurant_latitude       0
restaurant_longitude      0
delivery_latitude         0
delivery_longitude        0
delivery_person_age       0
delivery_person_rating    0
vehicle_condition         0
multiple_deliveries       0
duration_min              0
order_date                0
order_time                0
pickup_time               0
```

Invalid numeric values set to null (full source):


```text
delivery_person_age        0
delivery_person_rating    53
multiple_deliveries        0
vehicle_condition          0
```

Ages must be integral and in (0, 120]. Ages below 18 or above 80 get a review flag but are retained: there is no confirmed adult-only source policy. Ratings outside [0, 5] are nulled under an explicit five-point-scale assumption; valid low ratings are retained. Counts and condition codes must be nonnegative integers; condition code 3 is retained because its codebook is unavailable. Invalid-value and missing-value indicators preserve provenance.

Retained age review flags: 25.

Dates parse as day-month-year and export as ISO dates. Time values parse as HH:MM:SS and export as validated time-only strings, not timestamps with dummy dates. Hour, weekday (Monday=0) and month features are derived only from observed dates/times. No missing timestamps or midnight rollover dates are invented.

## Missing values before and after

Source counts include padded placeholders and `conditions NaN`. The middle column separates row filtering/validation from categorical imputation. Derived columns have no source missingness count (shown as zero).


```text
                                source_missing_after_placeholder_detection  retained_rows_before_category_imputation  final_missing
age_review_flag                                                          0                                         0              0
city                                                                  1200                                      1097              0
delivery_latitude                                                        0                                         0              0
delivery_longitude                                                       0                                         0              0
delivery_person_age                                                   1854                                      1476           1476
delivery_person_age_invalid                                              0                                         0              0
delivery_person_age_missing                                              0                                         0              0
delivery_person_id                                                       0                                         0              0
delivery_person_rating                                                1908                                      1539           1539
delivery_person_rating_invalid                                           0                                         0              0
delivery_person_rating_missing                                           0                                         0              0
distance_km                                                              0                                         0              0
duration_min                                                             0                                         0              0
festival                                                               228                                       215              0
multiple_deliveries                                                    993                                       897            897
multiple_deliveries_invalid                                              0                                         0              0
multiple_deliveries_missing                                              0                                         0              0
order_date                                                               0                                         0              0
order_date_missing                                                       0                                         0              0
order_day_of_week                                                        0                                         0              0
order_hour                                                               0                                      1325           1325
order_id                                                                 0                                         0              0
order_month                                                              0                                         0              0
order_time                                                            1731                                      1325           1325
order_time_missing                                                       0                                         0              0
order_type                                                               0                                         0              0
pickup_hour                                                              0                                         0              0
pickup_time                                                              0                                         0              0
pickup_time_missing                                                      0                                         0              0
restaurant_latitude                                                      0                                         0              0
restaurant_longitude                                                     0                                         0              0
traffic                                                                601                                       408              0
vehicle_condition                                                        0                                         0              0
vehicle_condition_invalid                                                0                                         0              0
vehicle_condition_missing                                                0                                         0              0
vehicle_type                                                             0                                         0              0
weather                                                                616                                       420              0
```

Categories imputed as `unknown` in retained rows:


```text
weather          420
traffic          408
city            1097
vehicle_type       0
festival         215
order_type         0
```

No medians or modes are learned on the complete dataset. Missing numeric inputs and dates/times remain nullable with missing indicators; future ML must fit numeric imputers on its training partition only. Neither duration nor target-based grouping is used to fill any input. CSV nulls are empty fields.

## Standardized categories

All listed categories use lowercase with spaces/hyphens replaced by underscores. `Metropolitian` becomes `metropolitan`; weather mapping below starts after prefix removal.

### weather


```text
        source standardized
0        Sunny        sunny
1       Stormy       stormy
2   Sandstorms   sandstorms
4       Cloudy       cloudy
6          Fog          fog
15       Windy        windy
74     unknown      unknown
```

Final frequencies:


```text
weather
fog           6962
stormy        6932
cloudy        6881
sandstorms    6853
windy         6792
sunny         6682
unknown        420
```

### traffic


```text
     source standardized
0      High         high
1       Jam          jam
2       Low          low
3    Medium       medium
74  unknown      unknown
```

Final frequencies:


```text
traffic
low        14095
jam        12950
medium     10023
high        4046
unknown      408
```

### city


```text
           source  standardized
0           Urban         urban
1   Metropolitian  metropolitan
57     Semi-Urban    semi_urban
58        unknown       unknown
```

Final frequencies:


```text
city
metropolitan    31103
urban            9175
unknown          1097
semi_urban        147
```

### vehicle_type


```text
                source      standardized
0           motorcycle        motorcycle
1              scooter           scooter
14    electric_scooter  electric_scooter
1142           bicycle           bicycle
```

Final frequencies:


```text
vehicle_type
motorcycle          24197
scooter             13878
electric_scooter     3404
bicycle                43
```

### festival


```text
       source standardized
0          No           no
88        Yes          yes
1401  unknown      unknown
```

Final frequencies:


```text
festival
no         40495
yes          812
unknown      215
```

### order_type


```text
   source standardized
0   Snack        snack
2  Drinks       drinks
3  Buffet       buffet
6    Meal         meal
```

Final frequencies:


```text
order_type
snack     10511
meal      10398
drinks    10348
buffet    10265
```

## Final schema

These are pandas pipeline types. CSV does not store types; downstream readers must explicitly parse order_date, nullable integers and HH:MM:SS time strings.


```text
order_id                                  string
delivery_person_id                        string
delivery_person_age                        Int64
delivery_person_rating                   Float64
restaurant_latitude                      Float64
restaurant_longitude                     Float64
delivery_latitude                        Float64
delivery_longitude                       Float64
order_date                        datetime64[us]
order_time                                string
pickup_time                               string
weather                                   string
traffic                                   string
vehicle_condition                          Int64
order_type                                string
vehicle_type                              string
multiple_deliveries                        Int64
festival                                  string
city                                      string
duration_min                             Float64
delivery_person_age_invalid                Int64
delivery_person_rating_invalid             Int64
multiple_deliveries_invalid                Int64
vehicle_condition_invalid                  Int64
age_review_flag                            Int64
order_hour                                 Int64
pickup_hour                                Int64
order_day_of_week                          Int64
order_month                                Int64
distance_km                              float64
delivery_person_age_missing                Int64
delivery_person_rating_missing             Int64
multiple_deliveries_missing                Int64
vehicle_condition_missing                  Int64
order_date_missing                         Int64
order_time_missing                         Int64
pickup_time_missing                        Int64
```

## Remaining limitations

- Numeric and time nulls intentionally remain; this is a clean, typed feature table, not a dense model matrix. Some estimators will require training-only imputation.
- Confirm the assumed rating scale and local-delivery distance threshold with the source owner.
- Straight-line distance underestimates road distance and does not include road routing.
- No timezone or pickup date is supplied; pickup timestamps and elapsed preparation time are not inferred.
- The city column is a settlement category, not the actual city name. Condition codes lack definitions.
- Missing categories use unknown rather than an invented majority category.
- Before ML, define the prediction moment: pickup_time, multiple_deliveries, ratings and other features may be unavailable then. Exclude identifiers and assess temporal/person leakage.

## Verification

Execution and CSV read-back checks passed: dimensions, missing counts, positive targets, finite in-range distances and distance/target round-trips. Raw CSV and both Phase 1 files have unchanged SHA-256 fingerprints. No new dependencies were needed.

Raw SHA-256: `d293b6fc7157aef30fb34301216a3432ec895d407ce2ea9edddf942b416cdde1`
