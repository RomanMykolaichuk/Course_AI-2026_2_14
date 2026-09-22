from __future__ import annotations

from pathlib import Path
from typing import Any

from src.preprocessing.boundaries import canonicalize_boundaries, load_boundary_snapshot
from src.preprocessing.regions import REGIONS

from .queries import get_attribution_coverage, get_region_summary


def build_region_geojson(
    db_path: str | Path | None = None,
    snapshot_dir: str | Path | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Merge canonical ADM1 geometry with evidence-only retrospective statistics."""
    geometry, metadata = load_boundary_snapshot(snapshot_dir)
    canonical, report = canonicalize_boundaries(geometry)

    if strict and (
        report["mapped_count"] != report["feature_count"]
        or report["duplicate_region_codes"]
    ):
        raise ValueError(
            "Boundary mapping is incomplete or ambiguous: "
            f"unmapped={report['unmapped_names']}, "
            f"duplicates={report['duplicate_region_codes']}"
        )

    statistics = {
        row["region_code"]: row
        for row in get_region_summary(db_path)
    }
    canonical_names = {
        region.code: region
        for region in REGIONS
    }

    for feature in canonical["features"]:
        properties = feature["properties"]
        code = properties.get("region_code")
        stat = statistics.get(code, {})
        region = canonical_names.get(code)

        properties.update(
            {
                "name_uk": region.name_uk if region else None,
                "name_en": region.name_en if region else None,
                "events": int(stat.get("events", 0) or 0),
                "high_confidence_events": int(
                    stat.get("high_confidence_events", 0) or 0
                ),
                "medium_confidence_events": int(
                    stat.get("medium_confidence_events", 0) or 0
                ),
                "low_confidence_events": int(
                    stat.get("low_confidence_events", 0) or 0
                ),
                "has_region_evidence": bool(stat.get("events", 0)),
            }
        )

    attribution = get_attribution_coverage(db_path)
    canonical["metadata"] = {
        "boundary_id": metadata.get("boundaryID"),
        "boundary_year_represented": metadata.get("boundaryYearRepresented"),
        "boundary_build_date": metadata.get("buildDate"),
        "boundary_source": metadata.get("boundarySource"),
        "boundary_license": metadata.get("boundaryLicense"),
        "boundary_license_source": metadata.get("licenseSource"),
        "geometry_sha256": metadata.get("geometrySHA256"),
        "geometry_variant": metadata.get("geometryVariant"),
        "feature_count": report["feature_count"],
        "mapped_count": report["mapped_count"],
        "region_attribution_coverage_pct": attribution["coverage_pct"],
        "events": attribution["events"],
        "events_with_region_link": attribution["events_with_region_link"],
        "interpretation": (
            "Map values represent only canonical events with available region evidence; "
            "a zero value does not prove absence of attacks in that region."
        ),
    }
    return canonical
