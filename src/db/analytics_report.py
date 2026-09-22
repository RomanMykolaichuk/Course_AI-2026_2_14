from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .queries import (
    get_attribution_coverage,
    get_category_summary,
    get_latest_build,
    get_model_summary,
    get_overview,
    get_region_summary,
)


def build_analytics_report(
    db_path: str | Path | None = None,
    model_limit: int = 10,
    region_limit: int = 10,
) -> dict[str, Any]:
    """Build a compact retrospective analytics report from canonical SQLite data."""
    return {
        "latest_build": get_latest_build(db_path),
        "overview": get_overview(db_path),
        "attribution": get_attribution_coverage(db_path),
        "categories": get_category_summary(db_path),
        "top_models": get_model_summary(db_path, limit=model_limit),
        "top_regions_with_available_evidence": get_region_summary(db_path)[:region_limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a compact retrospective analytics report as JSON."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument("--model-limit", type=int, default=10)
    parser.add_argument("--region-limit", type=int, default=10)
    args = parser.parse_args()

    report = build_analytics_report(
        db_path=args.db_path,
        model_limit=args.model_limit,
        region_limit=args.region_limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
