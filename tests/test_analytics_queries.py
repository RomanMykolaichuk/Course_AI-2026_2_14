from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.queries import (
    get_attribution_coverage,
    get_category_summary,
    get_daily_counts,
    get_latest_build,
    get_model_summary,
    get_overview,
    get_region_summary,
)
from src.db.seed_regions import seed_regions


class AnalyticsQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "analytics.db"
        initialize_database(self.db)
        seed_regions(self.db)

        with connect(self.db) as connection:
            connection.executemany(
                """
                INSERT INTO attack_events (
                    event_id, time_start, time_end, weapon_model, weapon_category,
                    launched, destroyed, source_name, source_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    ("e1", "2026-01-01", None, "Model A", "UAV", 10, 8, "test", "s1"),
                    ("e2", "2026-01-01T20:00:00Z", "2026-01-01T21:00:00Z", "Model A", "UAV", 4, 3, "test", "s1"),
                    ("e3", "2026-01-02", None, "Model B", "Cruise missile", 2, 1, "test", "s1"),
                ],
            )
            connection.executemany(
                """
                INSERT INTO attack_event_regions (
                    event_id, region_code, relation_type,
                    attribution_method, attribution_quality
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                [
                    ("e1", "kyiv_oblast", "target", "parsed", "medium"),
                    ("e2", "kyiv_oblast", "affected", "source_explicit_parsed", "high"),
                ],
            )
            connection.execute(
                """
                INSERT INTO dataset_builds (
                    build_id, source_name, source_snapshot,
                    transformation_version, rows_loaded
                )
                VALUES ('b1', 'test', 's1', 'test-v1', 3);
                """
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_overview(self) -> None:
        result = get_overview(self.db)
        self.assertEqual(result["events"], 3)
        self.assertEqual(result["first_date"], "2026-01-01")
        self.assertEqual(result["last_date"], "2026-01-02")
        self.assertEqual(result["events_with_region_link"], 2)
        self.assertEqual(result["region_link_coverage_pct"], 66.67)

    def test_daily_counts(self) -> None:
        rows = get_daily_counts(self.db)
        self.assertEqual(
            [(row["date"], row["events"]) for row in rows],
            [("2026-01-01", 2), ("2026-01-02", 1)],
        )
        self.assertEqual(rows[0]["launched_known_total"], 14)

    def test_category_and_model_summary(self) -> None:
        categories = get_category_summary(self.db)
        self.assertEqual(categories[0]["category"], "UAV")
        self.assertEqual(categories[0]["events"], 2)

        models = get_model_summary(self.db, limit=1)
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["model"], "Model A")

    def test_region_summary_is_evidence_only(self) -> None:
        rows = get_region_summary(self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["region_code"], "kyiv_oblast")
        self.assertEqual(rows[0]["events"], 2)
        self.assertEqual(rows[0]["high_confidence_events"], 1)
        self.assertEqual(rows[0]["medium_confidence_events"], 1)

    def test_attribution_coverage(self) -> None:
        result = get_attribution_coverage(self.db)
        self.assertEqual(result["events"], 3)
        self.assertEqual(result["events_with_region_link"], 2)
        self.assertEqual(result["events_with_high_confidence_region"], 1)
        self.assertEqual(result["events_with_medium_confidence_region"], 1)
        self.assertEqual(result["coverage_pct"], 66.67)

    def test_latest_build(self) -> None:
        result = get_latest_build(self.db)
        self.assertIsNotNone(result)
        self.assertEqual(result["build_id"], "b1")
        self.assertEqual(result["rows_loaded"], 3)


if __name__ == "__main__":
    unittest.main()
