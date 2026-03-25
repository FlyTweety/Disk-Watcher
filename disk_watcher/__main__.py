"""Disk Watcher CLI."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .scanner import scan_directory, format_size
from .storage import init_db, save_scan, get_available_scans
from .reporter import generate_report, list_scans


def format_tree(scan_data: list[tuple[str, int]], root_path: str, top_n: int = 20, min_size_mb: int = 1) -> str:
    """Format scan data as a tree structure with aligned sizes."""
    if not scan_data:
        return "无数据"

    # Filter by min size
    min_size_bytes = min_size_mb * 1024 * 1024
    filtered = [(p, s) for p, s in scan_data if s >= min_size_bytes]
    if not filtered:
        return "无数据"

    # Sort by size descending for top N
    by_size = sorted(filtered, key=lambda x: -x[1])[:top_n]

    def get_parent(path: str) -> str:
        return str(Path(path).parent)

    # Build a tree: parent -> list of children
    children: dict[str, list[tuple[str, int]]] = {}
    for path, size in by_size:
        parent = get_parent(path)
        if parent not in children:
            children[parent] = []
        children[parent].append((path, size))

    # Sort children by size descending
    for parent in children:
        children[parent].sort(key=lambda x: -x[1])

    size_col = 70

    lines = []

    def print_node(path: str, size: int, prefix: str, is_last: bool, is_root: bool = False):
        name = path.split("/")[-1]
        size_str = format_size(size)

        if is_root:
            lines.append(f"{name:<{size_col - len(size_str)}}{size_str}")
        else:
            tree_char = "└── " if is_last else "├── "
            lines.append(f"{prefix}{tree_char}{name:<{size_col - len(prefix) - len(tree_char) - len(size_str)}}{size_str}")

        if path not in children:
            return

        child_items = children[path]
        for i, (child_path, child_size) in enumerate(child_items):
            is_child_last = (i == len(child_items) - 1)
            extension = "    " if is_child_last else "│   "
            print_node(child_path, child_size, prefix + extension, is_child_last)

    # Start from root
    root_size = next((s for p, s in by_size if p == root_path), 0)
    lines.append(f"{root_path:<{size_col - len(format_size(root_size))}}{format_size(root_size)}")

    if root_path in children:
        child_items = children[root_path]
        for i, (child_path, child_size) in enumerate(child_items):
            is_last = (i == len(child_items) - 1)
            print_node(child_path, child_size, "", is_last)

    return "\n".join(lines)


def cmd_scan(args: argparse.Namespace) -> None:
    """Run a directory scan."""
    init_db(args.db)

    scanned_at = datetime.fromisoformat(args.time) if args.time else datetime.now()

    print(f"扫描目录: {args.path}")
    print(f"时间: {scanned_at.strftime('%Y-%m-%d %H:%M')}")
    if args.max_depth > 0:
        print(f"最大深度: {args.max_depth}")
    print()

    spin_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    last_update = [0]

    def progress(completed: int, total: int):
        if completed - last_update[0] >= 10:
            last_update[0] = completed
            spin_idx = (completed - 1) % len(spin_chars)
            print(f"\r  {spin_chars[spin_idx]} 正在扫描... {completed} 个目录", end="", flush=True)

    scan_data = list(scan_directory(args.path, max_depth=args.max_depth, progress_callback=progress))

    print(f"\r  ✓ 扫描完成! 共 {len(scan_data)} 个目录")
    scan_id = save_scan(args.db, str(args.path), scan_data, scanned_at)

    print(f"扫描ID: {scan_id}")
    print()
    print(format_tree(scan_data, str(args.path), top_n=args.top, min_size_mb=args.min_size))


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a comparison report."""
    init_db(args.db)

    available = get_available_scans(args.db)
    if not available:
        print("No scan data available. Run 'disk-watcher scan' first.")
        return

    target_scan_id = args.to or args.from_date or available[0][0]
    compare_scan_id = args.from_date if args.to else None

    result = generate_report(
        args.db,
        target_scan_id=target_scan_id,
        compare_scan_id=compare_scan_id,
        root_path=args.path,
        top_n=args.top,
        min_change_mb=args.min_change,
    )
    print(result)


def cmd_list(args: argparse.Namespace) -> None:
    """List available scans."""
    init_db(args.db)
    print(list_scans(args.db))


def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a specific scan."""
    from .storage import delete_scan

    init_db(args.db)

    available = get_available_scans(args.db)
    available_ids = [sid for sid, _ in available]

    if args.scan_id not in available_ids:
        print(f"Scan {args.scan_id} not found.")
        sys.exit(1)

    delete_scan(args.db, args.scan_id)
    print(f"已删除扫描: {args.scan_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="disk-watcher",
        description="Disk Watcher - 监控磁盘空间变化",
    )
    parser.add_argument("--db", default="disk_watcher.db", help="数据库路径 (默认: disk_watcher.db)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_parser = subparsers.add_parser("scan", help="扫描目录")
    scan_parser.add_argument("path", help="要扫描的目录路径")
    scan_parser.add_argument("--time", help="扫描时间 (YYYY-MM-DD-HHMM)")
    scan_parser.add_argument("--top", type=int, default=20, help="显示前N个目录 (默认: 20)")
    scan_parser.add_argument("--min-size", type=int, default=1, help="最小大小 MB (默认: 1)")
    scan_parser.add_argument("--max-depth", type=int, default=3, help="最大扫描深度 (默认: 3)")

    # report
    report_parser = subparsers.add_parser("report", help="生成对比报告")
    report_parser.add_argument("--from", dest="from_date", help="起始scan_id")
    report_parser.add_argument("--to", help="结束scan_id")
    report_parser.add_argument("--path", help="只显示此路径下的变化")
    report_parser.add_argument("--top", type=int, default=10, help="显示前N条 (默认: 10)")
    report_parser.add_argument("--min-change", type=int, default=1, help="最小变化 MB (默认: 1)")

    # list
    subparsers.add_parser("list", help="列出可用记录")

    # delete
    delete_parser = subparsers.add_parser("delete", help="删除某次扫描")
    delete_parser.add_argument("scan_id", help="要删除的scan_id")

    args = parser.parse_args()

    {
        "scan": cmd_scan,
        "report": cmd_report,
        "list": cmd_list,
        "delete": cmd_delete,
    }[args.command](args)


if __name__ == "__main__":
    main()
