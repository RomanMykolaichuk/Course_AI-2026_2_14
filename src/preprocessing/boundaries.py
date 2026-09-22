from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from src.db.connection import PROJECT_ROOT


DEFAULT_ROOT = PROJECT_ROOT / "data" / "external" / "geoboundaries"


GIS_ALIASES: dict[str, str] = {
    "vinnytsia": "vinnytsia_oblast",
    "vinnytska": "vinnytsia_oblast",
    "вінницька": "vinnytsia_oblast",
    "volyn": "volyn_oblast",
    "volynska": "volyn_oblast",
    "волинська": "volyn_oblast",
    "dnipropetrovsk": "dnipropetrovsk_oblast",
    "dnipropetrovska": "dnipropetrovsk_oblast",
    "дніпропетровська": "dnipropetrovsk_oblast",
    "donetsk": "donetsk_oblast",
    "donetska": "donetsk_oblast",
    "донецька": "donetsk_oblast",
    "zhytomyr": "zhytomyr_oblast",
    "zhytomyrska": "zhytomyr_oblast",
    "житомирська": "zhytomyr_oblast",
    "zakarpattia": "zakarpattia_oblast",
    "zakarpatska": "zakarpattia_oblast",
    "transcarpathia": "zakarpattia_oblast",
    "закарпатська": "zakarpattia_oblast",
    "zaporizhzhia": "zaporizhzhia_oblast",
    "zaporizhia": "zaporizhzhia_oblast",
    "zaporizka": "zaporizhzhia_oblast",
    "запорізька": "zaporizhzhia_oblast",
    "ivano frankivsk": "ivano_frankivsk_oblast",
    "ivano frankivska": "ivano_frankivsk_oblast",
    "івано франківська": "ivano_frankivsk_oblast",
    "kyivska": "kyiv_oblast",
    "kievska": "kyiv_oblast",
    "київська": "kyiv_oblast",
    "kirovohrad": "kirovohrad_oblast",
    "kirovohradska": "kirovohrad_oblast",
    "kirovograd": "kirovohrad_oblast",
    "кіровоградська": "kirovohrad_oblast",
    "luhansk": "luhansk_oblast",
    "luhanska": "luhansk_oblast",
    "lugansk": "luhansk_oblast",
    "луганська": "luhansk_oblast",
    "lviv": "lviv_oblast",
    "lvivska": "lviv_oblast",
    "львівська": "lviv_oblast",
    "mykolaiv": "mykolaiv_oblast",
    "mykolaivska": "mykolaiv_oblast",
    "nikolaev": "mykolaiv_oblast",
    "миколаївська": "mykolaiv_oblast",
    "odesa": "odesa_oblast",
    "odessa": "odesa_oblast",
    "odeska": "odesa_oblast",
    "одеська": "odesa_oblast",
    "poltava": "poltava_oblast",
    "poltavska": "poltava_oblast",
    "полтавська": "poltava_oblast",
    "rivne": "rivne_oblast",
    "rivnenska": "rivne_oblast",
    "rovno": "rivne_oblast",
    "рівненська": "rivne_oblast",
    "sumy": "sumy_oblast",
    "sumska": "sumy_oblast",
    "сумська": "sumy_oblast",
    "ternopil": "ternopil_oblast",
    "ternopilska": "ternopil_oblast",
    "тернопільська": "ternopil_oblast",
    "kharkiv": "kharkiv_oblast",
    "kharkivska": "kharkiv_oblast",
    "kharkov": "kharkiv_oblast",
    "харківська": "kharkiv_oblast",
    "kherson": "kherson_oblast",
    "khersonska": "kherson_oblast",
    "херсонська": "kherson_oblast",
    "khmelnytskyi": "khmelnytskyi_oblast",
    "khmelnytska": "khmelnytskyi_oblast",
    "khmelnitsky": "khmelnytskyi_oblast",
    "хмельницька": "khmelnytskyi_oblast",
    "cherkasy": "cherkasy_oblast",
    "cherkaska": "cherkasy_oblast",
    "черкаська": "cherkasy_oblast",
    "chernivtsi": "chernivtsi_oblast",
    "chernivetska": "chernivtsi_oblast",
    "чернівецька": "chernivtsi_oblast",
    "chernihiv": "chernihiv_oblast",
    "chernihivska": "chernihiv_oblast",
    "chernigov": "chernihiv_oblast",
    "чернігівська": "chernihiv_oblast",
    "autonomous republic of crimea": "crimea",
    "avtonomna respublika krym": "crimea",
    "crimea": "crimea",
    "крим": "crimea",
    "автономна республіка крим": "crimea",
    "kyiv": "kyiv_city",
    "kiev": "kyiv_city",
    "київ": "kyiv_city",
    "sevastopol": "sevastopol_city",
    "севастополь": "sevastopol_city",
}


def normalize_boundary_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).lower()
    text = (
        text.replace("’", "")
        .replace("'", "")
        .replace("ʻ", "")
        .replace("-", " ")
        .replace("_", " ")
    )
    text = re.sub(r"\b(oblast|region|city|misto|місто|область)\b", " ", text)
    text = re.sub(r"[^0-9a-zа-яіїєґ\s]+", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def match_boundary_region_code(name: object) -> str | None:
    if name is None:
        return None
    normalized = normalize_boundary_name(str(name))
    return GIS_ALIASES.get(normalized)


def _latest_snapshot(root: Path = DEFAULT_ROOT) -> Path:
    snapshots = sorted(
        (path for path in root.glob("UKR-ADM1-*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
    )
    if not snapshots:
        raise FileNotFoundError(
            "No geoBoundaries UKR ADM1 snapshot found. "
            "Run: python -m src.ingestion.acquire_boundaries"
        )
    return snapshots[-1]


def load_boundary_snapshot(
    snapshot_dir: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = Path(snapshot_dir).resolve() if snapshot_dir else _latest_snapshot()
    geojson_path = snapshot / "UKR_ADM1.geojson"
    metadata_path = snapshot / "metadata.json"

    geometry = json.loads(geojson_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return geometry, metadata


def canonicalize_boundaries(
    geometry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Attach canonical region_code to every resolvable ADM1 feature."""
    output = {
        "type": "FeatureCollection",
        "features": [],
    }
    seen_codes: set[str] = set()
    unmapped_names: list[str] = []
    duplicates: list[str] = []

    for feature in geometry.get("features", []):
        properties = dict(feature.get("properties") or {})
        shape_name = (
            properties.get("shapeName")
            or properties.get("name")
            or properties.get("NAME_1")
        )
        region_code = match_boundary_region_code(shape_name)

        if region_code is None:
            unmapped_names.append(str(shape_name))
        elif region_code in seen_codes:
            duplicates.append(region_code)
        else:
            seen_codes.add(region_code)

        properties["region_code"] = region_code
        output["features"].append(
            {
                **feature,
                "properties": properties,
            }
        )

    report = {
        "feature_count": len(output["features"]),
        "mapped_count": sum(
            1
            for feature in output["features"]
            if feature["properties"].get("region_code")
        ),
        "unmapped_names": sorted(set(unmapped_names)),
        "duplicate_region_codes": sorted(set(duplicates)),
        "mapped_region_codes": sorted(seen_codes),
    }
    return output, report
