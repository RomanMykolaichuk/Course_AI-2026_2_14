from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.queries import get_latest_model_evaluation
from src.db.seed_regions import seed_regions
from src.models.historical_count_backtest import run_historical_count_backtest
from src.models.record_evaluation import record_historical_count_evaluation


class HistoricalCountBacktestTests(unittest.TestCase):
    def test_backtest_returns_retrospective_metrics_only(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            db = Path(temp.name) / "model.db"
            initialize_database(db)
            seed_regions(db)

            rows = []
            dates = pd.date_range("2026-01-01", periods=70, freq="D")
            for day_index, date in enumerate(dates):
                count = 1 + (day_index % 5)
                for event_index in range(count):
                    rows.append(
                        (
                            f"d{day_index}-e{event_index}",
                            date.strftime("%Y-%m-%d"),
                            "Model",
                            "UAV",
                            count,
                            "test",
                            "snapshot",
                        )
                    )

            with connect(db) as connection:
                connection.executemany(
                    """
                    INSERT INTO attack_events (
                        event_id, time_start, weapon_model, weapon_category,
                        launched, source_name, source_snapshot
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    rows,
                )
                connection.execute(
                    """
                    INSERT INTO dataset_builds (
                        build_id, source_name, source_snapshot,
                        transformation_version, rows_loaded
                    )
                    VALUES (
                        'model-build', 'test', 'snapshot', 'test-v1', ?
                    );
                    """,
                    (len(rows),),
                )
                connection.commit()

            result = run_historical_count_backtest(db)

            self.assertEqual(
                result["task"],
                "offline_historical_national_source_event_count_backtest",
            )
            self.assertIn("does not save", result["artifact_policy"])
            self.assertEqual(
                set(result["evaluation"]["test"]["models"]),
                {"naive_lag1", "dummy_median", "random_forest_fixed"},
            )
            for model_metrics in result["evaluation"]["test"]["models"].values():
                self.assertIn("mae", model_metrics)
                self.assertIn("rmse", model_metrics)
                self.assertIn("r2", model_metrics)

            self.assertIn(
                result["deployment_gate"]["status"],
                {"blocked_research_only", "manual_review_required"},
            )
            self.assertIn(
                result["comparison"]["lowest_test_mae_model"],
                {"naive_lag1", "dummy_median", "random_forest_fixed"},
            )
        finally:
            temp.cleanup()



    def test_evaluation_registry_persists_metrics_not_model(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            db = Path(temp.name) / "registry.db"
            initialize_database(db)
            seed_regions(db)

            rows = []
            dates = pd.date_range("2026-01-01", periods=70, freq="D")
            for day_index, date in enumerate(dates):
                count = 1 + (day_index % 5)
                for event_index in range(count):
                    rows.append(
                        (
                            f"r{day_index}-e{event_index}",
                            date.strftime("%Y-%m-%d"),
                            "Model",
                            "UAV",
                            count,
                            "test",
                            "snapshot",
                        )
                    )

            with connect(db) as connection:
                connection.executemany(
                    """
                    INSERT INTO attack_events (
                        event_id, time_start, weapon_model, weapon_category,
                        launched, source_name, source_snapshot
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    rows,
                )
                connection.execute(
                    """
                    INSERT INTO dataset_builds (
                        build_id, source_name, source_snapshot,
                        transformation_version, rows_loaded
                    )
                    VALUES (
                        'registry-build', 'test', 'snapshot', 'test-v1', ?
                    );
                    """,
                    (len(rows),),
                )
                connection.commit()

            recorded = record_historical_count_evaluation(db)
            latest = get_latest_model_evaluation(db)

            self.assertIsNotNone(latest)
            self.assertEqual(latest["evaluation_id"], recorded["evaluation_id"])
            self.assertEqual(latest["source_build_id"], "registry-build")
            self.assertEqual(
                latest["deployment_status"],
                recorded["deployment_status"],
            )
            self.assertEqual(
                latest["comparison"],
                recorded["comparison"],
            )
            self.assertIn("models", latest["validation"])
            self.assertIn("models", latest["test"])

            with connect(db) as connection:
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(model_evaluations);"
                    ).fetchall()
                }
            self.assertNotIn("model_blob", columns)
            self.assertNotIn("model_path", columns)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()