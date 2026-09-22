from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.db.queries import get_attribution_coverage, get_latest_build


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
        "national_daily_historical_backtest": {
            "status": "allowed",
            "scope": "country-level daily source activity",
            "constraint": (
                "Use only lagged historical features and interpret predictions as "
                "patterns in the source dataset, not operational strike forecasts."
            ),
        },
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
