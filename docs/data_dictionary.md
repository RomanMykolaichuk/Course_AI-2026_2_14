# Data Dictionary

This document defines the canonical analytical model used by the project.

The primary source is not a simple “one row = one strike location” dataset. A single row can describe an attack interval for one weapon model and can contain a broad or multi-region target description. For that reason, the canonical model is relational rather than forcing every source row into one oblast.

## SQLite storage conventions

The project uses SQLite as the local relational store.

- timestamps are stored as ISO 8601 text;
- full date-time values are interpreted in the documented source timezone and normalized to UTC;
- source values that contain only a calendar date remain `YYYY-MM-DD` rather than receiving an invented time;
- integer counts use SQLite `INTEGER`;
- floating-point measurements use SQLite `REAL`;
- missing values remain `NULL`;
- every connection enables `PRAGMA foreign_keys = ON`.

Examples:

```text
2026-09-22
2026-09-22T07:30:00Z
```

## Core entities

### 1. attack_events

One row represents one normalized source observation for a specific attack interval and weapon model.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| event_id | TEXT | yes | Stable internal identifier |
| time_start | TEXT | yes | ISO 8601 source date or normalized UTC date-time |
| time_end | TEXT | no | ISO 8601 source date or normalized UTC date-time |
| weapon_model | TEXT | no | Normalized missile/UAV model |
| weapon_category | TEXT | no | Broad category such as UAV, cruise missile, ballistic missile |
| launch_place | TEXT | no | Source-provided launch location or area |
| target_raw | TEXT | no | Target description exactly/semantically preserved from the source |
| carrier | TEXT | no | Launch platform/carrier |
| launched | INTEGER | no | Number launched; null means unknown, not zero |
| destroyed | INTEGER | no | Number destroyed; null means unknown |
| not_reach_goal | INTEGER | no | Number reported as not reaching the target |
| border_crossing | INTEGER | no | Derived total when the source value is numeric or a parseable destination→count mapping |
| border_crossing_raw | TEXT | no | Original source representation, including structured values such as destination→count mappings |
| still_attacking | INTEGER | no | Number still attacking at report time |
| source_name | TEXT | yes | Dataset/source identifier |
| source_url | TEXT | no | URL of original source record/page where available |
| source_record_id | TEXT | no | Stable source-side identifier when available |
| source_snapshot | TEXT | yes | Snapshot/version filename or acquisition ID |
| ingested_at | TEXT | yes | SQLite-generated ingestion timestamp |

### 2. regions

Canonical oblast/reference table.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| region_code | TEXT | yes | Stable internal region code |
| name_uk | TEXT | yes | Ukrainian region name |
| name_en | TEXT | no | English region name |
| boundary_source | TEXT | no | GIS boundary source |
| boundary_version | TEXT | no | Release/version of boundary data |

### 3. attack_event_regions

Many-to-many link between attack observations and regions.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| event_id | TEXT | yes | FK to `attack_events` |
| region_code | TEXT | yes | FK to `regions` |
| relation_type | TEXT | yes | e.g. `affected`, `target`, `destroyed_location`, `mentioned` |
| attribution_method | TEXT | yes | e.g. `source_explicit_parsed`, `parsed`, `manual_review` |
| attribution_quality | TEXT | no | Optional quality flag such as `high`, `medium`, `low` |

This table prevents a multi-oblast target string from being incorrectly collapsed into one region.

### 4. alert_intervals

Optional historical alert layer.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| alert_id | TEXT | yes | Stable alert identifier |
| region_code | TEXT | yes | Canonical region code |
| alert_type | TEXT | yes | Alert/threat type |
| started_at | TEXT | yes | ISO 8601 UTC start time |
| finished_at | TEXT | no | ISO 8601 UTC end time |
| source_name | TEXT | yes | Alert source/API |
| source_snapshot | TEXT | yes | Snapshot/version |

### 5. weather_observations

Optional environmental enrichment table.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| observed_at | TEXT | yes | ISO 8601 UTC historical weather timestamp |
| region_code | TEXT | yes | Region to which the feature is aggregated |
| temperature_c | REAL | no | Temperature |
| wind_speed_ms | REAL | no | Wind speed |
| wind_direction_deg | REAL | no | Wind direction |
| precipitation_mm | REAL | no | Precipitation |
| cloud_cover_pct | REAL | no | Cloud cover |
| surface_pressure_hpa | REAL | no | Surface pressure |
| source_name | TEXT | yes | e.g. ERA5 |
| aggregation_method | TEXT | yes | Spatial aggregation rule |

### 6. dataset_builds

Database provenance table.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| build_id | TEXT | yes | Stable build identifier |
| source_name | TEXT | yes | Source used for the build/load |
| source_snapshot | TEXT | yes | Snapshot filename/version |
| source_sha256 | TEXT | no | SHA-256 of source snapshot |
| code_commit_sha | TEXT | no | Git commit used for the transformation |
| transformation_version | TEXT | no | ETL/schema transformation version |
| built_at | TEXT | yes | Build timestamp |
| rows_loaded | INTEGER | no | Number of rows loaded |
| notes | TEXT | no | Build notes |

### 7. model_evaluations

