from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.connection import PROJECT_ROOT, connect
from src.db.queries import get_latest_build


DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed" / "ml" / "national_daily"

MODEL_FEATURE_COLUMNS = [
    "day_of_week",
    "month",
    "day_of_year",
    "is_weekend",
    "event_count_lag1",
    "event_count_lag7",
    "launched_known_lag1",
    "uav_event_count_lag1",
    "missile_event_count_lag1",
    "event_count_roll7_prior",
    "event_count_roll30_prior",
    "launched_roll7_prior",
    "days_since_previous_source_event",
    "history_days_available",
]
LABEL_COLUMN = "source_event_present"


def _daily_source_aggregates(
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    with connect(db_path) as connection:
        frame = pd.read_sql_query(
            """
            SELECT
                substr(time_start, 1, 10) AS date,
                COUNT(*) AS event_count,
                SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END)
                    AS launched_known_total,
                SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END)
                    AS destroyed_known_total,
                SUM(CASE
                    WHEN lower(COALESCE(weapon_category, '')) = 'uav'
                    THEN 1 ELSE 0
                END) AS uav_event_count,
                SUM(CASE
                    WHEN lower(COALESCE(weapon_category, '')) LIKE '%missile%'
                    THEN 1 ELSE 0
                END) AS missile_event_count
            FROM attack_events
            WHERE time_start IS NOT NULL
            GROUP BY substr(time_start, 1, 10)
            ORDER BY date;
            """,
            connection,
        )

    if frame.empty:
        raise ValueError("attack_events is empty; cannot build daily features")

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    return frame


def build_national_daily_features(
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build a leakage-safe national daily historical feature table.

    The label is source_event_present: whether the canonical source dataset
    contains at least one event on that calendar date. It is deliberately not
    named 'attack_present' because source silence is not proof of real-world
    absence.
    """
    aggregates = _daily_source_aggregates(db_path)

    calendar = pd.DataFrame(
        {
            "date": pd.date_range(
                aggregates["date"].min(),
                aggregates["date"].max(),
                freq="D",
            )
        }
    )
    daily = calendar.merge(aggregates, on="date", how="left")

    count_columns = [
        "event_count",
        "launched_known_total",
        "destroyed_known_total",
        "uav_event_count",
        "missile_event_count",
    ]
    daily[count_columns] = daily[count_columns].fillna(0).astype("int64")

    daily["source_event_present"] = (daily["event_count"] > 0).astype("int8")
    daily["day_of_week"] = daily["date"].dt.dayofweek.astype("int8")
    daily["month"] = daily["date"].dt.month.astype("int8")
    daily["day_of_year"] = daily["date"].dt.dayofyear.astype("int16")
    daily["is_weekend"] = (daily["day_of_week"] >= 5).astype("int8")

    daily["event_count_lag1"] = daily["event_count"].shift(1)
    daily["event_count_lag7"] = daily["event_count"].shift(7)
    daily["launched_known_lag1"] = daily["launched_known_total"].shift(1)
    daily["uav_event_count_lag1"] = daily["uav_event_count"].shift(1)
    daily["missile_event_count_lag1"] = daily["missile_event_count"].shift(1)

    prior_event_count = daily["event_count"].shift(1)
    daily["event_count_roll7_prior"] = (
        prior_event_count.rolling(window=7, min_periods=1).mean()
    )
    daily["event_count_roll30_prior"] = (
        prior_event_count.rolling(window=30, min_periods=1).mean()
    )
    daily["launched_roll7_prior"] = (
        daily["launched_known_total"]
        .shift(1)
        .rolling(window=7, min_periods=1)
        .mean()
    )

    previous_event_date = (
        daily["date"]
        .where(daily["source_event_present"].eq(1))
        .shift(1)
        .ffill()
    )
    daily["days_since_previous_source_event"] = (
        daily["date"] - previous_event_date
    ).dt.days

    daily["history_days_available"] = daily.index.astype("int64")

    # Keep current-day source aggregates out of the exported ML table.
    # They are used only to construct the label and lagged historical features;
    # retaining them as columns would make accidental target leakage too easy.
    export_columns = ["date", LABEL_COLUMN, *MODEL_FEATURE_COLUMNS]

    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    return daily[export_columns].copy()


def model_ready_national_daily(features: pd.DataFrame) -> pd.DataFrame:
    """Return rows that can be used by baseline models without imputation.

    The first days naturally have missing lag/history values. For the initial
    educational baseline we drop those rows instead of imputing future-unknown
    history or introducing a more complex preprocessing pipeline.
    """
    required = ["date", LABEL_COLUMN, *MODEL_FEATURE_COLUMNS]
    missing = [column for column in required if column not in features.columns]
    if missing:
        raise ValueError(
            "National daily feature table is missing required columns: "
            + ", ".join(missing)
        )

    ready = (
        features[required]
        .dropna(subset=MODEL_FEATURE_COLUMNS)
        .sort_values("date")
        .reset_index(drop=True)
    )
    if ready.empty:
        raise ValueError("No model-ready rows remain after lag/history filtering")
    return ready


def feature_manifest(
    features: pd.DataFrame,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    latest_build = get_latest_build(db_path)
    positives = int(features["source_event_present"].sum())
    rows = int(len(features))
    return {
        "dataset_name": "national_daily_historical_features",
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_build_id": latest_build["build_id"] if latest_build else None,
        "rows": rows,
        "first_date": features["date"].min(),
        "last_date": features["date"].max(),
        "positive_source_days": positives,
        "negative_source_days": rows - positives,
        "positive_rate": round(positives / rows, 6) if rows else None,
        "label": LABEL_COLUMN,
        "model_feature_columns": MODEL_FEATURE_COLUMNS,
        "label_semantics": (
            "1 means at least one canonical source event exists on that date; "
            "0 means no canonical source record exists for that date and must "
            "not be interpreted as proof that no real-world attack occurred."
        ),
        "feature_timing": (
            "All activity predictors use only dates strictly before the label date. "
            "Current-day event/count aggregates are not exported as model features."
        ),
        "intended_use": "historical backtesting and education only",
        "columns": list(features.columns),
    }


def write_national_daily_features(
    db_path: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    features = build_national_daily_features(db_path)
    manifest = feature_manifest(features, db_path)

    root = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    build_label = manifest["source_build_id"] or "unversioned"
    output_dir = root / str(build_label)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "national_daily_features.csv"
    manifest_path = output_dir / "manifest.json"

    features.to_csv(csv_path, index=False)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        **manifest,
        "csv_path": str(csv_path),
        "manifest_path": str(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build leakage-safe national daily historical features."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    result = write_national_daily_features(
        db_path=args.db_path,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()