from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.map_data import build_region_geojson
from src.db.seed_regions import seed_regions


class MapDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.db = root / "map.db"
        self.snapshot = root / "UKR-ADM1-test"
        self.snapshot.mkdir()

        initialize_database(self.db)
        seed_regions(self.db)

        with connect(self.db) as connection:
            connection.execute(
                """
                INSERT INTO attack_events (
                    event_id, time_start, weapon_model, weapon_category,
                    source_name, source_snapshot
                )
                VALUES ('e1', '2026-01-01', 'Model A', 'UAV', 'test', 's1');
                """
            )
            connection.execute(
                """
                INSERT INTO attack_event_regions (
                    event_id, region_code, relation_type,
                    attribution_method, attribution_quality
                )
                VALUES ('e1', 'kyiv_oblast', 'target', 'parsed', 'medium');
                """
            )
            connection.commit()

        geometry = {
            "type": "FeatureCollection",
            "features": [
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
                {
                    "type": "Feature",
                    "properties": {
                        "shapeName": "Odes'ka Oblast",
                        "shapeISO": "UA-51",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [],
                    },
                },
            ],
        }
        metadata = {
            "boundaryID": "UKR-ADM1-test",
            "boundaryYearRepresented": "2017",
            "buildDate": "test",
            "boundarySource": "test geometry",
            "boundaryLicense": "test license",
            "licenseSource": "https://example.org/license",
            "geometrySHA256": "abc123",
            "geometryVariant": "simplified",
        }

        (self.snapshot / "UKR_ADM1.geojson").write_text(
            json.dumps(geometry),
            encoding="utf-8",
        )
        (self.snapshot / "metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_geojson_merges_evidence_without_converting_missing_to_zero_truth(self) -> None:
        result = build_region_geojson(
            db_path=self.db,
            snapshot_dir=self.snapshot,
        )

        by_code = {
            feature["properties"]["region_code"]: feature["properties"]
            for feature in result["features"]
        }

        self.assertEqual(by_code["kyiv_oblast"]["events"], 1)
        self.assertTrue(by_code["kyiv_oblast"]["has_region_evidence"])
        self.assertEqual(
            by_code["kyiv_oblast"]["medium_confidence_events"],
            1,
        )

        self.assertEqual(by_code["odesa_oblast"]["events"], 0)
        self.assertFalse(by_code["odesa_oblast"]["has_region_evidence"])

        self.assertEqual(result["metadata"]["mapped_count"], 2)
        self.assertEqual(result["metadata"]["events"], 1)
        self.assertEqual(result["metadata"]["events_with_region_link"], 1)
        self.assertEqual(
            result["metadata"]["region_attribution_coverage_pct"],
            100.0,
        )


if __name__ == "__main__":
    unittest.main()
