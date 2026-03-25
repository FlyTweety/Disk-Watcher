"""JSON file storage module for scan results."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator


def init_db(db_path: str = "disk_watcher.db") -> None:
    """Create scans directory if it doesn't exist."""
    scans_dir = Path(db_path).parent / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)


def make_scan_id(scanned_at: datetime | None = None) -> str:
    """Generate a unique scan ID based on timestamp (minute precision)."""
    if scanned_at is None:
        scanned_at = datetime.now()
    return scanned_at.strftime("%Y-%m-%d-%H%M")


def save_scan(
    db_path: str,
    root_path: str,
    scan_data: Iterator[tuple[str, int]],
    scanned_at: datetime | None = None,
) -> str:
    """Save a scan result to a JSON file. Returns the scan_id."""
    if scanned_at is None:
        scanned_at = datetime.now()

    scan_id = make_scan_id(scanned_at)
    scans_dir = Path(db_path).parent / "scans"
    scan_file = scans_dir / f"{scan_id}.json"

    # Collect all data
    data_list = [{"path": path, "size": size} for path, size in scan_data]

    scan_record = {
        "scan_id": scan_id,
        "root_path": root_path,
        "scanned_at": scanned_at.isoformat(),
        "data": data_list,
    }

    with open(scan_file, "w", encoding="utf-8") as f:
        json.dump(scan_record, f, indent=2, ensure_ascii=False)

    return scan_id


def get_scan_data(db_path: str, scan_id: str) -> dict[str, int]:
    """Get all scan data for a specific scan_id as a dict of path -> size."""
    scans_dir = Path(db_path).parent / "scans"
    scan_file = scans_dir / f"{scan_id}.json"

    if not scan_file.exists():
        return {}

    with open(scan_file, encoding="utf-8") as f:
        scan_record = json.load(f)

    return {item["path"]: item["size"] for item in scan_record["data"]}


def get_scan_by_time(db_path: str, target_time: datetime) -> str | None:
    """Get the scan_id closest to but not after the target time."""
    scans = get_available_scans(db_path)
    for scan_id, dt in scans:
        if dt <= target_time:
            return scan_id
    return None


def get_available_scans(db_path: str) -> list[tuple[str, datetime]]:
    """Get all unique scans with their timestamps, sorted newest first."""
    scans_dir = Path(db_path).parent / "scans"

    if not scans_dir.exists():
        return []

    scans = []
    for scan_file in scans_dir.glob("*.json"):
        with open(scan_file, encoding="utf-8") as f:
            scan_record = json.load(f)
        scan_id = scan_record["scan_id"]
        scanned_at = datetime.fromisoformat(scan_record["scanned_at"])
        scans.append((scan_id, scanned_at))

    scans.sort(key=lambda x: x[1], reverse=True)
    return scans


def delete_scan(db_path: str, scan_id: str) -> None:
    """Delete a specific scan."""
    scans_dir = Path(db_path).parent / "scans"
    scan_file = scans_dir / f"{scan_id}.json"
    if scan_file.exists():
        scan_file.unlink()
