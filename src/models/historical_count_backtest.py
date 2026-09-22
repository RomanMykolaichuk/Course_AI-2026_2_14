from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.features.national_daily import (
    MODEL_FEATURE_COLUMNS,
    build_national_daily_features,
    build_national_daily_targets,
    model_ready_national_daily,
)
from src.features.split import chronological_split
from src.features.target_diagnostics import diagnose_national_targets


TARGET_COLUMN = "source_event_count"


def _join_target(
    partition: pd.DataFrame,
    targets: pd.DataFrame,
) -> pd.DataFrame:
    joined = partition.merge(
        targets[["date", TARGET_COLUMN]],
        on="date",
        how="left",
        validate="one_to_one",
    )
    if joined[TARGET_COLUMN].isna().any():
        raise ValueError("Historical target is missing for one or more partition dates")
    return joined


def _metrics(y_true, y_pred) -> dict[str, float]:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "rmse": round(
            float(math.sqrt(mean_squared_error(y_true, y_pred))),
            6,
        ),
        "r2": round(float(r2_score(y_true, y_pred)), 6),
    }


def run_historical_count_backtest(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate fixed baselines on already-observed historical dates only.

    This function intentionally exposes no future-date inference API and does
    not persist a deployable fitted model.
    """
    diagnostics = diagnose_national_targets(db_path)
    target_gate = diagnostics["source_event_count_regression"]
    if target_gate["status"] != "evaluable_retrospectively":
        raise ValueError(
            "source_event_count target failed diagnostics: "
            + target_gate["status"]
        )

    features = model_ready_national_daily(
        build_national_daily_features(db_path)
    )
    split = chronological_split(features)
    targets = build_national_daily_targets(db_path)

    partitions = {
        "train": _join_target(split.train, targets),
        "validation": _join_target(split.validation, targets),
        "test": _join_target(split.test, targets),
    }

    train = partitions["train"]
    X_train = train[MODEL_FEATURE_COLUMNS]
    y_train = train[TARGET_COLUMN]

    fitted_models = {
        "dummy_median": DummyRegressor(strategy="median"),
        "random_forest_fixed": RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=1,
        ),
    }
    for model in fitted_models.values():
        model.fit(X_train, y_train)

    evaluation: dict[str, Any] = {}
    for partition_name in ("validation", "test"):
        frame = partitions[partition_name]
        X = frame[MODEL_FEATURE_COLUMNS]
        y = frame[TARGET_COLUMN]

        partition_metrics: dict[str, Any] = {
            "rows": int(len(frame)),
            "first_date": frame["date"].min(),
            "last_date": frame["date"].max(),
            "target_mean": round(float(y.mean()), 6),
            "target_std": round(float(y.std(ddof=0)), 6),
            "models": {},
        }

        # Persistence baseline: previous day's canonical source-event count.
        partition_metrics["models"]["naive_lag1"] = _metrics(
            y,
            frame["event_count_lag1"],
        )

        for name, model in fitted_models.items():
            partition_metrics["models"][name] = _metrics(
                y,
                model.predict(X),
            )

        evaluation[partition_name] = partition_metrics

    return {
        "task": "offline_historical_national_source_event_count_backtest",
        "target": TARGET_COLUMN,
        "target_semantics": (
            "Number of canonical source rows for an already-observed historical "
            "calendar date. It is not a count of all real-world attacks."
        ),
        "feature_columns": MODEL_FEATURE_COLUMNS,
        "training_policy": (
            "Fixed models are fit only on the chronological training partition. "
            "No shuffle, no future-date feature construction, no live inference."
        ),
        "artifact_policy": (
            "This command returns retrospective metrics only and does not save "
            "a deployable fitted model."
        ),
        "target_diagnostics": target_gate,
        "evaluation": evaluation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run offline historical national source-count backtests."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = run_historical_count_backtest(args.db_path)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
