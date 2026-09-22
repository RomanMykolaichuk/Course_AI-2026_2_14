from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo.build_demo import build_demo


class DemoBuilderTests(unittest.TestCase):
    @patch("src.demo.build_demo.get_db_path")
    @patch("src.demo.build_demo.check_database")
    @patch("src.demo.build_demo.record_historical_count_evaluation")
    @patch("src.demo.build_demo.load_boundary_reference")
    @patch("src.demo.build_demo.acquire_adm1")
    @patch("src.demo.build_demo.load_primary_snapshot")
    @patch("src.demo.build_demo.acquire_snapshot")
    def test_build_demo_orchestrates_complete_reproducible_flow(
        self,
        acquire_primary,
        load_primary,
        acquire_boundaries,
        load_boundaries,
        record_evaluation,
        check_database,
        get_db_path,
    ) -> None:
        acquire_primary.return_value = Path("/tmp/raw/primary/2026-09-22")
        load_primary.return_value = {
            "build_id": "primary-test",
            "stats": {
                "events": 100,
                "region_links": 25,
            },
        }
        acquire_boundaries.return_value = Path("/tmp/gis/UKR-ADM1-test")
        load_boundaries.return_value = {
            "boundary_id": "UKR-ADM1-test",
            "mapped_regions": 27,
        }
        record_evaluation.return_value = {
            "evaluation_id": "eval-test",
            "deployment_status": "blocked_research_only",
        }
        check_database.return_value = (
            True,
            [
                "PASS: integrity_check = ok.",
                "PASS: all expected tables exist.",
            ],
        )
        get_db_path.return_value = Path("/tmp/demo.db")

        result = build_demo(db_path="/tmp/demo.db")

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["primary_build_id"], "primary-test")
        self.assertEqual(result["canonical_events"], 100)
        self.assertEqual(result["region_links"], 25)
        self.assertEqual(result["mapped_regions"], 27)
        self.assertEqual(
            result["model_evaluation"]["deployment_status"],
            "blocked_research_only",
        )
        self.assertEqual(
            result["serve_command"],
            "uvicorn api.main:app --reload",
        )

        acquire_primary.assert_called_once()
        load_primary.assert_called_once()
        acquire_boundaries.assert_called_once()
        load_boundaries.assert_called_once()
        record_evaluation.assert_called_once()
        check_database.assert_called_once()


if __name__ == "__main__":
    unittest.main()
