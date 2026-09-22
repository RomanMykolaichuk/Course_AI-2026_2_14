# System Architecture

## Goal

Create a reproducible educational analytics pipeline that separates data acquisition, transformation, storage, analytics, machine learning, API delivery, and visualization.

## Logical layers

1. **Data sources** — public historical/open data.
2. **Ingestion** — source-specific download/parsing code.
3. **Raw zone** — immutable source snapshots.
4. **Interim zone** — source-specific parsing, cleaning and normalization.
5. **Canonical processed zone** — common relational analytical model.
6. **Reference/external zone** — boundaries and other supporting datasets.
7. **Storage** — PostgreSQL for structured queries.
8. **Analytics** — descriptive and diagnostic analysis.
9. **ML** — baseline and interpretable prediction experiments.
10. **FastAPI** — analytical endpoints.
11. **Web dashboard** — Leaflet map + Chart.js visualizations.

## Design rules

### 1. Dashboard isolation

The dashboard must not depend directly on raw source formats. Every source must first be normalized into the canonical data model.

### 2. Source isolation

Source-specific assumptions belong in `src/ingestion/` and `src/preprocessing/`, not in API or dashboard code.

### 3. Canonical geography

An attack observation can relate to zero, one or many oblasts. Region attribution is stored separately from the attack event rather than forcing one `region` value into each record.

### 4. Reproducibility

Every processed dataset must be traceable to:

- raw snapshot(s);
- source/version;
- code commit;
- transformation rules;
- processed build manifest.

### 5. ML isolation

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
                                      PostgreSQL
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

## Canonical storage model

Core relational entities:

```text
attack_events
      │
      ├──< attack_event_regions >── regions
      │
      ├── optional alert_intervals
      └── optional weather_observations
```

Why this matters: the primary attack dataset can contain broad, multi-region or nationwide target descriptions. A many-to-many event/region model avoids inventing false geographic precision.

See:

- [Data Sources](data_sources.md)
- [Data Dictionary](data_dictionary.md)
- [Data Governance](data_governance.md)

## Initial implementation order

1. acquire a versioned snapshot of the primary Kaggle dataset;
2. build source-specific parser;
3. normalize weapon/model fields;
4. preserve raw target text;
5. extract/validate region relations into a separate link table;
6. load canonical tables into PostgreSQL;
7. perform EDA;
8. generate leakage-safe ML features;
9. expose analytics through FastAPI;
10. connect the dashboard only to normalized API outputs.
