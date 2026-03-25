#!/usr/bin/env python3
"""Generate mock scan data for testing."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

from disk_watcher import init_db, save_scan


def generate_mock_data(root_path: str, day_offset: int, variation: float = 0.0) -> list[tuple[str, int]]:
    """Generate mock directory sizes for testing."""
    base_sizes = {
        f"{root_path}": 50000,
        f"{root_path}/home": 30000,
        f"{root_path}/home/zcy": 20000,
        f"{root_path}/home/zcy/Downloads": 8000,
        f"{root_path}/home/zcy/Downloads/movies": 5000,
        f"{root_path}/home/zcy/Downloads/documents": 500,
        f"{root_path}/home/zcy/Downloads/temp": 200,
        f"{root_path}/home/zcy/Projects": 5000,
        f"{root_path}/home/zcy/Projects/project-a": 3000,
        f"{root_path}/home/zcy/Projects/project-a/src": 500,
        f"{root_path}/home/zcy/Projects/project-a/node_modules": 2000,
        f"{root_path}/home/zcy/Projects/project-b": 2000,
        f"{root_path}/home/zcy/.cache": 3000,
        f"{root_path}/home/zcy/.cache/pip": 1500,
        f"{root_path}/home/zcy/.cache/npm": 1200,
        f"{root_path}/home/zcy/.local": 2000,
        f"{root_path}/home/zcy/.local/share": 1800,
        f"{root_path}/var": 15000,
        f"{root_path}/var/log": 500,
        f"{root_path}/var/cache": 3000,
        f"{root_path}/var/cache/apt": 2500,
        f"{root_path}/usr": 10000,
        f"{root_path}/usr/lib": 8000,
        f"{root_path}/opt": 5000,
    }

    result = []
    for path, base_size in base_sizes.items():
        var = random.uniform(0.95, 1.05) + variation
        size_mb = int(base_size * var)
        # Simulate growth over time
        if day_offset > 0 and ("Downloads" in path or "cache" in path):
            size_mb = int(size_mb * (1 + day_offset * 0.03))
        result.append((path, size_mb * 1024 * 1024))

    return result


def main() -> None:
    db_path = "disk_watcher.db"
    root_path = "/mnt/data"
    init_db(db_path)

    # Clean old scans
    scans_dir = Path(db_path).parent / "scans"
    if scans_dir.exists():
        for f in scans_dir.glob("*.json"):
            f.unlink()

    today = datetime.now()
    print(f"生成模拟数据: {root_path}")
    print(f"日期范围: {(today - timedelta(days=6)).strftime('%Y-%m-%d')} 到 {today.strftime('%Y-%m-%d')}")
    print()

    for day_offset in range(7):
        base_date = today - timedelta(days=6 - day_offset)

        # Morning scan (smaller growth)
        morning = base_date.replace(hour=8, minute=0, second=0)
        print(f"{morning.strftime('%Y-%m-%d %H:%M')}...", end=" ", flush=True)
        data = generate_mock_data(root_path, day_offset, variation=0.0)
        scan_id = save_scan(db_path, root_path, iter(data), morning)
        print(scan_id)

        # Evening scan (bigger growth)
        evening = base_date.replace(hour=18, minute=30, second=0)
        print(f"{evening.strftime('%Y-%m-%d %H:%M')}...", end=" ", flush=True)
        data = generate_mock_data(root_path, day_offset, variation=0.05)
        scan_id = save_scan(db_path, root_path, iter(data), evening)
        print(scan_id)
        print()

    print("模拟数据生成完成!")


if __name__ == "__main__":
    main()
