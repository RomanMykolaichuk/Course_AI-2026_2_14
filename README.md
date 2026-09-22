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
│   │   └── queries.py
│   ├── ingestion/
│   │   └── acquire_primary.py
│   ├── preprocessing/
│   │   ├── primary_dataset.py
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
- canonical region reference;
- geoBoundaries ADM1;
- Leaflet;
- агрегована історична карта.

### Sprint 6 — ML dataset
- часові ознаки;
- rolling statistics;
- лагові ознаки;
- регіональні агрегати;
- leakage-safe feature table.

### Sprint 7 — ML models
- DummyClassifier;
- Logistic Regression;
- Random Forest;
- chronological validation;
- метрики та explainability.

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

Після acquisition та SQLite load:

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
```

Поточний dashboard показує лише ретроспективну аналітику. Показники `launched_known_total` та `destroyed_known_total` — суми відомих числових значень у джерелі, а не твердження про повноту всіх реальних запусків/знищень.

## 14. Наступний крок

**Sprint 5 — Regional map**:

1. завантажити versioned geoBoundaries ADM1 snapshot;
2. зіставити canonical `region_code` з геометрією;
3. додати GeoJSON endpoint;
4. інтегрувати Leaflet;
5. показувати лише available region evidence з помітним coverage indicator.

До ML переходимо лише після окремої оцінки придатності регіональної розмітки; поточні 23.97% region-link coverage не слід автоматично вважати достатнім oblast-level training label.