# Ukraine Air Strike Analytics & Forecasting Dashboard

Навчальний проєкт з побудови інформаційно-аналітичної системи для аналізу історичних відкритих даних про повітряні атаки по території України та демонстрації методів машинного навчання для прогнозної аналітики.

## 1. Мета проєкту

Побудувати наскрізну навчальну систему:

```text
Open Data → ETL → SQLite → Analytics → Machine Learning → API → Dashboard
```

Система має показати повний життєвий цикл даних: від отримання сирих відкритих даних до локальної реляційної БД, інтерактивної візуалізації, статистичного аналізу та демонстраційного ML-прогнозування.

> Проєкт має навчальний та дослідницький характер. Прогнозний модуль не призначений для оперативного застосування або прогнозування конкретних цілей, маршрутів чи точного місця майбутніх ударів.

## 2. Технологічний стек

Початковий runtime навмисно простий:

- Python;
- SQLite через стандартний модуль `sqlite3`;
- pandas / NumPy;
- scikit-learn;
- FastAPI;
- HTML + CSS + JavaScript;
- Chart.js;
- Leaflet.

SQLite використовується замість окремого серверного СУБД, щоб проєкт можна було локально запускати без Docker, портів, користувачів БД і окремої інсталяції сервера.

Локальна БД:

```text
data/airstrikes.db
```

Файл БД генерується локально і не комітиться в Git.

## 3. Основні функції MVP

1. Завантаження історичних даних з документованих відкритих джерел.
2. Збереження незмінних source snapshots та provenance.
3. Очищення й нормалізація даних.
4. Формування canonical relational dataset.
5. Завантаження canonical tables у SQLite.
6. Візуалізація:
   - кількість подій у часі;
   - розподіл за регіонами;
   - розподіл за категоріями повітряних засобів;
   - часові закономірності;
   - агрегована карта України.
7. Побудова baseline ML-моделі.
8. Порівняння декількох моделей класифікації.
9. Відображення результатів моделі у dashboard.

## 4. Базові джерела даних

Для MVP визначено такі ролі джерел:

