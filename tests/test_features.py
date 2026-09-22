from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.seed_regions import seed_regions
from src.features.national_daily import (
    LABEL_COLUMN,
    MODEL_FEATURE_COLUMNS,
    build_national_daily_features,
    feature_manifest,
)
from src.features.split import chronological_split, split_summary
from src.features.quality_gate import build_ml_quality_gate


class NationalDailyFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "features.db"
        initialize_database(self.db)
        seed_regions(self.db)

        with connect(self.db) as connection:
            connection.executemany(
                """
                INSERT INTO attack_events (
                    event_id, time_start, weapon_model, weapon_category,
                    launched, destroyed, source_name, source_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        "e1",
                        "2026-01-01",
                        "Model A",
                        "UAV",
                        10,
                        8,
                        "test",
                        "snapshot",
                    ),
                    (
                        "e2",
                        "2026-01-03",
                        "Model B",
                        "cruise missile",
                        2,
                        1,
                        "test",
                        "snapshot",
                    ),
                ],
            )
            connection.execute(
                """
                INSERT INTO dataset_builds (
                    build_id, source_name, source_snapshot,
                    transformation_version, rows_loaded
                )
                VALUES ('build-test', 'test', 'snapshot', 'test-v1', 2);
                """
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_complete_calendar_and_source_label_semantics(self) -> None:
        features = build_national_daily_features(self.db)

        self.assertEqual(
            list(features["date"]),
            ["2026-01-01", "2026-01-02", "2026-01-03"],
        )
        self.assertEqual(
            list(features["source_event_present"]),
            [1, 0, 1],
        )

    def test_lags_use_only_prior_days(self) -> None:
        features = build_national_daily_features(self.db).set_index("date")

        self.assertTrue(pd.isna(features.loc["2026-01-01", "event_count_lag1"]))
        self.assertEqual(features.loc["2026-01-02", "event_count_lag1"], 1)
        self.assertEqual(features.loc["2026-01-03", "event_count_lag1"], 0)
        self.assertEqual(
            features.loc["2026-01-03", "event_count_roll7_prior"],
            0.5,
        )
        self.assertEqual(
            features.loc["2026-01-03", "days_since_previous_source_event"],
            2,
        )

    def test_target_day_outcomes_are_not_exported_as_predictors(self) -> None:
        features = build_national_daily_features(self.db)

        forbidden = {
            "event_count",
            "launched_known_total",
            "destroyed_known_total",
            "uav_event_count",
            "missile_event_count",
        }
        self.assertTrue(forbidden.isdisjoint(features.columns))

    def test_manifest_preserves_cautious_label_semantics(self) -> None:
        features = build_national_daily_features(self.db)
        manifest = feature_manifest(features, self.db)

        self.assertEqual(manifest["source_build_id"], "build-test")
        self.assertEqual(manifest["rows"], 3)
        self.assertEqual(manifest["positive_source_days"], 2)
        self.assertEqual(manifest["negative_source_days"], 1)
        self.assertIn("not be interpreted as proof", manifest["label_semantics"])
        self.assertIn("Current-day", manifest["feature_timing"])


class ChronologicalSplitTests(unittest.TestCase):
    def test_split_is_ordered_and_has_no_overlap(self) -> None:
        dates = pd.date_range("2026-01-01", periods=40, freq="D")
        frame = pd.DataFrame(
            {
                "date": dates.strftime("%Y-%m-%d"),
                LABEL_COLUMN: [index % 2 for index in range(40)],
            }
        )
        for index, column in enumerate(MODEL_FEATURE_COLUMNS):
            frame[column] = [float(row + index + 1) for row in range(40)]

        split = chronological_split(frame)
        summary = split_summary(split)

        self.assertEqual(len(split.train), 28)
        self.assertEqual(len(split.validation), 6)
        self.assertEqual(len(split.test), 6)
        self.assertLess(
            split.train["date"].max(),
            split.validation["date"].min(),
        )
        self.assertLess(
            split.validation["date"].max(),
            split.test["date"].min(),
        )
        self.assertEqual(summary["strategy"], "chronological_no_shuffle")
        self.assertEqual(summary["features"], MODEL_FEATURE_COLUMNS)

    def test_split_rejects_duplicate_dates(self) -> None:
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        frame = pd.DataFrame(
            {
                "date": dates.strftime("%Y-%m-%d"),
                LABEL_COLUMN: [0] * 30,
            }
        )
        for column in MODEL_FEATURE_COLUMNS:
            frame[column] = 1.0

        frame.loc[1, "date"] = frame.loc[0, "date"]

        with self.assertRaisesRegex(ValueError, "one row per date"):
            chronological_split(frame)


class MlQualityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "quality.db"
        initialize_database(self.db)
        seed_regions(self.db)

        with connect(self.db) as connection:
            connection.executemany(
                """
                INSERT INTO attack_events (
                    event_id, time_start, weapon_model, weapon_category,
                    source_name, source_snapshot
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                [
                    ("e1", "2026-01-01", "A", "UAV", "test", "snapshot"),
                    ("e2", "2026-01-02", "B", "UAV", "test", "snapshot"),
                    ("e3", "2026-01-03", "C", "UAV", "test", "snapshot"),
                ],
            )
            connection.execute(
                """
                INSERT INTO attack_event_regions (
                    event_id, region_code, relation_type,
                    attribution_method, attribution_quality
                )
                VALUES (
                    'e1', 'kyiv_oblast', 'target',
                    'parsed', 'medium'
                );
                """
            )
            connection.execute(
                """
                INSERT INTO dataset_builds (
                    build_id, source_name, source_snapshot,
                    transformation_version, rows_loaded
                )
                VALUES ('quality-build', 'test', 'snapshot', 'test-v1', 3);
                """
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_medium_only_regional_labels_are_blocked(self) -> None:
        gate = build_ml_quality_gate(self.db)

        self.assertEqual(
            gate["national_daily_historical_backtest"]["status"],
            "allowed",
        )
        self.assertEqual(
            gate["oblast_level_training"]["status"],
            "blocked_medium_confidence_only",
        )
        self.assertEqual(
            gate["oblast_level_training"]["events_with_high_confidence_region"],
            0,
        )
        self.assertEqual(
            gate["oblast_level_training"]["events_with_medium_confidence_region"],
            1,
        )
        self.assertEqual(
            gate["oblast_level_training"]["region_link_coverage_pct"],
            33.33,
        )


if __name__ == "__main__":
    unittest.main()