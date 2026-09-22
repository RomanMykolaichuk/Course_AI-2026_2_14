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
│   │   └── queries.py
│   ├── ingestion/
│   ├── preprocessing/
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
- [ ] отримати versioned snapshot `missile_attacks_daily.csv`;
- [ ] зберегти metadata/checksum;
- [ ] реалізувати primary-source ingestion parser;
- [ ] реалізувати canonical transformation;
- [ ] завантажити `attack_events`;
- [ ] розібрати `target` у `attack_event_regions`;
- [ ] записати provenance у `dataset_builds`.

### Sprint 3 — EDA + SQL analytics
- дослідити пропуски та дублікати;
- проаналізувати неоднозначні target fields;
- створити базові SQL queries;
- побудувати перші графіки;
- визначити придатність даних для oblast-level ML labels.

### Sprint 4 — FastAPI + first dashboard
- перший analytics endpoint;
- daily timeline;
- KPI;
- перший Chart.js графік.

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

## 12. Наступний крок

Після SQLite foundation наступний практичний етап:

1. завантажити versioned snapshot `missile_attacks_daily.csv`;
2. зберегти metadata/checksum;
3. реалізувати `src/ingestion/` parser;
4. створити нормалізовані `attack_events`;
5. окремо розібрати `target` у `attack_event_regions`;
6. завантажити результат у SQLite;
7. виконати перший SQL/EDA аналіз;
8. перевірити, які записи реально придатні для oblast-level ML labels.
