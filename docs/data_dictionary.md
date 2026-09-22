# Data Dictionary

This document defines the canonical analytical model used by the project.

The primary source is not a simple “one row = one strike location” dataset. A single row can describe an attack interval for one weapon model and can contain a broad or multi-region target description. For that reason, the canonical model is relational rather than forcing every source row into one oblast.

## Core entities

### 1. attack_events

One row represents one normalized source observation for a specific attack interval and weapon model.

| Field | Type | Required | Description |
|---|---|---:|---|
| event_id | text | yes | Stable internal identifier |
| time_start | timestamptz | yes | Start of the reported attack interval |
| time_end | timestamptz | no | End of the reported attack interval |
| weapon_model | text | no | Normalized missile/UAV model |
| weapon_category | text | no | Broad category such as UAV, cruise missile, ballistic missile |
| launch_place | text | no | Source-provided launch location or area |
| target_raw | text | no | Target description exactly/semantically preserved from the source |
| carrier | text | no | Launch platform/carrier |
| launched | integer | no | Number launched; null means unknown, not zero |
| destroyed | integer | no | Number destroyed; null means unknown |
| not_reach_goal | integer | no | Number reported as not reaching the target |
| border_crossing | integer | no | Number reported as crossing out of Ukraine |
| still_attacking | integer | no | Number still attacking at report time |
| source_name | text | yes | Dataset/source identifier |
| source_url | text | no | URL of original source record/page where available |
| source_record_id | text | no | Stable source-side identifier when available |
| source_snapshot | text | yes | Snapshot/version filename or acquisition ID |
| ingested_at | timestamptz | yes | ETL ingestion timestamp |

### 2. regions

Canonical oblast/reference table.

| Field | Type | Required | Description |
|---|---|---:|---|
| region_code | text | yes | Stable internal region code |
| name_uk | text | yes | Ukrainian region name |
| name_en | text | no | English region name |
| boundary_source | text | no | GIS boundary source |
| boundary_version | text | no | Release/version of boundary data |

### 3. attack_event_regions

Many-to-many link between attack observations and regions.

| Field | Type | Required | Description |
|---|---|---:|---|
| event_id | text | yes | FK to `attack_events` |
| region_code | text | yes | FK to `regions` |
| relation_type | text | yes | `target`, `destroyed_location`, `mentioned`, or another documented relation |
| attribution_method | text | yes | `source_explicit`, `parsed`, `manual_review`, etc. |
| attribution_quality | text | no | Optional quality flag such as `high`, `medium`, `low` |

This table prevents a multi-oblast target string from being incorrectly collapsed into one region.

### 4. alert_intervals

Optional historical alert layer.

| Field | Type | Required | Description |
|---|---|---:|---|
| alert_id | text | yes | Stable alert identifier |
| region_code | text | yes | Canonical region code |
| alert_type | text | yes | Alert/threat type |
| started_at | timestamptz | yes | Start time |
| finished_at | timestamptz | no | End time |
| source_name | text | yes | Alert source/API |
| source_snapshot | text | yes | Snapshot/version |

### 5. weather_observations

Optional environmental enrichment table.

| Field | Type | Required | Description |
|---|---|---:|---|
| observed_at | timestamptz | yes | Historical weather timestamp |
| region_code | text | yes | Region to which the feature is aggregated |
| temperature_c | double precision | no | Temperature |
| wind_speed_ms | double precision | no | Wind speed |
| wind_direction_deg | double precision | no | Wind direction |
| precipitation_mm | double precision | no | Precipitation |
| cloud_cover_pct | double precision | no | Cloud cover |
| surface_pressure_hpa | double precision | no | Surface pressure |
| source_name | text | yes | e.g. ERA5 |
| aggregation_method | text | yes | Spatial aggregation rule |

## ML feature table

The model should train from a derived table produced from the canonical entities, not directly from raw CSV.

Suggested grain for the first experiment:

`region_code × time_bucket`

Example derived fields:

| Field | Meaning |
|---|---|
| bucket_start | Start of the prediction interval |
| region_code | Canonical oblast |
| event_present | Target label: whether a normalized historical event is associated with the region/time bucket |
| event_count_prev_24h | Number of events in previous 24 h |
| event_count_prev_7d | Number of events in previous 7 d |
| rolling_mean_7d | Historical rolling mean |
| rolling_mean_30d | Historical rolling mean |
| days_since_previous_event | Time since previous event |
| uav_activity_prev_7d | Historical UAV activity |
| missile_activity_prev_7d | Historical missile activity |
| alert_duration_prev_24h | Optional alert-history feature |
| weather_* | Optional lagged/aggregated weather features |
| day_of_week | Calendar feature |
| month | Calendar feature |

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
| `time_start` | `time_start` | parse to timezone-aware timestamp |
| `time_end` | `time_end` | parse when present |
| `model` | `weapon_model` | normalize via weapon reference table |
| model reference category | `weapon_category` | join from `missiles_and_uavs.csv` |
| `launch_place` | `launch_place` | preserve source text |
| `target` | `target_raw` | preserve; parse regions separately |
| `carrier` | `carrier` | preserve/normalize |
| `launched` | `launched` | integer/null; never replace null with zero |
| `destroyed` | `destroyed` | integer/null |
| `not_reach_goal` | `not_reach_goal` | integer/null |
| `border_crossing` | `border_crossing` | integer/null |
| `still_attacking` | `still_attacking` | integer/null |
| source field/page | `source_url` | preserve where available |

## Identifier strategy

A deterministic event identifier should be generated from stable normalized source fields, for example:

`sha256(source_name + time_start + model + launch_place + target_raw + source_record_id)`

The exact implementation must be fixed before the first processed dataset is published.

## Timezone

All stored timestamps should be timezone-aware.

Recommended storage:

- PostgreSQL: `TIMESTAMPTZ`;
- Python/pandas: UTC internally;
- dashboard: convert to `Europe/Kyiv` for presentation when appropriate.

The source timezone assumption must be documented during ingestion rather than guessed downstream.
