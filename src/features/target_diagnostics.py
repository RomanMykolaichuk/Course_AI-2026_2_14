from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .national_daily import (
    build_national_daily_features,
    build_national_daily_targets,
    model_ready_national_daily,
)
from .split import chronological_split


def _partition_target(
    partition: pd.DataFrame,
    targets: pd.DataFrame,
) -> pd.DataFrame:
    joined = partition[["date"]].merge(targets, on="date", how="left")
    if joined["source_event_count"].isna().any():
        raise ValueError("Target series is missing dates from a chronological partition")
    return joined


def _count_summary(frame: pd.DataFrame) -> dict[str, Any]:
    series = frame["source_event_count"].astype(float)
    return {
        "rows": int(len(series)),
        "first_date": frame["date"].min(),
        "last_date": frame["date"].max(),
        "mean": round(float(series.mean()), 6),
        "median": round(float(series.median()), 6),
        "std": round(float(series.std(ddof=0)), 6),
        "min": int(series.min()),
        "max": int(series.max()),
        "unique_values": int(series.nunique()),
        "zero_days": int(series.eq(0).sum()),
    }


def _binary_balance(
    frame: pd.DataFrame,
    threshold: float,
) -> dict[str, Any]:
    label = frame["source_event_count"].astype(float).ge(threshold)
    positives = int(label.sum())
    rows = int(len(label))
    negatives = rows - positives
    return {
        "rows": rows,
        "positive_days": positives,
        "negative_days": negatives,
        "positive_rate": round(positives / rows, 6) if rows else None,
        "contains_both_classes": bool(positives > 0 and negatives > 0),
    }


def diagnose_national_targets(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Diagnose aggregate source-level targets before any model is trained.

    Thresholds for candidate binary labels are learned from the training
    partition only and then frozen for validation/test diagnostics.
    """
    features = model_ready_national_daily(
        build_national_daily_features(db_path)
    )
    split = chronological_split(features)
    targets = build_national_daily_targets(db_path)

    partitions = {
        "train": _partition_target(split.train, targets),
        "validation": _partition_target(split.validation, targets),
        "test": _partition_target(split.test, targets),
    }

    count_summaries = {
        name: _count_summary(frame)
        for name, frame in partitions.items()
    }
    count_evaluable = all(
        count_summaries[name]["unique_values"] >= 3
        and count_summaries[name]["std"] > 0
        for name in ("validation", "test")
    )

    train_counts = partitions["train"]["source_event_count"].astype(float)
    thresholds = {
        "train_median": float(train_counts.quantile(0.50)),
        "train_q75": float(train_counts.quantile(0.75)),
    }

    binary_candidates: dict[str, Any] = {}
    for name, threshold in thresholds.items():
        balance = {
            partition_name: _binary_balance(partition, threshold)
            for partition_name, partition in partitions.items()
        }
        evaluable = (
            balance["validation"]["contains_both_classes"]
            and balance["test"]["contains_both_classes"]
        )
        binary_candidates[name] = {
            "definition": "source_event_count >= training-derived threshold",
            "threshold": round(threshold, 6),
            "status": (
                "evaluable_retrospectively"
                if evaluable
                else "blocked_single_class_evaluation"
            ),
            "balance": balance,
        }

    return {
        "scope": "country-level historical source activity",
        "interpretation": (
            "Targets describe canonical source-record activity only. Diagnostics "
            "are for offline historical backtesting and do not authorize live or "
            "current operational forecasting."
        ),
        "source_event_count_regression": {
            "status": (
                "evaluable_retrospectively"
                if count_evaluable
                else "blocked_insufficient_target_variation"
            ),
            "partitions": count_summaries,
        },
        "binary_high_activity_candidates": binary_candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose aggregate historical ML target formulations."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    args = parser.parse_args()

    print(
        json.dumps(
            diagnose_national_targets(args.db_path),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()