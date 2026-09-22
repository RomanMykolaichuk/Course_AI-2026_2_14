# System Architecture

## Goal

Create a reproducible educational analytics pipeline for retrospective analysis of historical/open air-strike data.

The production path of the demo is:

\`\`\`text
sources → snapshots → canonical SQLite → analytics → API → dashboard
                                      ↘ historical ML evaluation
\`\`\`

The project intentionally does not expose a live/current strike-prediction API.

## Logical layers

1. **Public/open data sources**
2. **Acquisition and immutable snapshots**
3. **Source-specific parsing**
4. **Canonical transformation**
5. **SQLite relational storage**
6. **SQL analytics**
7. **GIS enrichment**
8. **Leakage-safe feature engineering**
9. **Offline historical backtesting**
10. **Retrospective evaluation registry**
11. **FastAPI**
12. **HTML/JS dashboard**

## Data flow

\`\`\`text
Primary historical source
        ↓
src/ingestion/acquire_primary.py
        ↓
data/raw/
        ↓
src/preprocessing/primary_dataset.py
        ↓
canonical CSV
        ↓
SQLite: data/airstrikes.db
        │
        ├────────────→ SQL analytics ──────→ FastAPI ──────→ dashboard
        │
        ├────────────→ feature engineering
        │                    ↓
        │           chronological split
        │                    ↓
        │           offline historical backtest
        │                    ↓
        │             model_evaluations
        │                    ↓
        └────────────────→ read-only API ──→ ML metrics panel

geoBoundaries metadata/GeoJSON
        ↓
data/external/
        ↓
canonical ADM1 mapping
        ↓
region GeoJSON endpoint
        ↓
Leaflet map
\`\`\`

## SQLite-first runtime

SQLite is used because the course/demo should run locally without a database server.

Generated database:

\`\`\`text
data/airstrikes.db
\`\`\`

The DB is a generated artifact and is excluded from Git. It must remain reproducible from source snapshots and code.

All Python code obtains connections through:

\`\`\`text
src/db/connection.py
\`\`\`

Each connection enables:

\`\`\`sql
PRAGMA foreign_keys = ON;
\`\`\`

## Core relational model

\`\`\`text
attack_events
      │
      ├──< attack_event_regions >── regions
      │
      ├── optional alert_intervals
      └── optional weather_observations

dataset_builds
      └── source/build provenance

model_evaluations
      └── retrospective metrics/provenance only
\`\`\`

### Why geography is separate

One source observation may mention one oblast, several oblasts, a broad direction, all of Ukraine, or no resolvable oblast. Region attribution is therefore modeled as a many-to-many relationship rather than forcing one region into each event.

## GIS architecture

Versioned geoBoundaries UKR ADM1 geometry is stored outside SQLite as GeoJSON.

The canonical mapping rule is:

1. use \`shapeISO\`;
2. use normalized source name only as a fallback;
3. fail the GIS smoke test when a feature is unmapped or duplicated.

The API merges ADM1 geometry with canonical evidence-only region statistics. A region without canonical evidence is rendered as **no evidence**, not as zero events.

## ML architecture

Machine-learning features are derived from canonical historical tables, never directly from raw CSV, dashboard state, or mutable API responses.

Target-day outcome/count columns are excluded from predictors. Activity predictors are lagged or rolling statistics computed strictly from dates before the target date.

Splits are chronological and never shuffled:

\`\`\`text
train → validation → test
\`\`\`

Current quality gates block:

- oblast-level training because current regional evidence is incomplete and medium-confidence only;
- national binary daily classification because validation becomes single-class.

The current allowed experiment uses \`source_event_count\` only for offline historical regression backtesting.

## Evaluation registry

\`model_evaluations\` stores:

- source build;
- task/target;
- validation metrics;
- test metrics;
- comparison metadata;
- deployment gate;
- explanatory notes.

It does **not** store a model binary/blob, pickle/joblib artifact, or future-date prediction output.

The dashboard reads only these recorded retrospective metrics.

## API boundary

The API exposes health/database diagnostics, retrospective summaries, historical daily data, category/model summaries, evidence-only regional statistics, GeoJSON and the latest retrospective model evaluation.

No public endpoint accepts a future date or region and returns a strike forecast.

## Dashboard boundary

The dashboard is descriptive/diagnostic:

- KPI;
- daily history;
- weapon categories/models;
- data-quality coverage;
- evidence-only regional map;
- provenance;
- retrospective ML metrics;
- deployment gate status.

## Reproducibility

A meaningful result must be traceable to source URL, source snapshot, acquisition time, SHA-256, code commit, transformation version, dataset build ID, and evaluation ID where ML metrics are involved.

## One-command demo orchestration

The complete local build is orchestrated by:

\`\`\`bash
python -m src.demo.build_demo
\`\`\`

This command acquires or reuses the primary snapshot, builds canonical SQLite, acquires/version-controls ADM1 geometry, records GIS provenance, runs/records retrospective evaluation metrics, and performs a final integrity check.

It does not start Uvicorn automatically.

Serve separately:

\`\`\`bash
uvicorn api.main:app --reload
\`\`\`

## Design rules summary

1. Raw snapshots are immutable.
2. Dashboard never reads raw source formats.
3. SQLite is generated, not the source of truth.
4. Missing geography is not converted into zero.
5. Missing numeric source values are not converted into zero unless zero is explicit.
6. Target-day outcomes are excluded from ML predictors.
7. Chronological evaluation is mandatory.
8. Failed quality gates block model deployment.
9. Only retrospective metrics are exposed to the dashboard.
10. No live operational forecasting surface is implemented.
