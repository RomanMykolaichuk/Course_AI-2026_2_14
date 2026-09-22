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

1. Завантаження історичних даних з одного або кількох відкритих джерел.
2. Очищення та нормалізація даних.
3. Формування єдиного набору даних для аналізу.
4. Візуалізація:
   - кількість подій у часі;
   - розподіл за регіонами;
   - розподіл за категоріями повітряних засобів;
   - часові закономірності;
   - агрегована карта України.
5. Побудова baseline ML-моделі.
6. Порівняння декількох моделей класифікації.
7. Відображення результатів моделі у dashboard.

## 3. ML-задача

Початкова навчальна постановка:

**оцінювання ймовірності наявності події у певному регіоні протягом наступного агрегованого часового інтервалу на основі історичних ознак.**

Приклади ознак:

- region;
- day_of_week;
- month;
- previous_24h_events;
- previous_7d_events;
- rolling_mean_7d;
- rolling_mean_30d;
- days_since_previous_event;
- historical weapon-category activity.

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

## 4. Архітектура

```text
Public Open Data
       ↓
 ingestion/
       ↓
 raw CSV / JSON
       ↓
 preprocessing / ETL
       ↓
 processed dataset
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

## 5. Структура репозиторію

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   ├── raw/
│   └── processed/
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
└── docs/
```

## 6. Етапи реалізації

### Stage 1 — Data
- визначити джерела;
- описати ліцензії та обмеження;
- завантажити перший dataset;
- визначити canonical schema.

### Stage 2 — EDA
- очистити дані;
- дослідити пропуски та дублікати;
- побудувати базові графіки;
- визначити придатність даних для ML.

### Stage 3 — Feature engineering
- часові ознаки;
- rolling statistics;
- лагові ознаки;
- регіональні агрегати.

### Stage 4 — Machine Learning
- baseline;
- Logistic Regression;
- Random Forest;
- порівняння метрик;
- feature importance / explainability.

### Stage 5 — API
- FastAPI;
- endpoints для аналітики;
- endpoint для демонстраційного прогнозу.

### Stage 6 — Dashboard
- KPI;
- карта;
- часові графіки;
- регіональна аналітика;
- ML-блок.

## 7. Принципи роботи з даними

- використовуються лише відкриті джерела;
- сирі дані не редагуються вручну;
- усі трансформації мають бути відтворюваними;
- походження кожного набору даних документується;
- оперативно чутливі сценарії та точне прогнозування цілей не входять до цілей проєкту;
- моделі оцінюються як статистичні моделі на історичних даних, а не як система оперативного передбачення.

## 8. Наступний крок

Наступний етап — вибір першого джерела даних та формування canonical dataset schema:

```text
event_id
event_date
event_time
region
weapon_category
weapon_type
count
status
source
source_url
latitude
longitude
notes
```

Після цього буде створено перший ingestion pipeline та notebook для первинного аналізу.
