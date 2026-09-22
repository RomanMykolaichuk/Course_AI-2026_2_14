# System Architecture

## Goal

Create a reproducible educational analytics pipeline that separates data acquisition, transformation, local relational storage, analytics, machine learning, API delivery, and visualization.

## Logical layers

1. **Data sources** — public historical/open data.
2. **Ingestion** — source-specific download/parsing code.
3. **Raw zone** — immutable source snapshots.
4. **Interim zone** — source-specific parsing, cleaning and normalization.
5. **Canonical processed zone** — common relational analytical model.
6. **Reference/external zone** — boundaries and other supporting datasets.
7. **Storage** — SQLite local relational database.
8. **Analytics** — descriptive and diagnostic analysis.
9. **ML** — baseline and interpretable prediction experiments.
10. **FastAPI** — analytical endpoints.
11. **Web dashboard** — Leaflet map + Chart.js visualizations.

## Why SQLite for the course

SQLite keeps the runtime simple and portable:

- no separate database server;
- no database users, ports or service configuration;
- Python includes the `sqlite3` driver in the standard library;
- the whole relational store is one local file;
- SQL remains explicit and visible to learners;
- the database can later be migrated to PostgreSQL if scale or concurrency requirements change.

The generated database is stored locally as:

```text
data/airstrikes.db
```

and is excluded from Git. It must always be reproducible from documented source snapshots and transformation code.

## Design rules

### 1. Dashboard isolation

The dashboard must not depend directly on raw source formats. Every source must first be normalized into the canonical data model.

### 2. Source isolation

Source-specific assumptions belong in `src/ingestion/` and `src/preprocessing/`, not in API or dashboard code.

### 3. Canonical geography

An attack observation can relate to zero, one or many oblasts. Region attribution is stored separately from the attack event rather than forcing one `region` value into each record.

### 4. Reproducibility

Every processed dataset/database build must be traceable to:

- raw snapshot(s);
- source/version;
- checksum;
- code commit;
- transformation rules;
- processed build manifest / `dataset_builds` record.

### 5. Database isolation

All Python code should obtain SQLite connections through `src/db/connection.py`. Notebooks, API code, ingestion code and ML code should not independently hard-code database paths.

### 6. ML isolation

Machine-learning features are derived from canonical historical tables. Models must not train directly from mutable API responses or current dashboard state.

## Data flow

```text
                            ┌──────────────────────────┐
                            │ Public/open data sources │
                            └─────────────┬────────────┘
                                          │
                                          ▼
                                  src/ingestion/
                                          │
                                          ▼
                                      data/raw/
                                          │
                                          ▼
                               src/preprocessing/
                                          │
                                          ▼
                                   data/interim/
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
             canonical transformation                  data/external/
                     │                              boundaries/lookups
                     └────────────────────┬────────────────────┘
                                          ▼
                                  data/processed/
                                          │
                                          ▼
                               SQLite: data/airstrikes.db
                                   ┌──────┴──────┐
                                   ▼             ▼
                              analytics         ML
                                   └──────┬──────┘
                                          ▼
                                       FastAPI
                                          ▼
                                  REST/JSON endpoints
                                          ▼
                               HTML + CSS + JavaScript
                                          ▼
                               Leaflet + Chart.js
```

## SQLite storage conventions

- enable `PRAGMA foreign_keys = ON` for every connection;
- store canonical timestamps as ISO 8601 text, normalized to UTC by ETL code;
- use `REAL` for floating-point measurements;
- use `INTEGER` for counts and booleans where applicable;
- do not store large raw source files or GIS binaries inside SQLite;
- treat `data/airstrikes.db` as generated runtime state, not as a source artifact.

## Canonical storage model

Core relational entities:

```text
attack_events
      │
      ├──< attack_event_regions >── regions
      │
      ├── optional alert_intervals
      └── optional weather_observations

dataset_builds
      └── provenance/version records for database builds
```

Why this matters: the primary attack dataset can contain broad, multi-region or nationwide target descriptions. A many-to-many event/region model avoids inventing false geographic precision.

See:

- [Data Sources](data_sources.md)
- [Data Dictionary](data_dictionary.md)
- [Data Governance](data_governance.md)

## Local runtime

Initialize the database:

```bash
python -m src.db.init_db
```

Verify it:

```bash
python -m src.db.check_db
```

The database path defaults to `data/airstrikes.db` and can be overridden with the `DATABASE_PATH` environment variable.

## Initial implementation order

1. initialize and verify the SQLite schema;
2. acquire a versioned snapshot of the primary Kaggle dataset;
3. build source-specific parser;
4. normalize weapon/model fields;
5. preserve raw target text;
6. extract/validate region relations into a separate link table;
7. load canonical tables into SQLite;
8. perform EDA and SQL analytics;
9. expose one analytical endpoint through FastAPI;
10. render the first Chart.js visualization;
11. generate leakage-safe ML features;
12. add baseline models and later enrichments.
