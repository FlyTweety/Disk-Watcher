"""Directory scanning module - recursively calculate directory sizes."""
from __future__ import annotations

import os
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator


def _scan_dir(dir_path: Path) -> tuple[Path, int, list[Path]]:
    """Scan a single directory, return (path, own_size, subdirs)."""
    total = 0
    subdirs = []
    try:
        with os.scandir(dir_path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        subdirs.append(Path(entry.path))
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return dir_path, total, subdirs


def scan_directory(
    root_path: str | Path,
    workers: int = 8,
    max_depth: int = 0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Iterator[tuple[str, int]]:
    """
    Scan a directory and yield (path, cumulative_size) for each directory.

    Args:
        root_path: Root directory to scan
        workers: Number of parallel threads (default: 8)
        max_depth: Maximum depth to scan, 0 means unlimited
        progress_callback: Optional callback(completed, total) for progress updates
    """
    root_path = Path(root_path).resolve()
    root_depth = len(root_path.parts)

    dir_own_size: dict[Path, int] = {}
    parent_to_children: dict[Path, list[Path]] = defaultdict(list)

    # Progress tracking
    completed = 0
    pending_lock = threading.Lock()
    pending_count = 1  # Start with root

    def on_done():
        nonlocal completed
        with pending_lock:
            completed += 1
            if progress_callback:
                progress_callback(completed, -1)  # -1 means unknown total

    # BFS with thread pool
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_scan_dir, root_path): root_path}

        while futures:
            done = set()
            for f in futures:
                if f.done():
                    done.add(f)
                    break

            for future in done:
                dir_path, own_size, subdirs = future.result()
                dir_own_size[dir_path] = own_size
                on_done()

                # Check depth limit
                current_depth = len(dir_path.parts) - root_depth
                if max_depth > 0 and current_depth >= max_depth:
                    subdirs = []

                with pending_lock:
                    for subdir in subdirs:
                        if subdir not in dir_own_size:
                            parent_to_children[dir_path].append(subdir)
                            futures[executor.submit(_scan_dir, subdir)] = subdir
                            pending_count += 1

                del futures[future]

    # Calculate cumulative sizes bottom-up
    all_dirs = list(dir_own_size.keys())
    all_dirs.sort(key=lambda p: -len(p.parts))

    dir_cumulative: dict[Path, int] = {}
    for dir_path in all_dirs:
        cumulative = dir_own_size.get(dir_path, 0)
        for child in parent_to_children.get(dir_path, []):
            if child in dir_cumulative:
                cumulative += dir_cumulative[child]
        dir_cumulative[dir_path] = cumulative

    for dir_path, size in sorted(dir_cumulative.items(), key=lambda x: -x[1]):
        yield str(dir_path), size


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}PB"
