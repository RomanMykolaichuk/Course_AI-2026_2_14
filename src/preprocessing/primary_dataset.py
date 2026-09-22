from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .regions import extract_region_codes


SOURCE_NAME = "kaggle:piterfm/massive-missile-attacks-on-ukraine"
SOURCE_PAGE = "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine"
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"https?://[^\s,;\]\[\)\(\"']+")

COUNT_FIELDS = (
    "launched",
    "destroyed",
    "not_reach_goal",
    "border_crossing",
    "still_attacking",
)


def _optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object, field: str, row_number: int) -> int | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    number = float(value)
    if not number.is_integer() or number < 0:
        raise ValueError(
            f"Row {row_number}: {field} must be a non-negative integer or null; got {value!r}"
        )
    return int(number)


def _normalize_time(value: object, row_number: int, field: str) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None

    if DATE_ONLY.fullmatch(text):
        return text

    try:
        timestamp = pd.Timestamp(text)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("Europe/Kyiv")
        timestamp = timestamp.tz_convert("UTC")
    except Exception as exc:
        raise ValueError(f"Row {row_number}: cannot parse {field}={text!r}") from exc

    return timestamp.isoformat().replace("+00:00", "Z")


def _first_url(value: object) -> str | None:
    text = _optional_text(value)
    if not text:
        return None
    match = URL_RE.search(text)
    return match.group(0) if match else None


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _weapon_categories(reference: pd.DataFrame) -> dict[str, str]:
    if "model" not in reference.columns or "category" not in reference.columns:
        return {}

    mapping: dict[str, str] = {}
    for _, row in reference[["model", "category"]].dropna(subset=["model"]).iterrows():
        model = str(row["model"]).strip()
        category = _optional_text(row["category"])
        if model and category and model not in mapping:
            mapping[model] = category
    return mapping


def transform_primary_dataset(
    attacks_csv: str | Path,
    weapons_csv: str | Path,
    source_snapshot: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Transform the primary source into canonical events and region links."""
    attacks_path = Path(attacks_csv)
    weapons_path = Path(weapons_csv)

    attacks = pd.read_csv(attacks_path)
    weapons = pd.read_csv(weapons_path)

    required = {"time_start", "model"}
    missing = sorted(required - set(attacks.columns))
    if missing:
        raise ValueError("Primary CSV is missing required columns: " + ", ".join(missing))

    categories = _weapon_categories(weapons)
    event_rows: list[dict[str, Any]] = []
    link_rows: list[dict[str, Any]] = []
    explicit_region_events = 0
    any_region_events = 0

    for index, row in attacks.iterrows():
        row_number = index + 2
        time_start = _normalize_time(row.get("time_start"), row_number, "time_start")
        if time_start is None:
            raise ValueError(f"Row {row_number}: time_start is required")

        time_end = _normalize_time(row.get("time_end"), row_number, "time_end")
        model = _optional_text(row.get("model"))
        launch_place = _optional_text(row.get("launch_place"))
        target_raw = _optional_text(row.get("target"))
        carrier = _optional_text(row.get("carrier"))

        key_payload = {
            "source": SOURCE_NAME,
            "time_start": _optional_text(row.get("time_start")),
            "time_end": _optional_text(row.get("time_end")),
            "model": model,
            "launch_place": launch_place,
            "target": target_raw,
            "carrier": carrier,
        }
        event_id = _stable_hash(key_payload)

        source_record_payload = {
            str(column): None if pd.isna(row[column]) else row[column]
            for column in attacks.columns
        }
        source_record_id = _stable_hash(source_record_payload)

        counts = {
            field: _optional_int(row.get(field), field, row_number)
            for field in COUNT_FIELDS
        }

        event_rows.append(
            {
                "event_id": event_id,
                "time_start": time_start,
                "time_end": time_end,
                "weapon_model": model,
                "weapon_category": categories.get(model) if model else None,
                "launch_place": launch_place,
                "target_raw": target_raw,
                "carrier": carrier,
                **counts,
                "source_name": SOURCE_NAME,
                "source_url": _first_url(row.get("source")) or SOURCE_PAGE,
                "source_record_id": source_record_id,
                "source_snapshot": source_snapshot,
            }
        )

        explicit_codes = extract_region_codes(row.get("affected_region"))
        target_codes = extract_region_codes(row.get("target"))

        if explicit_codes:
            explicit_region_events += 1

        seen: set[tuple[str, str]] = set()
        for region_code in explicit_codes:
            key = (region_code, "affected")
            if key not in seen:
                seen.add(key)
                link_rows.append(
                    {
                        "event_id": event_id,
                        "region_code": region_code,
                        "relation_type": "affected",
                        "attribution_method": "source_explicit_parsed",
                        "attribution_quality": "high",
                    }
                )

        for region_code in target_codes:
            key = (region_code, "target")
            if key not in seen:
                seen.add(key)
                link_rows.append(
                    {
                        "event_id": event_id,
                        "region_code": region_code,
                        "relation_type": "target",
                        "attribution_method": "parsed",
                        "attribution_quality": "medium",
                    }
                )

        if explicit_codes or target_codes:
            any_region_events += 1

    events = (
        pd.DataFrame(event_rows)
        .drop_duplicates(subset=["event_id"], keep="last")
        .reset_index(drop=True)
    )
    links = (
        pd.DataFrame(
            link_rows,
            columns=[
                "event_id",
                "region_code",
                "relation_type",
                "attribution_method",
                "attribution_quality",
            ],
        )
        .drop_duplicates(
            subset=["event_id", "region_code", "relation_type"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    stats = {
        "source_rows": int(len(attacks)),
        "events": int(len(events)),
        "region_links": int(len(links)),
        "events_with_explicit_regions": int(explicit_region_events),
        "events_with_any_region": int(any_region_events),
        "weapon_reference_rows": int(len(weapons)),
    }
    return events, links, stats