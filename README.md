# Ukraine Air Strike Historical Analytics Dashboard

Навчальний проєкт інформаційно-аналітичної системи для **ретроспективного аналізу відкритих історичних даних** про повітряні атаки по території України.

Проєкт показує повний цикл роботи з даними:

\`\`\`text
Open Data
   ↓
Acquisition + provenance
   ↓
ETL / canonical model
   ↓
SQLite
   ↓
SQL analytics
   ↓
FastAPI
   ↓
Chart.js + Leaflet dashboard
   ↓
Offline historical ML backtest
\`\`\`

> ML-модуль використовується лише для історичного backtesting. Репозиторій не містить live/current endpoint для прогнозування майбутніх ударів, цілей, маршрутів або конкретних регіонів.

## 1. Поточний статус

На 22 вересня 2026 року реалізовано повний демонстраційний MVP:

- SQLite-first runtime;
- автоматичне завантаження primary dataset;
- source snapshots + SHA-256 + metadata;
- canonical relational model;
- SQL-аналітика;
- FastAPI;
- інтерактивний dashboard;
- Chart.js timeline/categories;
- Leaflet ADM1 map;
- data-quality / attribution coverage;
- leakage-safe ML feature engineering;
- chronological train/validation/test split;
- ML quality gates;
- offline regression backtest;
- registry retrospective model evaluations;
- one-command demo build;
- unit tests + GitHub Actions smoke tests.

## 2. Real-data baseline

Актуальний primary build у CI:

\`\`\`text
source rows                  4152
canonical events             4146
region links                 1114
events with region evidence   994
region-link coverage        23.97%
period                  2022-09-28 — 2026-09-18
\`\`\`

Важливо: current snapshot не містить поля \`affected_region\`, хоча воно описане в Data Card джерела. Тому поточні region links формуються лише з явних адміністративних згадок у \`target\`.

Це означає:

- high-confidence region events: **0**;
- medium-confidence region events: **994**;
- відсутність region link **не означає відсутність події** у відповідному регіоні.

## 3. GIS baseline

Використовується versioned geoBoundaries \`gbOpen\` UKR ADM1 snapshot:

\`\`\`text
boundary ID          UKR-ADM1-14850775
boundary year        2017
ADM1 features        27
canonical mappings   27/27
duplicates           0
geometry             simplified GeoJSON
\`\`\`

Mapping виконується пріоритетно через \`shapeISO\`, а назва використовується лише як fallback.

Поточна layer-specific license metadata зберігається разом зі snapshot; для цього UKR ADM1 шару API повідомляє **ODbL 1.0**.

## 4. ML quality gate

### 4.1 Початкова oblast-level задача

Початкова ідея:

\`\`\`text
region_code × time_bucket → binary event label
\`\`\`

на поточних даних **заблокована**:

\`\`\`text
region-link coverage              23.97%
high-confidence region events         0
medium-confidence region events     994
status      BLOCKED_MEDIUM_CONFIDENCE_ONLY
\`\`\`

### 4.2 National daily binary label

Побудовано complete daily calendar:

\`\`\`text
calendar rows                 1452
period        2022-09-28 — 2026-09-18
positive source days          1218
negative source days           234
positive rate              83.8843%
model-ready start        2022-10-05
\`\`\`

Chronological split:

\`\`\`text
train       2022-10-05 — 2025-07-11   1011 rows   positive 77.3492%
validation  2025-07-12 — 2026-02-12    216 rows   positive 100.0000%
test        2026-02-13 — 2026-09-18    218 rows   positive 99.0826%
\`\`\`

Validation має лише один клас, тому binary classification evaluation заблокований:

\`\`\`text
BLOCKED_SINGLE_CLASS_EVALUATION
\`\`\`

### 4.3 Допустимий retrospective target

Для offline historical experiment використовується:

\`\`\`text
source_event_count
\`\`\`

Це **кількість canonical source rows за вже відому історичну календарну дату**, а не оцінка повної кількості реальних атак.

У validation/test цей target зберігає достатню варіативність для regression backtest.

## 5. Offline historical ML backtest

Порівнюються:

- \`naive_lag1\`;
- \`DummyRegressor(strategy="median")\`;
- fixed \`RandomForestRegressor\`.

### Validation

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| naive_lag1 | 1.583 | 2.126 | -0.941 |
| dummy_median | 1.528 | 2.057 | -0.818 |
| random_forest_fixed | **1.237** | **1.589** | **-0.085** |

### Test

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| naive_lag1 | 1.541 | 2.048 | -0.849 |
| dummy_median | 1.518 | 2.100 | -0.945 |
| random_forest_fixed | **1.385** | **1.660** | **-0.215** |

Random Forest має найменші MAE/RMSE, але **test R² залишається від'ємним**.

Тому deployment gate:

\`\`\`text
blocked_research_only
\`\`\`

Жодний fitted model не серіалізується і не публікується як inference artifact.

## 6. Технологічний стек

- Python 3.12;
- SQLite / \`sqlite3\`;
- pandas / NumPy;
- scikit-learn;
- FastAPI / Uvicorn;
- HTML / CSS / JavaScript;
- Chart.js;
- Leaflet;
- KaggleHub;
- GitHub Actions.

## 7. Canonical data model

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
      └── retrospective metrics only
          no fitted model artifact
\`\`\`

Ключові правила:

- raw data не редагується вручну;
- \`null\` не перетворюється на \`0\` без доказів;
- structured source values зберігаються окремо, якщо з них виводиться scalar;
- географічна невизначеність не замінюється вигаданою точністю;
- ML predictors використовують лише минулі значення;
- current-day outcomes не потрапляють у predictors;
- model evaluation не означає deployment approval.

## 8. Структура репозиторію

\`\`\`text
.
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── external/
│   └── airstrikes.db        # generated, gitignored
├── src/
│   ├── db/
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   ├── check_db.py
│   │   ├── load_primary.py
│   │   ├── load_boundaries.py
│   │   ├── map_data.py
│   │   └── queries.py
│   ├── ingestion/
│   │   ├── acquire_primary.py
│   │   └── acquire_boundaries.py
│   ├── preprocessing/
│   │   ├── primary_dataset.py
│   │   ├── boundaries.py
│   │   └── regions.py
│   ├── features/
│   │   ├── national_daily.py
│   │   ├── split.py
│   │   ├── quality_gate.py
│   │   └── target_diagnostics.py
│   ├── models/
│   │   ├── historical_count_backtest.py
│   │   └── record_evaluation.py
│   └── demo/
│       └── build_demo.py
├── api/
│   └── main.py
├── web/
│   ├── index.html
│   ├── css/
│   └── js/
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── tests/
└── docs/
\`\`\`

## 9. Найпростіший запуск

### Ubuntu / Linux

\`\`\`bash
git clone https://github.com/RomanMykolaichuk/Course_AI-2026_2_14.git
cd Course_AI-2026_2_14

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
\`\`\`

Побудувати весь локальний demo dataset + SQLite + GIS + retrospective ML evaluation:

\`\`\`bash
python -m src.demo.build_demo
\`\`\`

Після успішного build:

\`\`\`bash
uvicorn api.main:app --reload
\`\`\`

Відкрити:

\`\`\`text
http://127.0.0.1:8000/
\`\`\`

Повторний запуск builder без \`--force-downloads\` використовує вже наявний primary snapshot.

Якщо primary CSV були завантажені вручну:

\`\`\`bash
python -m src.demo.build_demo \
  --primary-from-dir /path/to/downloaded/dataset
\`\`\`

## 10. Ручний pipeline

Primary dataset:

\`\`\`bash
python -m src.ingestion.acquire_primary
python -m src.db.load_primary
\`\`\`

GIS:

\`\`\`bash
python -m src.ingestion.acquire_boundaries
python -m src.db.load_boundaries
\`\`\`

ML audit:

\`\`\`bash
python -m src.features.national_daily
python -m src.features.split
python -m src.features.target_diagnostics
python -m src.features.quality_gate
python -m src.models.historical_count_backtest
python -m src.models.record_evaluation
\`\`\`

Database integrity:

\`\`\`bash
python -m src.db.check_db
\`\`\`

## 11. API

\`\`\`text
GET /api/health
GET /api/db/summary
GET /api/build/latest
GET /api/stats/overview
GET /api/stats/daily
GET /api/stats/categories
GET /api/stats/models
GET /api/stats/regions
GET /api/stats/attribution
GET /api/map/regions
GET /api/ml/evaluation/latest
\`\`\`

\`/api/ml/evaluation/latest\` повертає лише вже записані retrospective metrics. Endpoint для future/live prediction відсутній.

## 12. Dashboard

Поточний web dashboard містить:

- SQLite/API status;
- KPI;
- historical daily timeline;
- weapon categories;
- data-quality / region coverage;
- model table;
- evidence-only region table;
- interactive ADM1 Leaflet map;
- GIS provenance;
- retrospective ML evaluation;
- deployment gate status;
- data build provenance.

На карті:

- кольоровий регіон = є canonical region evidence;
- сірий регіон = **немає достатньої географічної розмітки**;
- сірий колір не означає \`0 attacks\`.

## 13. План реалізації

### Sprint 1 — SQLite foundation
- [x] complete

### Sprint 2 — Primary dataset → SQLite
- [x] complete

### Sprint 3 — SQL analytics
- [x] complete

### Sprint 4 — FastAPI + first dashboard
- [x] complete

### Sprint 5 — Regional map
- [x] complete

### Sprint 6 — ML feature engineering + quality gate
- [x] complete

### Sprint 7 — Offline historical ML backtest
- [x] alternative aggregate target diagnostics;
- [x] naive baseline;
- [x] Dummy baseline;
- [x] fixed Random Forest;
- [x] chronological evaluation;
- [x] deployment quality gate;
- [x] no fitted model persistence;
- [x] real-data CI backtest.

### Sprint 8 — ML evaluation in dashboard
- [x] \`model_evaluations\` registry;
- [x] metrics/provenance persistence;
- [x] read-only API endpoint;
- [x] dashboard ML panel;
- [x] explicit \`blocked_research_only\` state;
- [x] no live inference.

### Demo Sprint
- [x] one-command demo builder;
- [x] final SQLite integrity check;
- [x] GitHub Actions unit tests;
- [x] real-data smoke pipeline.

## 14. Testing

Unit/CI:

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

GitHub Actions:

- **Tests** — schema, ETL, analytics, GIS, feature engineering, quality gates, models, API surface, demo orchestration;
- **Primary Data Smoke** — current public primary data → SQLite → analytics → features → diagnostics → backtest → evaluation registry;
- **GIS Smoke** — live geoBoundaries metadata/GeoJSON → 27/27 canonical mapping.

Raw datasets and generated DB are not uploaded to the repository.

## 15. Data sources

Primary:

- Kaggle: **Massive Missile Attacks on Ukraine**.

GIS:

- geoBoundaries \`gbOpen\`, UKR ADM1.

Planned/optional enrichment:

- ERA5 historical weather;
- historical alert archives where reproducibility and licensing permit;
- ACLED/UCDP for independent historical validation subject to their usage terms.

See [docs/data_sources.md](docs/data_sources.md).

## 16. Research and operational boundary

The project is designed for:

- historical analytics;
- data engineering education;
- SQL/FastAPI/dashboard practice;
- GIS visualization;
- leakage-safe feature engineering;
- retrospective ML methodology;
- model evaluation and limitations.

The project does **not** provide:

- live operational warning;
- prediction of an exact future target;
- prediction of strike route;
- live oblast forecast;
- future-date public inference endpoint;
- replacement for official alert systems.

## 17. Current conclusion

The project successfully demonstrates the end-to-end analytical workflow.

The most important ML result is not “Random Forest predicts well”, but the opposite methodological lesson:

> a model may improve MAE/RMSE against simple baselines and still fail a meaningful out-of-sample quality gate.

Because test R² remains negative, the current model is retained as a **research/teaching backtest only**.

The next useful development should focus on **better historical data quality and target formulation**, not on deploying increasingly complex models.
