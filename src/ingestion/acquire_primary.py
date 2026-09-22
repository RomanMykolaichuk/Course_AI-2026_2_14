from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import kagglehub

from src.db.connection import PROJECT_ROOT


DATASET_HANDLE = "piterfm/massive-missile-attacks-on-ukraine"
SOURCE_URL = "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine"
LICENSE = "CC BY-NC-SA 4.0"
FILES = ("missile_attacks_daily.csv", "missiles_and_uavs.csv")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _copy_required_files(source_dir: Path, destination: Path) -> list[Path]:
    copied: list[Path] = []
    for filename in FILES:
        source = source_dir / filename
        if not source.exists():
            raise FileNotFoundError(f"Required dataset file not found: {source}")
        target = destination / filename
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def acquire_snapshot(
    output_root: str | Path | None = None,
    from_dir: str | Path | None = None,
    snapshot_date: str | None = None,
    force: bool = False,
) -> Path:
    """Acquire a dated immutable snapshot of the primary Kaggle dataset."""
    date_label = snapshot_date or datetime.now(timezone.utc).date().isoformat()
    root = Path(output_root) if output_root else PROJECT_ROOT / "data" / "raw"
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    snapshot_dir = root / "piterfm_massive_missile_attacks" / date_label
    if snapshot_dir.exists():
        if not force:
            raise FileExistsError(
                f"Snapshot already exists: {snapshot_dir}. Use --force to replace it."
            )
        shutil.rmtree(snapshot_dir)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    acquired_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if from_dir:
        source_dir = Path(from_dir).expanduser().resolve()
        acquisition_method = f"local_copy:{source_dir}"
        copied = _copy_required_files(source_dir, snapshot_dir)
    else:
        acquisition_method = "kagglehub.dataset_download"
        with tempfile.TemporaryDirectory(prefix="course_ai_kaggle_") as temp:
            download_dir = Path(temp)
            kagglehub.dataset_download(
                DATASET_HANDLE,
                output_dir=str(download_dir),
                force_download=force,
            )
            copied = _copy_required_files(download_dir, snapshot_dir)

    file_metadata = []
    for path in copied:
        metadata = {
            "filename": path.name,
            "sha256": sha256_file(path),
            "rows": csv_row_count(path),
            "bytes": path.stat().st_size,
        }
        file_metadata.append(metadata)

        sidecar = {
            "source_name": "Massive Missile Attacks on Ukraine",
            "dataset_handle": DATASET_HANDLE,
            "source_url": SOURCE_URL,
            "source_version": "latest_at_acquisition",
            "acquired_at": acquired_at,
            "license": LICENSE,
            "acquisition": acquisition_method,
            **metadata,
        }
        (path.with_suffix(path.suffix + ".meta.json")).write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "source_name": "Massive Missile Attacks on Ukraine",
        "dataset_handle": DATASET_HANDLE,
        "source_url": SOURCE_URL,
        "source_version": "latest_at_acquisition",
        "snapshot_date": date_label,
        "acquired_at": acquired_at,
        "license": LICENSE,
        "acquisition": acquisition_method,
        "files": file_metadata,
    }
    (snapshot_dir / "snapshot.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return snapshot_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire an immutable snapshot of the primary Kaggle dataset."
    )
    parser.add_argument("--output-root", default=None)
    parser.add_argument(
        "--from-dir",
        default=None,
        help="Use an already-downloaded directory instead of KaggleHub.",
    )
    parser.add_argument("--snapshot-date", default=None, help="YYYY-MM-DD label.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    snapshot = acquire_snapshot(
        output_root=args.output_root,
        from_dir=args.from_dir,
        snapshot_date=args.snapshot_date,
        force=args.force,
    )
    print(f"Snapshot created: {snapshot}")


if __name__ == "__main__":
    main()
