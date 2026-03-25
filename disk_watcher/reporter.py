"""Report generation module."""
from __future__ import annotations

from typing import Optional

from .scanner import format_size
from .storage import get_scan_data, get_available_scans


def generate_report(
    db_path: str,
    target_scan_id: str,
    compare_scan_id: str | None = None,
    root_path: Optional[str] = None,
    top_n: int = 10,
    min_change_mb: int = 1,
) -> str:
    """
    Generate a comparison report between two scans.
    """
    available = get_available_scans(db_path)
    if not available:
        return "No scan data available. Run 'disk-watcher scan' first."

    available_ids = [sid for sid, _ in available]

    if target_scan_id not in available_ids:
        return f"Scan {target_scan_id} not found. Use 'disk-watcher list' to see available scans."

    recent_data = get_scan_data(db_path, target_scan_id)

    if compare_scan_id is None:
        idx = available_ids.index(target_scan_id)
        if idx + 1 >= len(available_ids):
            return f"No previous scan to compare with for {target_scan_id}."
        compare_scan_id = available_ids[idx + 1]

    if compare_scan_id not in available_ids:
        return f"Scan {compare_scan_id} not found. Available: {', '.join(available_ids)}"

    old_data = get_scan_data(db_path, compare_scan_id)

    target_time = dict(available).get(target_scan_id)
    compare_time = dict(available).get(compare_scan_id)

    changes = []
    for path, new_size in recent_data.items():
        if root_path and not path.startswith(root_path):
            continue
        old_size = old_data.get(path, 0)
        change = new_size - old_size
        change_mb = change / (1024 * 1024)

        if abs(change_mb) >= min_change_mb or (path in old_data and old_size == 0 and new_size > 0):
            changes.append({
                "path": path,
                "old_size": old_size,
                "new_size": new_size,
                "change": change,
                "change_mb": change_mb,
            })

    new_dirs = [c for c in changes if c["old_size"] == 0 and c["new_size"] > 0]
    growing = sorted([c for c in changes if c["change"] > 0 and c["old_size"] > 0], key=lambda x: -x["change"])
    shrinking = sorted([c for c in changes if c["change"] < 0 and c["old_size"] > 0], key=lambda x: x["change"])

    lines = []

    # Header
    compare_str = compare_time.strftime("%Y-%m-%d %H:%M") if compare_time else compare_scan_id
    target_str = target_time.strftime("%Y-%m-%d %H:%M") if target_time else target_scan_id
    lines.append("")
    lines.append("  ╔══════════════════════════════════════════════════════════╗")
    lines.append("  ║           📊 磁盘空间变化报告                            ║")
    lines.append(f"  ║  {compare_str} → {target_str}            ║")
    lines.append("  ╚══════════════════════════════════════════════════════════╝")
    lines.append("")

    # New directories
    if new_dirs:
        lines.append("🆕 新增目录")
        lines.append("─" * 64)
        for item in sorted(new_dirs, key=lambda x: -x["new_size"])[:top_n]:
            lines.append(f"  {item['path']}")
            lines.append(f"    └─ 0B → {format_size(item['new_size'])}")
        lines.append("")

    # Growing
    if growing:
        lines.append("📈 增长最多")
        lines.append("─" * 64)
        lines.append(f"  {'目录':<50} {'变化':>10}")
        lines.append("  " + "─" * 60)
        for item in growing[:top_n]:
            pct = (item["change"] / item["old_size"] * 100) if item["old_size"] > 0 else 100
            change_str = f"+{format_size(item['change'])} ({pct:.0f}%)"
            lines.append(f"  {item['path']:<50} {change_str:>10}")
        lines.append("")

    # Shrinking
    if shrinking:
        lines.append("📉 减少最多")
        lines.append("─" * 64)
        lines.append(f"  {'目录':<50} {'变化':>10}")
        lines.append("  " + "─" * 60)
        for item in shrinking[:top_n]:
            pct = (abs(item["change"]) / item["old_size"] * 100) if item["old_size"] > 0 else 100
            change_str = f"-{format_size(abs(item['change']))} ({pct:.0f}%)"
            lines.append(f"  {item['path']:<50} {change_str:>10}")
        lines.append("")

    if not changes:
        lines.append("无显著变化")

    return "\n".join(lines)


def list_scans(db_path: str) -> str:
    """List all available scans."""
    available = get_available_scans(db_path)
    if not available:
        return "No scan data available."
    lines = ["", "  ╔══════════════════════╦══════════════════════╗"]
    lines.append("  ║ scan_id             ║ 时间                 ║")
    lines.append("  ╠══════════════════════╬══════════════════════╣")
    for scan_id, dt in available:
        lines.append(f"  ║ {scan_id:<18} ║ {dt.strftime('%Y-%m-%d %H:%M'):<18} ║")
    lines.append("  ╚══════════════════════╩══════════════════════╝")
    return "\n".join(lines)