Retrospective ML evaluation registry. It stores metrics/provenance, not fitted models.

| Field | SQLite type | Required | Description |
|---|---|---:|---|
| evaluation_id | TEXT | yes | Deterministic evaluation identifier |
| source_build_id | TEXT | no | FK to the source dataset build |
| task | TEXT | yes | Historical evaluation task |
| target_name | TEXT | yes | Target used by the experiment |
| evaluated_at | TEXT | yes | UTC evaluation timestamp |
| deployment_status | TEXT | yes | Quality/deployment gate result |
| comparison_json | TEXT | yes | Compact model-comparison metadata |
| validation_json | TEXT | yes | Validation metrics |
| test_json | TEXT | yes | Test metrics |
| notes | TEXT | no | Target semantics, policies and gate explanation |

The table intentionally contains no model blob, pickle path or future prediction output.

## ML feature table

The model should train from a derived table produced from the canonical entities, not directly from raw CSV.

Current retrospective grain:

\`country × calendar_day\`

The initial oblast-level label formulation is blocked by the regional-data quality gate.

Exported national daily fields:

| Field | Meaning |
|---|---|
| date | Historical calendar date |
| source_event_present | Source-record presence label used only for diagnostics |
| day_of_week | Calendar feature |
| month | Calendar feature |
| day_of_year | Calendar feature |
| is_weekend | Calendar feature |
| event_count_lag1 | Previous-day canonical source-event count |
| event_count_lag7 | Canonical source-event count seven days earlier |
| launched_known_lag1 | Previous-day sum of known launched counts |
| uav_event_count_lag1 | Previous-day UAV source-event count |
| missile_event_count_lag1 | Previous-day missile source-event count |
| event_count_roll7_prior | Mean source-event count over prior 7 days |
| event_count_roll30_prior | Mean source-event count over prior 30 days |
| launched_roll7_prior | Prior 7-day rolling known-launch mean |
| days_since_previous_source_event | Historical recency feature |
| history_days_available | Number of historical days available before the row |

Current-day \`event_count\`, \`launched_known_total\`, \`destroyed_known_total\` and category counts are not exported as model predictors.

## Leakage rules

Features must be computable using information available strictly before the prediction bucket.

Do not use as predictors:

- final outcome fields from the same future interval;
- future alert duration;
- destroyed/impact information published after the prediction cutoff;
- manually inferred future labels;
- aggregates that accidentally include the target interval.

## Source-to-canonical mapping for the primary Kaggle dataset

| Source field | Canonical field | Rule |
|---|---|---|
| `time_start` | `time_start` | date-only → preserve `YYYY-MM-DD`; date-time → interpret as Europe/Kyiv when naive and normalize to UTC |
| `time_end` | `time_end` | same rule when present |
| `model` | `weapon_model` | normalize via weapon reference table |
| model reference category | `weapon_category` | join from `missiles_and_uavs.csv` |
| `launch_place` | `launch_place` | preserve source text |
| `target` | `target_raw` | preserve exactly/semantically; explicit oblast mentions may create medium-confidence `target` relations |
| `affected_region` (optional) | `attack_event_regions` | when present, explicit administrative-region mentions create high-confidence `affected` relations; the 2026-09-22 acquired CSV does not contain this column |
| `carrier` | `carrier` | preserve/normalize |
| `launched` | `launched` | integer/null; never replace null with zero |
| `destroyed` | `destroyed` | integer/null |
| `not_reach_goal` | `not_reach_goal` | integer/null |
| `border_crossing` | `border_crossing`, `border_crossing_raw` | preserve source text; derive total from numeric values or parseable destination→count mappings |
| `still_attacking` | `still_attacking` | integer/null |
| source field/page | `source_url` | preserve where available |

## Identifier strategy

The first implementation uses a deterministic SHA-256 event key based on the semantic observation identity:

`source_name + raw time_start + raw time_end + model + launch_place + target + carrier`

Mutable outcome/count fields are intentionally excluded so corrections in a newer snapshot update the same canonical observation instead of automatically creating a second event.

`source_record_id` is a separate SHA-256 hash of the complete source row and therefore changes when the source record itself changes.

## Timezone

Canonical date-times represent timezone-aware instants even though SQLite stores them as text. Date-only source observations remain dates and do not imply midnight.

Current primary-source handling:

- source date-time without timezone: interpret as `Europe/Kyiv`;
- Python/pandas: convert full timestamps to UTC;
- SQLite: persist full timestamps as ISO 8601 UTC strings ending in `Z`;
- source date only: preserve `YYYY-MM-DD`;
- dashboard: convert full timestamps to `Europe/Kyiv` for presentation when appropriate.

This distinction prevents false temporal precision from being introduced during ETL.

## Mixed temporal precision

The primary source may mix date-only values with full date-time values. Because these have different precision, SQLite does not enforce a text-level `time_end >= time_start` constraint.

ETL validates temporal order only when both values have comparable precision:

- date + date: compare calendar dates;
- datetime + datetime: compare normalized UTC instants;
- date + datetime (or datetime + date): preserve both values and do not infer an unavailable hour.

This prevents a source date from being silently converted into a fabricated midnight timestamp.