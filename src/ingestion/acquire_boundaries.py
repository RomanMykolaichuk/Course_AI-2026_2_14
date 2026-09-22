from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.db.connection import PROJECT_ROOT


METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/UKR/ADM1/"
DEFAULT_ROOT = PROJECT_ROOT / "data" / "external" / "geoboundaries"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_json(url: str, timeout: int = 60) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _download_file(url: str, destination: Path, timeout: int = 120) -> None:
    with requests.get(url, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    stream.write(chunk)


def acquire_adm1(
    output_root: str | Path | None = None,
    force: bool = False,
    simplified: bool = True,
) -> Path:
    """Acquire a versioned geoBoundaries UKR ADM1 snapshot."""
    root = Path(output_root) if output_root else DEFAULT_ROOT
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    metadata = _download_json(METADATA_URL)
    boundary_id = str(metadata["boundaryID"]).strip()
    if not boundary_id:
        raise ValueError("geoBoundaries metadata did not include boundaryID")

    snapshot_dir = root / boundary_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    geometry_url = (
        metadata.get("simplifiedGeometryGeoJSON")
        if simplified
        else metadata.get("gjDownloadURL")
    )
    if not geometry_url:
        geometry_url = metadata.get("gjDownloadURL")
    if not geometry_url:
        raise ValueError("geoBoundaries metadata did not include a GeoJSON URL")

    geometry_path = snapshot_dir / "UKR_ADM1.geojson"
    metadata_path = snapshot_dir / "metadata.json"

    if geometry_path.exists() and metadata_path.exists() and not force:
        return snapshot_dir

    _download_file(str(geometry_url), geometry_path)

    acquired_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    snapshot_metadata = {
        **metadata,
        "metadataURL": METADATA_URL,
        "geometryURLUsed": geometry_url,
        "geometryVariant": "simplified" if simplified else "full",
        "acquiredAt": acquired_at,
        "geometrySHA256": sha256_file(geometry_path),
        "geometryBytes": geometry_path.stat().st_size,
    }
    metadata_path.write_text(
        json.dumps(snapshot_metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return snapshot_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire a versioned geoBoundaries UKR ADM1 snapshot."
    )
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Download full rather than simplified GeoJSON.",
    )
    args = parser.parse_args()

    snapshot = acquire_adm1(
        output_root=args.output_root,
        force=args.force,
        simplified=not args.full,
    )
    print(f"ADM1 snapshot ready: {snapshot}")


if __name__ == "__main__":
    main()
