from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .national_daily import (
    LABEL_COLUMN,
    MODEL_FEATURE_COLUMNS,
    build_national_daily_features,
    model_ready_national_daily,
)


@dataclass(frozen=True)
class ChronologicalSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def chronological_split(
    frame: pd.DataFrame,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> ChronologicalSplit:
    """Split an already model-ready table strictly by chronological order."""
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation fractions must leave a test set")

    required = ["date", LABEL_COLUMN, *MODEL_FEATURE_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Split input is missing columns: " + ", ".join(missing))

    ordered = frame[required].copy()
    ordered["date"] = pd.to_datetime(ordered["date"], errors="raise")
    ordered = ordered.sort_values("date").reset_index(drop=True)

    if ordered["date"].duplicated().any():
        raise ValueError("Expected one row per date before chronological split")

    n_rows = len(ordered)
    if n_rows < 30:
        raise ValueError("At least 30 model-ready daily rows are required")

    train_end = max(1, int(n_rows * train_fraction))
    validation_end = train_end + max(1, int(n_rows * validation_fraction))
    validation_end = min(validation_end, n_rows - 1)

    train = ordered.iloc[:train_end].copy()
    validation = ordered.iloc[train_end:validation_end].copy()
    test = ordered.iloc[validation_end:].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError("Chronological split produced an empty partition")

    if not (
        train["date"].max() < validation["date"].min()
        and validation["date"].max() < test["date"].min()
    ):
        raise ValueError("Chronological partition ordering check failed")

    for partition in (train, validation, test):
        partition["date"] = partition["date"].dt.strftime("%Y-%m-%d")

    return ChronologicalSplit(
        train=train.reset_index(drop=True),
        validation=validation.reset_index(drop=True),
        test=test.reset_index(drop=True),
    )


def split_summary(split: ChronologicalSplit) -> dict[str, Any]:
    def describe(frame: pd.DataFrame) -> dict[str, Any]:
        positives = int(frame[LABEL_COLUMN].sum())
        rows = int(len(frame))
        return {
            "rows": rows,
            "first_date": frame["date"].min(),
            "last_date": frame["date"].max(),
            "positive_source_days": positives,
            "negative_source_days": rows - positives,
            "positive_rate": round(positives / rows, 6) if rows else None,
        }

    return {
        "strategy": "chronological_no_shuffle",
        "label": LABEL_COLUMN,
        "features": MODEL_FEATURE_COLUMNS,
        "train": describe(split.train),
        "validation": describe(split.validation),
        "test": describe(split.test),
    }


def write_national_daily_splits(
    db_path: str | Path | None = None,
    output_dir: str | Path = "data/processed/ml/national_daily/splits",
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> dict[str, Any]:
    features = build_national_daily_features(db_path)
    ready = model_ready_national_daily(features)
    split = chronological_split(
        ready,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
    )

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    split.train.to_csv(target / "train.csv", index=False)
    split.validation.to_csv(target / "validation.csv", index=False)
    split.test.to_csv(target / "test.csv", index=False)

    summary = split_summary(split)
    (target / "split_manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        **summary,
        "output_dir": str(target),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create chronological national-daily ML partitions."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument("--output-dir", default="/tmp/national-daily-splits")
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    args = parser.parse_args()

    result = write_national_daily_splits(
        db_path=args.db_path,
        output_dir=args.output_dir,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
