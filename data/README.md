# Data directory

## raw/
Immutable snapshots exactly as obtained from external sources.

## processed/
Cleaned and normalized data produced by project code.

Large or frequently changing datasets are intentionally excluded from Git through `.gitignore`.

## Canonical event schema (draft)

| Field | Type | Description |
|---|---|---|
| event_id | string | Stable internal event identifier |
| event_date | date | Event date |
| event_time | time/null | Event time if available |
| region | string | Standardized Ukrainian region |
| weapon_category | string/null | Broad category |
| weapon_type | string/null | Source-provided or normalized type |
| count | integer/null | Number of items if explicitly reported |
| status | string/null | Historical outcome/status if source provides it |
| source | string | Source name |
| source_url | string/null | Original record/page URL |
| latitude | float/null | Approximate/source-provided latitude |
| longitude | float/null | Approximate/source-provided longitude |
| notes | string/null | Non-structured source notes |

This schema is provisional and will be finalized after inspecting the first real dataset.
