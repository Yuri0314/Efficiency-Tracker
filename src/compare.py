"""
Trend Comparison Module.

This module handles comparing statistics between different time periods
to identify trends and changes in work patterns.
"""

from __future__ import annotations

from typing import Any


def calculate_change(current: float, previous: float) -> dict[str, Any]:
    """
    Calculate the change between two values.

    Args:
        current: The current period value.
        previous: The previous period value.

    Returns:
        A dictionary containing:
            - current: The current value
            - previous: The previous value
            - diff: The absolute difference
            - percent: The percentage change (None if previous is 0)
            - direction: "up", "down", or "same"
    """
    diff = current - previous

    if previous == 0:
        percent = None
        direction = "up" if current > 0 else "same"
    else:
        percent = round((diff / previous) * 100, 1)
        if abs(percent) < 1:
            direction = "same"
        elif diff > 0:
            direction = "up"
        else:
            direction = "down"

    return {
        "current": current,
        "previous": previous,
        "diff": round(diff, 1),
        "percent": percent,
        "direction": direction,
    }


def compare_stats(
    current_stats: dict[str, Any],
    previous_stats: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare statistics between current and previous periods.

    Args:
        current_stats: Statistics from the current period.
        previous_stats: Statistics from the previous period.

    Returns:
        A dictionary containing comparison results for key metrics.
    """
    comparison = {
        "total_hours": calculate_change(
            current_stats["total_hours"],
            previous_stats["total_hours"],
        ),
        "not_afk_hours": calculate_change(
            current_stats["not_afk_hours"],
            previous_stats["not_afk_hours"],
        ),
        "editor_hours": calculate_change(
            current_stats["editor"]["total_hours"],
            previous_stats["editor"]["total_hours"],
        ),
        "browser_hours": calculate_change(
            current_stats["browser"]["total_hours"],
            previous_stats["browser"]["total_hours"],
        ),
    }

    # Calculate activity rate change
    current_rate = (
        current_stats["not_afk_hours"] / current_stats["total_hours"] * 100
        if current_stats["total_hours"] > 0 else 0
    )
    previous_rate = (
        previous_stats["not_afk_hours"] / previous_stats["total_hours"] * 100
        if previous_stats["total_hours"] > 0 else 0
    )
    comparison["activity_rate"] = calculate_change(
        round(current_rate, 1),
        round(previous_rate, 1),
    )

    # Compare top apps
    current_apps = {app: hours for app, hours in current_stats["by_app"]}
    previous_apps = {app: hours for app, hours in previous_stats["by_app"]}

    app_changes = []
    for app, current_hours in current_apps.items():
        previous_hours = previous_apps.get(app, 0)
        if current_hours >= 0.5 or previous_hours >= 0.5:  # Only significant apps
            change = calculate_change(current_hours, previous_hours)
            change["app"] = app
            app_changes.append(change)

    # Sort by absolute difference
    app_changes.sort(key=lambda x: abs(x["diff"]), reverse=True)
    comparison["top_app_changes"] = app_changes[:5]

    # Count switches from hourly data if available
    current_switches = _count_total_switches(current_stats)
    previous_switches = _count_total_switches(previous_stats)
    if current_switches is not None and previous_switches is not None:
        comparison["total_switches"] = calculate_change(
            current_switches,
            previous_switches,
        )

    return comparison


def _count_total_switches(stats: dict[str, Any]) -> int | None:
    """
    Count total switches from hourly switches view.

    Args:
        stats: The statistics dictionary containing views.

    Returns:
        Total switch count, or None if data not available.
    """
    views = stats.get("views", {})
    hourly_switches = views.get("hourly_switches", "")

    if not hourly_switches or hourly_switches.startswith("（"):
        return None

    total = 0
    for line in hourly_switches.split("\n"):
        # Format: "09:00: 3次" or "10:00: 8次 ← 切换频繁"
        if "次" in line:
            try:
                count_str = line.split(":")[1].split("次")[0].strip()
                total += int(count_str)
            except (IndexError, ValueError):
                continue

    return total if total > 0 else None


def format_comparison_for_prompt(
    comparison: dict[str, Any],
    period_name: str,
) -> str:
    """
    Format comparison results for inclusion in AI prompt.

    Args:
        comparison: The comparison results from compare_stats.
        period_name: The period name (e.g., "日报", "周报").

    Returns:
        A formatted string describing the trends.
    """
    if period_name == "日报":
        prev_period = "昨天"
    else:
        prev_period = "上周"

    lines = [f"## 与{prev_period}对比"]

    # Activity hours
    afk = comparison["not_afk_hours"]
    lines.append(
        f"- 活跃时长: {afk['current']}h vs {afk['previous']}h "
        f"({_format_change(afk)})"
    )

    # Activity rate
    rate = comparison["activity_rate"]
    lines.append(
        f"- 活跃率: {rate['current']}% vs {rate['previous']}% "
        f"({_format_change(rate)})"
    )

    # Editor hours
    editor = comparison["editor_hours"]
    lines.append(
        f"- 编程时长: {editor['current']}h vs {editor['previous']}h "
        f"({_format_change(editor)})"
    )

    # Switches if available
    if "total_switches" in comparison:
        switches = comparison["total_switches"]
        lines.append(
            f"- 总切换次数: {int(switches['current'])}次 vs {int(switches['previous'])}次 "
            f"({_format_change(switches)})"
        )

    # Top app changes
    if comparison.get("top_app_changes"):
        lines.append("")
        lines.append("主要应用变化:")
        for change in comparison["top_app_changes"][:3]:
            if abs(change["diff"]) >= 0.3:  # Only show meaningful changes
                lines.append(
                    f"- {change['app']}: {change['current']}h vs {change['previous']}h "
                    f"({_format_change(change)})"
                )

    return "\n".join(lines)


def _format_change(change: dict[str, Any]) -> str:
    """
    Format a change dictionary as a human-readable string.

    Args:
        change: A change dictionary from calculate_change.

    Returns:
        A formatted string like "+15.2%" or "-3次".
    """
    if change["direction"] == "same":
        return "持平"

    sign = "+" if change["direction"] == "up" else ""

    if change["percent"] is not None:
        return f"{sign}{change['percent']}%"
    else:
        return f"{sign}{change['diff']}"
