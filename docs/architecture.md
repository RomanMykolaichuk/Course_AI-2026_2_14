# System Architecture

## Goal

Create a reproducible educational analytics pipeline that separates data acquisition, transformation, storage, analytics, machine learning, API delivery, and visualization.

## Logical layers

1. **Data sources** — public historical/open data.
2. **Ingestion** — source-specific download/parsing code.
3. **Raw zone** — immutable source snapshots.
4. **Preprocessing** — cleaning, normalization, deduplication.
5. **Processed zone** — canonical analytical dataset.
6. **Storage** — PostgreSQL for structured queries.
7. **Analytics** — descriptive and diagnostic analysis.
8. **ML** — baseline and interpretable prediction experiments.
9. **FastAPI** — analytical endpoints.
10. **Web dashboard** — Leaflet map + Chart.js visualizations.

## Design rule

The dashboard must not depend directly on raw source formats. Every source is converted into the canonical schema first.

## Initial data flow

```text
Source
  ↓
src/ingestion
  ↓
data/raw
  ↓
src/preprocessing
  ↓
data/processed
  ↓
PostgreSQL / pandas
  ↓
analytics + ML
  ↓
FastAPI
  ↓
dashboard
```
