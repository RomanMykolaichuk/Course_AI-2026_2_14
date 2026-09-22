# Ukraine Air Strike Analytics & Forecasting Dashboard

Навчальний проєкт з побудови інформаційно-аналітичної системи для аналізу історичних відкритих даних про повітряні атаки по території України та демонстрації методів машинного навчання для прогнозної аналітики.

## 1. Мета проєкту

Побудувати наскрізну навчальну систему:

```text
Open Data → ETL → Storage → Analytics → Machine Learning → API → Dashboard
```

Система має показати повний життєвий цикл даних: від отримання сирих відкритих даних до інтерактивної візуалізації, статистичного аналізу та демонстраційного ML-прогнозування.

> Проєкт має навчальний та дослідницький характер. Прогнозний модуль не призначений для оперативного застосування або прогнозування конкретних цілей, маршрутів чи точного місця майбутніх ударів.

## 2. Основні функції MVP

1. Завантаження історичних даних з документованих відкритих джерел.
2. Збереження незмінних source snapshots та provenance.
3. Очищення й нормалізація даних.
4. Формування canonical relational dataset.
5. Візуалізація:
   - кількість подій у часі;
   - розподіл за регіонами;
   - розподіл за категоріями повітряних засобів;
   - часові закономірності;
   - агрегована карта України.
6. Побудова baseline ML-моделі.
7. Порівняння декількох моделей класифікації.
8. Відображення результатів моделі у dashboard.

## 3. Базові джерела даних

Для MVP визначено такі ролі джерел:

- **Primary:** [Massive Missile Attacks on Ukraine](https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine) — історичні атаки, типи/моделі та кількісні показники;
- **GIS reference:** [geoBoundaries](https://www.geoboundaries.org/api.html) `gbOpen` ADM1 — межі областей;
- **Weather enrichment:** [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) — опційні історичні погодні ознаки;
- **Alert enrichment:** alerts.in.ua / Ukraine Alarm API — лише за наявності відтворюваного історичного архіву;
- **Independent validation:** ACLED та UCDP.

Детальний реєстр, ліцензії, обмеження та рішення щодо використання описані у [docs/data_sources.md](docs/data_sources.md).

## 4. ML-задача

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

## 5. Архітектура

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
PostgreSQL
   ↙        ↘
Analytics   ML model
   ↘        ↙
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

## 6. Структура репозиторію

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
│   └── external/     # GIS/reference/enrichment files
├── notebooks/
├── src/
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

## 7. Canonical data model

Початкова плоска схема `event → one region` не використовується, оскільки source row може містити кілька областей, напрямок або всю Україну.

Основна модель:

```text
attack_events
      │
      ├──< attack_event_regions >── regions
      │
      ├── optional alert_intervals
      └── optional weather_observations
```

Тобто:

- source attack observation зберігається без втрати оригінальної семантики;
- `target_raw` зберігається окремо;
- регіональні зв’язки виділяються в many-to-many таблицю;
- неоднозначні записи не отримують вигадану географічну точність.

Поля та правила mapping: [docs/data_dictionary.md](docs/data_dictionary.md).

## 8. Етапи реалізації

### Stage 1 — Data foundation
- [x] визначити primary/candidate sources;
- [x] описати ліцензії та обмеження;
- [x] визначити data zones;
- [x] визначити canonical relational schema;
- [ ] реалізувати acquisition першого snapshot;
- [ ] реалізувати primary-source ingestion parser;
- [ ] створити processed build manifest.

### Stage 2 — EDA
- очистити дані;
- дослідити пропуски та дублікати;
- проаналізувати неоднозначні target fields;
- побудувати базові графіки;
- визначити придатність даних для ML.

### Stage 3 — Feature engineering
- часові ознаки;
- rolling statistics;
- лагові ознаки;
- регіональні агрегати;
- optional historical weather/alert features.

### Stage 4 — Machine Learning
- baseline;
- Logistic Regression;
- Random Forest;
- chronological validation;
- порівняння метрик;
- feature importance / explainability.

### Stage 5 — API
- FastAPI;
- endpoints для аналітики;
- endpoint для демонстраційного агрегованого ML-прогнозу.

### Stage 6 — Dashboard
- KPI;
- карта;
- часові графіки;
- регіональна аналітика;
- ML-блок з чітко позначеними обмеженнями.

## 9. Принципи роботи з даними

- використовуються лише документовані відкриті/доступні для дослідження джерела;
- сирі дані не редагуються вручну;
- усі трансформації мають бути відтворюваними;
- походження кожного набору даних документується;
- `null` не перетворюється на `0`, якщо джерело не повідомляє нуль явно;
- неоднозначна географія не перетворюється на точну координату без доказового правила;
- raw source snapshots та processed dataset builds версіонуються;
- API keys/tokens не комітяться;
- оперативно чутливі сценарії та точне прогнозування цілей не входять до цілей проєкту;
- моделі оцінюються як статистичні моделі на історичних даних, а не як система оперативного передбачення.

Правила provenance/versioning: [docs/data_governance.md](docs/data_governance.md).

## 10. Наступний крок

Наступний практичний етап:

1. завантажити versioned snapshot `missile_attacks_daily.csv`;
2. зберегти metadata/checksum;
3. реалізувати `src/ingestion/` parser;
4. створити нормалізовані `attack_events`;
5. окремо розібрати `target` у `attack_event_regions`;
6. виконати перший EDA notebook;
7. перевірити, які записи реально придатні для oblast-level ML labels.

Після цього можна переходити до feature engineering та першої baseline-моделі.
