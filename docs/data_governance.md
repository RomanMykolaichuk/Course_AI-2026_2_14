# Data Governance and Reproducibility

This project uses public/open historical data for education and research. Every analytical result must be traceable to a source snapshot and a reproducible transformation.

## 1. Data zones

### `data/raw/`

Immutable source snapshots exactly as acquired.

Rules:

- never edit files in place;
- keep original filenames where practical;
- add acquisition date/version to the directory or filename;
- preserve source-specific structure;
- do not commit large or frequently changing raw files to Git.

### `data/interim/`

Source-specific cleaned/parsing outputs.

Examples:

- parsed timestamps;
- normalized column names;
- weapon-name normalization;
- extracted region mentions;
- deduplicated source rows.

Interim data may still retain source-specific semantics.

### `data/processed/`

Canonical analytical datasets used by notebooks, PostgreSQL loading, API endpoints, and ML experiments.

Only code-generated outputs belong here.

### `data/external/`

Stable reference/enrichment files that are not primary attack observations.

Examples:

- geoBoundaries ADM1 geometry;
- weapon reference tables;
- small lookup tables;
- curated region dictionaries.

Large ERA5 extracts should normally be stored outside Git and regenerated/downloaded from documented scripts.

## 2. Snapshot naming

Recommended pattern:

`<source>_<dataset>_<YYYY-MM-DD>[_vVERSION].<ext>`

Examples:

- `kaggle_piterfm_missile_attacks_daily_2026-09-22.csv`
- `geoboundaries_UKR_ADM1_2026-09-22.geojson`

For API collections with multiple pages, use a snapshot directory:

`data/raw/<source>/<YYYY-MM-DDTHHMMSSZ>/`

## 3. Metadata sidecar

Every raw snapshot used in a published experiment should have metadata that records:

- source name;
- source URL;
- acquisition timestamp;
- source version/release where available;
- license/terms URL;
- acquisition method/script;
- SHA-256 checksum;
- row count / file size;
- notes about filters applied during acquisition.

Recommended filename:

`<data-file>.meta.json`

Example:

```json
{
  "source_name": "Massive Missile Attacks on Ukraine",
  "source_url": "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine",
  "acquired_at": "2026-09-22T00:00:00Z",
  "license": "CC BY-NC-SA 4.0",
  "sha256": "<checksum>",
  "rows": 0,
  "acquisition": "kagglehub or manual Kaggle export"
}
```

## 4. Provenance columns

Canonical records should retain, at minimum:

- `source_name`;
- `source_url` where available;
- `source_record_id` where available;
- `source_snapshot`;
- `ingested_at`.

Derived ML tables should also record a dataset build/version identifier.

## 5. Dataset versioning

A model result is not reproducible unless the exact input dataset can be identified.

Each processed dataset build should therefore have:

- build timestamp;
- code commit SHA;
- input snapshot checksums;
- transformation version;
- row counts;
- feature schema version.

A simple first implementation can write these values to:

`data/processed/manifest.json`

## 6. License and redistribution rules

Before committing or publishing external data:

1. check the source license/terms;
2. distinguish permission to **use** data from permission to **redistribute raw data**;
3. keep restricted raw datasets out of Git;
4. preserve required attribution;
5. document share-alike/non-commercial requirements for derived public artifacts.

Specific current notes:

- Kaggle “Massive Missile Attacks on Ukraine”: CC BY-NC-SA 4.0;
- geoBoundaries `gbOpen`: CC BY 4.0;
- ERA5 single-level hourly data: CC-BY with attribution requirements;
- ACLED: follow ACLED EULA/content-usage terms; do not publish raw licensed content from this repository unless explicitly permitted;
- Meteostat: preserve provider-specific license metadata.

## 7. Credentials

API keys/tokens must never be committed.

Use `.env` locally and keep only variable names/examples in `.env.example`.

Examples:

- alert API tokens;
- database credentials;
- future Kaggle/API credentials.

## 8. Data quality checks

At minimum, every processed build should test:

- required columns exist;
- timestamps parse successfully;
- `time_end >= time_start` where both exist;
- count fields are non-negative;
- null is not silently converted to zero;
- duplicate source records are identified;
- region mappings use only the canonical region table;
- source rows with ambiguous target geography remain flagged rather than force-mapped;
- no future information is introduced into ML features.

## 9. Research/operational boundary

The project is designed for retrospective analysis and educational ML demonstrations.

It must not present model output as:

- prediction of an exact future strike target;
- prediction of a route;
- real-time operational warning;
- replacement for official alert systems.

The initial ML output should remain aggregated by region and time bucket and should be presented with validation metrics and uncertainty/limitations.

## 10. Review checklist before a model is trained

- [ ] Exact source snapshots are identified.
- [ ] Licenses/terms are documented.
- [ ] Canonical mapping is reproducible.
- [ ] Ambiguous geography is flagged.
- [ ] Train/validation/test split is chronological where appropriate.
- [ ] Feature calculation uses only past information.
- [ ] Class imbalance is reported.
- [ ] A naive baseline is included.
- [ ] Model/data version is recorded.
- [ ] Dashboard wording clearly labels output as an experimental historical-data model.
