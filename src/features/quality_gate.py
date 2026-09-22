from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.db.queries import get_attribution_coverage, get_latest_build

from .national_daily import (
    build_national_daily_features,
    model_ready_national_daily,
)
from .split import chronological_split, split_summary


def _national_daily_gate(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate whether the daily binary label supports chronological evaluation."""
    try:
        features = build_national_daily_features(db_path)
        ready = model_ready_national_daily(features)
        split = chronological_split(ready)
    except ValueError as exc:
        return {
            "status": "insufficient_data",
            "reason": str(exc),
        }

    summary = split_summary(split)
    validation = summary["validation"]
    test = summary["test"]

    validation_has_both_classes = (
        validation["positive_source_days"] > 0
        and validation["negative_source_days"] > 0
    )
    test_has_both_classes = (
        test["positive_source_days"] > 0
        and test["negative_source_days"] > 0
    )

    if not validation_has_both_classes or not test_has_both_classes:
        status = "blocked_single_class_evaluation"
        reason = (
            "Chronological validation/test partitions do not both contain positive "
            "and negative source days. Binary classification metrics would be "
            "misleading or undefined for at least one evaluation partition."
        )
    else:
        train_rate = summary["train"]["positive_rate"]
        test_rate = summary["test"]["positive_rate"]
        drift = abs(float(train_rate) - float(test_rate))

        if drift >= 0.20:
            status = "manual_review_distribution_shift"
            reason = (
                "The positive-source-day rate shifts by at least 20 percentage "
                "points between train and test. Review source/process changes "
                "before interpreting model performance."
            )
        else:
            status = "allowed_historical_backtest"
            reason = (
                "Both evaluation partitions contain both classes and no large "
                "train-to-test label-rate shift was detected by the basic gate."
            )

    return {
        "status": status,
        "reason": reason,
        "scope": "country-level daily source activity",
        "label": "source_event_present",
        "interpretation": (
            "This label describes presence of canonical source records, not proof "
            "of real-world attack presence/absence and not an operational forecast."
        ),
        "split": summary,
    }


def build_ml_quality_gate(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    attribution = get_attribution_coverage(db_path)
    build = get_latest_build(db_path)

    high = attribution["events_with_high_confidence_region"]
    medium = attribution["events_with_medium_confidence_region"]
    coverage = attribution["coverage_pct"]

    if high == 0 and medium > 0:
        regional_status = "blocked_medium_confidence_only"
        regional_reason = (
            "The current build has no high-confidence region-linked events. "
            "Available region links are medium-confidence evidence parsed from "
            "explicit administrative mentions in target text."
        )
    elif attribution["events_with_region_link"] == 0:
        regional_status = "blocked_no_region_labels"
        regional_reason = "The current build has no canonical region-linked events."
    else:
        regional_status = "manual_review_required"
        regional_reason = (
            "Some region evidence exists, but representativeness and missing-label "
            "mechanisms must be assessed before regional classification."
        )

    return {
        "source_build_id": build["build_id"] if build else None,
        "national_daily_feature_generation": {
            "status": "allowed",
            "scope": "country-level daily source activity",
            "constraint": (
                "Only lagged historical activity predictors are exported. "
                "Current-day outcome/count fields are excluded from model features."
            ),
        },
        "national_daily_binary_classification": _national_daily_gate(db_path),
        "oblast_level_training": {
            "status": regional_status,
            "reason": regional_reason,
            "region_link_coverage_pct": coverage,
            "events": attribution["events"],
            "events_with_region_link": attribution["events_with_region_link"],
            "events_with_high_confidence_region": high,
            "events_with_medium_confidence_region": medium,
            "events_with_low_confidence_region": attribution[
                "events_with_low_confidence_region"
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate whether current canonical data is suitable for ML tasks."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    args = parser.parse_args()

    print(
        json.dumps(
            build_ml_quality_gate(args.db_path),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