- **Primary:** [Massive Missile Attacks on Ukraine](https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine) — історичні атаки, типи/моделі та кількісні показники;
- **GIS reference:** [geoBoundaries](https://www.geoboundaries.org/api.html) `gbOpen` ADM1 — межі областей;
- **Weather enrichment:** [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) — опційні історичні погодні ознаки;
- **Alert enrichment:** alerts.in.ua / Ukraine Alarm API — лише за наявності відтворюваного історичного архіву;
- **Independent validation:** ACLED та UCDP.

Детальний реєстр, ліцензії, обмеження та рішення щодо використання описані у [docs/data_sources.md](docs/data_sources.md).

## 5. ML-задача

Початкова навчальна постановка:

**оцінювання ймовірності наявності історично спостережуваної події в певному регіоні протягом наступного агрегованого часового інтервалу на основі лише попередніх історичних ознак.**

Рекомендований grain для ML-таблиці:

```text
region_code × time_bucket
```

Приклади ознак:

- day_of_week;
- month;
- previous_24h_events;
- previous_7d_events;
- rolling_mean_7d;
- rolling_mean_30d;
- days_since_previous_event;
- historical UAV activity;
- historical missile activity;
- optional lagged alert/weather features.

Початкові моделі:

- DummyClassifier;
- LogisticRegression;
- RandomForestClassifier.

Метрики:

- Precision;
- Recall;
- F1-score;
- ROC-AUC;
- PR-AUC.

Обов’язкова вимога: ознаки формуються лише з інформації, доступної **до** prediction interval.

## 6. Архітектура

```text
Public Open Data
       ↓
src/ingestion/
       ↓
data/raw/
       ↓
src/preprocessing/
       ↓
data/interim/
       ↓
canonical transformation  ←  data/external/
       ↓
data/processed/
       ↓
SQLite: data/airstrikes.db
   ↙                 ↘
Analytics             ML
   ↘                 ↙
        FastAPI
           ↓
       REST API
           ↓
HTML + CSS + JavaScript
           ↓
Leaflet + Chart.js
```

Ключове архітектурне правило: dashboard та ML не працюють безпосередньо з форматами зовнішніх джерел.

Докладніше: [docs/architecture.md](docs/architecture.md).

## 7. Структура репозиторію

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   ├── README.md
│   ├── raw/          # immutable source snapshots
│   ├── interim/      # source-specific cleaned/parsing outputs
│   ├── processed/    # canonical analytical datasets
│   ├── external/     # GIS/reference/enrichment files
│   └── airstrikes.db # generated locally, gitignored
├── notebooks/
├── src/
│   ├── db/
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   ├── check_db.py
│   │   ├── seed_regions.py
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
│   ├── models/
│   └── utils/
├── api/
├── web/
├── models/
├── sql/
│   └── schema.sql
└── docs/
    ├── architecture.md
    ├── data_sources.md
    ├── data_dictionary.md
    ├── data_governance.md
    └── methodology.md
```

## 8. Canonical data model

Початкова плоска схема `event → one region` не використовується, оскільки source row може містити кілька областей, напрямок або всю Україну.

Основна модель:

```text
attack_events
      │
      ├──< attack_event_regions >── regions
      │
      ├── optional alert_intervals
      └── optional weather_observations

dataset_builds
      └── provenance / version records
```

Тобто:

- source attack observation зберігається без втрати оригінальної семантики;
- `target_raw` зберігається окремо;
- регіональні зв’язки виділяються в many-to-many таблицю;
- неоднозначні записи не отримують вигадану географічну точність;
- кожна суттєва побудова БД може мати provenance record.

Поля та правила mapping: [docs/data_dictionary.md](docs/data_dictionary.md).

## 9. Локальний запуск БД

Створити virtual environment і встановити залежності:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ініціалізувати SQLite:

```bash
python -m src.db.init_db
```

Перевірити структуру та integrity:

```bash
python -m src.db.check_db
```

За замовчуванням використовується:

```text
data/airstrikes.db
```

Інший шлях можна задати через `DATABASE_PATH` у локальному `.env`.

### Primary dataset: acquisition → SQLite

Завантажити актуальний snapshot через офіційний KaggleHub:

```bash
python -m src.ingestion.acquire_primary
```

Якщо CSV уже завантажені вручну:

```bash
python -m src.ingestion.acquire_primary --from-dir /path/to/downloaded/dataset
```

Команда створює датований каталог у `data/raw/`, SHA-256 та metadata sidecars. Самі raw-файли не комітяться.

Перетворити останній snapshot і завантажити canonical tables у SQLite:

```bash
python -m src.db.load_primary
python -m src.db.check_db
```

Згенеровані canonical CSV та `manifest.json` зберігаються під `data/processed/primary/<snapshot-date>/` і також не комітяться.

## 10. План реалізації

### Sprint 1 — SQLite foundation
- [x] перейти від PostgreSQL до SQLite;
- [x] адаптувати `schema.sql`;
- [x] створити централізований DB connection layer;
- [x] додати DB initialization;
- [x] додати DB integrity/schema check;
- [x] додати `dataset_builds` для provenance;
- [x] синхронізувати документацію та конфігурацію.

### Sprint 2 — Primary dataset → SQLite
- [x] реалізувати acquisition через KaggleHub або локальний каталог;
- [x] автоматично створювати metadata/checksum;
- [x] реалізувати primary-source parser;
- [x] реалізувати canonical transformation;
- [x] реалізувати завантаження `attack_events`;
- [x] підтримати `affected_region` як primary region evidence, якщо поле присутнє у snapshot;
- [x] використовувати explicit oblast mentions у `target` як conservative fallback;
- [x] записувати provenance у `dataset_builds`;
- [x] додати synthetic unit tests та GitHub Actions CI;
- [x] виконати real-data acquisition/build через GitHub Actions;
- [x] зафіксувати actual CSV schema у snapshot metadata;
- [x] перевірити SQLite integrity/foreign keys на актуальному dataset.

### Sprint 3 — EDA + SQL analytics
- [x] додати reusable SQLite analytics queries;
- [x] додати overview та daily timeline;
- [x] додати category/model summaries;
- [x] додати region-attribution coverage;
- [x] додати evidence-only region summary;
- [x] додати `sql/analytics.sql` як навчальні SQL-приклади;
- [x] перевірити analytics queries на synthetic SQLite;
- [x] перевірити analytics report на актуальному real-data build.

### Sprint 4 — FastAPI + first dashboard
- [x] expose analytics endpoints через FastAPI;
- [x] додати KPI;
- [x] додати daily Chart.js timeline;
- [x] додати category chart;
- [x] додати model/region tables;
- [x] явно показати region-attribution coverage/confidence;
- [x] віддавати `web/` через той самий FastAPI application.

### Sprint 5 — Regional map
- [x] canonical region reference;
- [x] versioned geoBoundaries UKR ADM1 acquisition;
- [x] 27/27 mapping через shapeISO з name fallback;
- [x] GIS provenance у `regions.boundary_source/boundary_version`;
- [x] evidence-only GeoJSON endpoint;
- [x] Leaflet integration;
- [x] aggregated historical map;
- [x] explicit no-evidence styling instead of treating missing geography as zero;
- [x] real geoBoundaries smoke test та synthetic map-data tests.

### Sprint 6 — ML dataset + quality gate
- [x] complete national daily calendar;
- [x] label `source_event_present` з обережною source-level семантикою;
- [x] calendar features;
- [x] lag-1 / lag-7 historical activity;
- [x] prior-only rolling 7/30-day statistics;
- [x] days-since-previous-source-event;
- [x] explicit predictor allow-list;
- [x] current-day outcome/count columns виключені з ML predictors;
- [x] chronological train/validation/test split без shuffle;
- [x] leakage/unit tests;
- [x] real-data feature/split smoke;
- [x] ML quality gate для national та oblast-level задач.

### Sprint 7 — Offline historical ML backtest
- [ ] не запускати binary daily classifier, поки evaluation split не містить обидва класи;
- [ ] не навчати oblast-level classifier на поточній medium-confidence розмітці;
- [ ] обрати альтернативну агреговану retrospective target formulation;
- [ ] додати simple baseline;
- [ ] використовувати chronological backtesting;
- [ ] зберігати лише historical evaluation metrics, без live/current forecast endpoint.

### Sprint 8 — ML in dashboard
- API endpoint для експериментального агрегованого результату;
- відображення метрик;
- ML-блок з чітко позначеними обмеженнями.

## 11. Принципи роботи з даними

- використовуються лише документовані відкриті/доступні для дослідження джерела;
- сирі дані не редагуються вручну;
- усі трансформації мають бути відтворюваними;
- походження кожного набору даних документується;
- `null` не перетворюється на `0`, якщо джерело не повідомляє нуль явно;
- неоднозначна географія не перетворюється на точну координату без доказового правила;
- raw source snapshots та processed dataset builds версіонуються;
- SQLite DB є generated artifact, а не джерелом істини;
- API keys/tokens не комітяться;
- оперативно чутливі сценарії та точне прогнозування цілей не входять до цілей проєкту;
- моделі оцінюються як статистичні моделі на історичних даних, а не як система оперативного передбачення.

Правила provenance/versioning: [docs/data_governance.md](docs/data_governance.md).

## 12. Реальний baseline build — 2026-09-22

End-to-end smoke test на актуальному public Kaggle snapshot успішний:

```text
source rows                  4152
canonical events             4146
region links                 1114
events with any region       994
weapon reference rows        64
affected_region present      no
SQLite integrity_check       ok
foreign_key_check            ok
```

Build ID: `primary-8278a8d28145b9c1`.

Важливе спостереження: поточний завантажений `missile_attacks_daily.csv` не містить колонки `affected_region`, хоча вона описана у Data Card джерела. Тому для цього snapshot регіональна прив’язка формується лише з явних адміністративних згадок у `target`; це неповне покриття і його не можна трактувати як повну oblast-level розмітку.

## 13. Запуск dashboard

Після acquisition та SQLite load завантажити versioned ADM1 geometry і записати її provenance:

```bash
python -m src.ingestion.acquire_boundaries
python -m src.db.load_boundaries
```

Після цього запустити API + dashboard:

```bash
uvicorn api.main:app --reload
```

Відкрити:

```text
http://127.0.0.1:8000/
```

FastAPI віддає і API, і `web/` з одного origin. Основні endpoints:

```text
GET /api/health
GET /api/build/latest
GET /api/stats/overview
GET /api/stats/daily
GET /api/stats/categories
GET /api/stats/models
GET /api/stats/regions
GET /api/stats/attribution
GET /api/map/regions
```

Поточний dashboard показує лише ретроспективну аналітику. Показники `launched_known_total` та `destroyed_known_total` — суми відомих числових значень у джерелі, а не твердження про повноту всіх реальних запусків/знищень.

## 14. GIS baseline — 2026-09-22

Поточний geoBoundaries UKR ADM1 snapshot:

```text
boundary ID             UKR-ADM1-14850775
boundary year           2017
ADM1 features           27
canonical mappings      27/27
mapping duplicates      0
geometry variant        simplified GeoJSON
```

Карта не перетворює відсутню регіональну розмітку на нуль. Для регіонів без `attack_event_regions` UI показує стан **no region evidence**.

## 15. ML feature baseline — 2026-09-22

Побудовано national daily feature dataset для **historical backtesting only**:

```text
calendar rows                 1452
period                        2022-09-28 — 2026-09-18
positive source days          1218
negative source days           234
overall positive rate        83.8843%
model-ready start             2022-10-05
```

Фінальний ML CSV не містить target-day `event_count`, `launched`, `destroyed` або інших outcome-полів. Дозволені predictors — календарні та lag/rolling features, сформовані лише з попередніх дат.

Chronological split без shuffle:

```text
train       2022-10-05 — 2025-07-11   1011 rows   positive 77.3492%
validation  2025-07-12 — 2026-02-12    216 rows   positive 100.0000%
test        2026-02-13 — 2026-09-18    218 rows   positive 99.0826%
```

Цей split виявив суттєву зміну source-label distribution. Validation не містить жодного negative day, тому стандартне binary classification evaluation є методологічно некоректним для поточної постановки.

Quality gate:

```text
national feature generation       ALLOWED
national binary classification    BLOCKED_SINGLE_CLASS_EVALUATION
oblast-level training             BLOCKED_MEDIUM_CONFIDENCE_ONLY
region-link coverage              23.97%
high-confidence region events     0
medium-confidence region events   994
```

## 16. Наступний крок

**Sprint 7 — Offline historical ML backtest** починається не з навчання Logistic Regression/Random Forest, а з переоцінки target formulation.

Допустимий напрям для наступного етапу:

1. залишити поточний binary classifier заблокованим;
2. дослідити агреговану national-level historical activity target, яка має достатню варіативність у всіх chronological partitions;
3. перевірити distribution shift до training;
4. порівнювати model лише з простим naive/dummy baseline;
5. зберігати лише retrospective evaluation artifacts;
6. не створювати live/current endpoint для прогнозу майбутніх ударів, цілей, маршрутів або конкретних регіонів.