from __future__ import annotations

import unittest

from src.preprocessing.boundaries import (
    canonicalize_boundaries,
    match_boundary_region_code,
    normalize_boundary_name,
)


class BoundaryMappingTests(unittest.TestCase):
    def test_shape_iso_disambiguates_kyiv(self) -> None:
        self.assertEqual(
            match_boundary_region_code("Kyiv", "UA-30"),
            "kyiv_city",
        )
        self.assertEqual(
            match_boundary_region_code("Kyiv", "UA-32"),
            "kyiv_oblast",
        )

    def test_text_fallback_handles_oblast_name(self) -> None:
        self.assertEqual(
            match_boundary_region_code("Odes'ka Oblast"),
            "odesa_oblast",
        )
        self.assertEqual(
            normalize_boundary_name("Ivano-Frankivs'ka Oblast"),
            "ivano frankivska",
        )

    def test_canonicalize_reports_complete_mapping(self) -> None:
        geometry = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "shapeName": "Kyiv",
                        "shapeISO": "UA-30",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "shapeName": "Kyiv",
                        "shapeISO": "UA-32",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [],
                    },
                },
            ],
        }

        canonical, report = canonicalize_boundaries(geometry)

        self.assertEqual(report["feature_count"], 2)
        self.assertEqual(report["mapped_count"], 2)
        self.assertEqual(report["duplicate_region_codes"], [])
        self.assertEqual(
            {
                feature["properties"]["region_code"]
                for feature in canonical["features"]
            },
            {"kyiv_city", "kyiv_oblast"},
        )


if __name__ == "__main__":
    unittest.main()
