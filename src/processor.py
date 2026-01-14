"""
Data Processing Module.

This module handles AFK filtering, data aggregation, and statistics calculation
for ActivityWatch event data. It also generates behavior views for AI analysis.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

# =============================================================================
# Behavior View Builders (for AI Analysis)
# =============================================================================


def build_timeline_view(
    window_events: list[dict[str, Any]],
    browser_events: list[dict[str, Any]],
    min_duration_seconds: int = 60,
) -> str:
    """
    Build a human-readable timeline of application usage.

    Creates a chronological view of app switches with timestamps and durations,
    suitable for AI to analyze patterns and interruptions.

    Args:
        window_events: List of window events from ActivityWatch.
        browser_events: List of browser events for URL context.
        min_duration_seconds: Minimum event duration to include (filters noise).

    Returns:
        A formatted string showing the app usage timeline.

    Example output:
        09:00-09:47 VS Code (efficiency-tracker) [47min]
        09:47-09:52 Chrome (zhihu.com) [5min]
        09:52-10:30 VS Code (efficiency-tracker) [38min]
    """
    if not window_events:
        return "（无应用使用记录）"

    # Build a map of timestamp -> browser URL for context
    browser_context: dict[str, str] = {}
    for event in browser_events:
        ts = event.get("timestamp", "")
        url = event.get("data", {}).get("url", "")
        if ts and url:
            domain = extract_domain(url)
            browser_context[ts[:16]] = domain  # Use minute-level precision

    # Sort window events by timestamp
    sorted_events = sorted(
        window_events,
        key=lambda e: e.get("timestamp", ""),
    )

    lines: list[str] = []
    for event in sorted_events:
        duration = event.get("duration", 0)
        if duration < min_duration_seconds:
            continue

        start = parse_timestamp(event.get("timestamp", ""))
        if not start:
            continue

        end = start + timedelta(seconds=duration)
        app = event.get("data", {}).get("app", "Unknown")
        title = event.get("data", {}).get("title", "")

        # Format duration
        duration_min = int(duration / 60)
        if duration_min < 1:
            duration_str = f"{int(duration)}s"
        else:
            duration_str = f"{duration_min}min"

        # Add browser context for Chrome/Safari/Firefox
        context = ""
        if any(browser in app.lower() for browser in ["chrome", "safari", "firefox", "arc", "edge"]):
            # Try to find matching browser event
            ts_key = event.get("timestamp", "")[:16]
            if ts_key in browser_context:
                context = f" ({browser_context[ts_key]})"
            elif title:
                # Extract domain-like info from title
                context = f" ({title[:30]}...)" if len(title) > 30 else f" ({title})"

        line = f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')} {app}{context} [{duration_str}]"
        lines.append(line)

    if not lines:
        return "（无符合条件的应用使用记录）"

    return "\n".join(lines)


def build_session_view(
    window_events: list[dict[str, Any]],
    min_session_minutes: int = 10,
    merge_gap_seconds: int = 120,
) -> str:
    """
    Build a view of continuous usage sessions.

    Merges consecutive events of the same app into sessions, showing
    periods of focused work.

    Args:
        window_events: List of window events.
        min_session_minutes: Minimum session duration to include.
        merge_gap_seconds: Maximum gap between events to merge into same session.

    Returns:
        A formatted string showing continuous usage sessions.

    Example output:
        - VS Code: 47min (09:00-09:47)
        - VS Code: 38min (09:52-10:30)
        - Chrome: 35min (10:40-11:15)
    """
    if not window_events:
        return "（无连续使用记录）"

    # Sort by timestamp
    sorted_events = sorted(
        window_events,
        key=lambda e: e.get("timestamp", ""),
    )

    # Merge consecutive same-app events into sessions
    sessions: list[dict[str, Any]] = []
    current_session: dict[str, Any] | None = None

    for event in sorted_events:
        start = parse_timestamp(event.get("timestamp", ""))
        if not start:
            continue

        duration = event.get("duration", 0)
        end = start + timedelta(seconds=duration)
        app = event.get("data", {}).get("app", "Unknown")

        if current_session is None:
            current_session = {"app": app, "start": start, "end": end, "duration": duration}
        elif (
            app == current_session["app"]
            and (start - current_session["end"]).total_seconds() <= merge_gap_seconds
        ):
            # Extend current session
            current_session["end"] = max(current_session["end"], end)
            current_session["duration"] += duration
        else:
            # Save current session and start new one
            sessions.append(current_session)
            current_session = {"app": app, "start": start, "end": end, "duration": duration}

    if current_session:
        sessions.append(current_session)

    # Filter by minimum duration and format
    min_duration_seconds = min_session_minutes * 60
    lines: list[str] = []

    for session in sessions:
        if session["duration"] >= min_duration_seconds:
            duration_min = int(session["duration"] / 60)
            time_range = f"{session['start'].strftime('%H:%M')}-{session['end'].strftime('%H:%M')}"
            lines.append(f"- {session['app']}: {duration_min}min ({time_range})")

    if not lines:
        return f"（无超过 {min_session_minutes} 分钟的连续使用记录）"

    return "\n".join(lines)


def build_hourly_switches(
    window_events: list[dict[str, Any]],
) -> str:
    """
    Build a heatmap of context switches per hour.

    Counts how many times the active app changed in each hour,
    helping identify fragmented time periods.

    Args:
        window_events: List of window events.

    Returns:
        A formatted string showing switches per hour.

    Example output:
        09:00: 3次
        10:00: 8次 ← 切换频繁
        11:00: 2次
    """
    if len(window_events) < 2:
        return "（数据不足，无法分析切换频率）"

    # Sort by timestamp
    sorted_events = sorted(
        window_events,
        key=lambda e: e.get("timestamp", ""),
    )

    # Count switches per hour
    hourly_switches: dict[int, int] = defaultdict(int)
    prev_app: str | None = None

    for event in sorted_events:
        start = parse_timestamp(event.get("timestamp", ""))
        if not start:
            continue

        app = event.get("data", {}).get("app", "")
        if prev_app is not None and app != prev_app:
            hourly_switches[start.hour] += 1
        prev_app = app

    if not hourly_switches:
        return "（无应用切换记录）"

    # Find max for highlighting
    max_switches = max(hourly_switches.values()) if hourly_switches else 0

    # Format output
    lines: list[str] = []
    for hour in sorted(hourly_switches.keys()):
        count = hourly_switches[hour]
        highlight = " ← 切换频繁" if count == max_switches and count >= 5 else ""
        lines.append(f"{hour:02d}:00: {count}次{highlight}")

    return "\n".join(lines)


def build_website_summary(
    browser_events: list[dict[str, Any]],
    work_domains: list[str] | None = None,
) -> str:
    """
    Build a summary of website visits, categorized by work/other.

    Args:
        browser_events: List of browser events.
        work_domains: List of domains considered work-related.

    Returns:
        A formatted string showing website usage summary.

    Example output:
        工作相关:
        - alidocs.dingtalk.com: 45min
        - github.com: 20min

        其他:
        - zhihu.com: 25min
        - weibo.com: 10min
    """
    if not browser_events:
        return "（无浏览器使用记录）"

    if work_domains is None:
        work_domains = []

    # Aggregate time by domain
    domain_times: dict[str, float] = defaultdict(float)
    for event in browser_events:
        url = event.get("data", {}).get("url", "")
        duration = event.get("duration", 0)
        if url:
            domain = extract_domain(url)
            domain_times[domain] += duration

    if not domain_times:
        return "（无有效的网站访问记录）"

    # Categorize domains
    work_sites: list[tuple[str, float]] = []
    other_sites: list[tuple[str, float]] = []

    for domain, seconds in domain_times.items():
        is_work = any(wd.lower() in domain.lower() for wd in work_domains)
        if is_work:
            work_sites.append((domain, seconds))
        else:
            other_sites.append((domain, seconds))

    # Sort by duration descending
    work_sites.sort(key=lambda x: -x[1])
    other_sites.sort(key=lambda x: -x[1])

    lines: list[str] = []

    if work_sites:
        lines.append("工作相关:")
        for domain, seconds in work_sites[:5]:
            minutes = int(seconds / 60)
            lines.append(f"  - {domain}: {minutes}min")

    if other_sites:
        if lines:
            lines.append("")
        lines.append("其他:")
        for domain, seconds in other_sites[:10]:
            minutes = int(seconds / 60)
            if minutes >= 1:  # Only show if at least 1 minute
                lines.append(f"  - {domain}: {minutes}min")

    return "\n".join(lines) if lines else "（无有效的网站访问记录）"


def parse_timestamp(ts_str: str) -> datetime | None:
    """
    Parse an ISO format timestamp string and convert to local time.

    ActivityWatch stores timestamps in UTC. This function parses the timestamp
    and converts it to the local timezone for display.

    Args:
        ts_str: The timestamp string to parse (typically in UTC).

    Returns:
        A datetime object in local time if parsing succeeds, None otherwise.
    """
    from datetime import timezone

    formats_with_tz = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    formats_without_tz = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]

    # Try formats with timezone first
    for fmt in formats_with_tz:
        try:
            # Parse with timezone info
            dt_utc = datetime.strptime(ts_str, fmt)
            # Convert to local time
            dt_local = dt_utc.astimezone()
            # Return as naive datetime (without tzinfo) for compatibility
            return dt_local.replace(tzinfo=None)
        except ValueError:
            continue

    # Try formats without timezone (assume already local)
    for fmt in formats_without_tz:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue

    return None


def seconds_to_hours(seconds: float) -> float:
    """
    Convert seconds to hours, rounded to 1 decimal place.

    Args:
        seconds: The number of seconds.

    Returns:
        The equivalent number of hours.
    """
    return round(seconds / 3600, 1)


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url: The URL to parse.

    Returns:
        The domain name, or "unknown" if extraction fails.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "unknown"
    except Exception:
        return "unknown"


class AFKFilter:
    """
    Filter for removing events that occurred during AFK (Away From Keyboard) periods.

    This class analyzes AFK events to determine active periods and filters
    other events to only include those that overlap with active periods.

    Attributes:
        active_periods: List of (start, end) datetime tuples representing
            periods when the user was not AFK.
    """

    def __init__(self, afk_events: list[dict[str, Any]]) -> None:
        """
        Initialize the AFK filter.

        Args:
            afk_events: List of AFK events from ActivityWatch.
        """
        self.active_periods = self._get_not_afk_periods(afk_events)

    def _get_not_afk_periods(
        self,
        afk_events: list[dict[str, Any]],
    ) -> list[tuple[datetime, datetime]]:
        """
        Extract all non-AFK time periods from AFK events.

        Args:
            afk_events: List of AFK events.

        Returns:
            List of (start, end) tuples for active periods.
        """
        periods: list[tuple[datetime, datetime]] = []
        for event in afk_events:
            if event.get("data", {}).get("status") == "not-afk":
                start = parse_timestamp(event.get("timestamp", ""))
                duration = event.get("duration", 0)
                if start and duration > 0:
                    end = start + timedelta(seconds=duration)
                    periods.append((start, end))
        return periods

    def is_in_active_period(
        self,
        event_time: datetime,
        event_duration: float,
    ) -> bool:
        """
        Check if an event overlaps with any active period.

        Args:
            event_time: The start time of the event.
            event_duration: The duration of the event in seconds.

        Returns:
            True if the event overlaps with an active period, False otherwise.
            Returns True if no AFK data is available.
        """
        if not self.active_periods:
            return True  # No AFK data means we consider all events as active

        event_end = event_time + timedelta(seconds=event_duration)

        for period_start, period_end in self.active_periods:
            # Check for any overlap between event and active period
            if event_time < period_end and event_end > period_start:
                return True
        return False

    def filter_events(
        self,
        events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter events to only include those during active periods.

        Args:
            events: List of events to filter.

        Returns:
            Filtered list containing only events that overlap with active periods.
        """
        if not self.active_periods:
            return events

        filtered: list[dict[str, Any]] = []
        for event in events:
            event_time = parse_timestamp(event.get("timestamp", ""))
            event_duration = event.get("duration", 0)

            if event_time and self.is_in_active_period(event_time, event_duration):
                filtered.append(event)

        return filtered

    @staticmethod
    def get_total_active_seconds(afk_events: list[dict[str, Any]]) -> float:
        """
        Calculate total active (not-AFK) time in seconds.

        Args:
            afk_events: List of AFK events.

        Returns:
            Total seconds spent in not-AFK status.
        """
        return sum(
            e.get("duration", 0)
            for e in afk_events
            if e.get("data", {}).get("status") == "not-afk"
        )


class DataAggregator:
    """
    Aggregator for computing statistics from event data.

    This class provides methods for grouping and summing event durations
    by various categories like application, category, domain, etc.

    Attributes:
        categories: Dictionary mapping category names to lists of app name patterns.
    """

    def __init__(self, categories: dict[str, list[str]]) -> None:
        """
        Initialize the data aggregator.

        Args:
            categories: Dictionary mapping category names to app name patterns.
                Example: {"coding": ["VS Code", "PyCharm"], "browser": ["Chrome"]}
        """
        self.categories = categories

    def categorize_app(self, app_name: str) -> str:
        """
        Determine the category for an application.

        Args:
            app_name: The name of the application.

        Returns:
            The category name, or "other" if no match is found.
        """
        app_lower = app_name.lower()
        for category, apps in self.categories.items():
            for app in apps:
                if app.lower() in app_lower:
                    return category
        return "other"

    def aggregate_by_app(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Aggregate event durations by application name.

        Args:
            events: List of window events.

        Returns:
            Dictionary mapping app names to total duration in seconds.
        """
        app_times: dict[str, float] = defaultdict(float)
        for event in events:
            app = event.get("data", {}).get("app", "Unknown")
            duration = event.get("duration", 0)
            app_times[app] += duration
        return dict(app_times)

    def aggregate_by_category(
        self,
        app_times: dict[str, float],
    ) -> dict[str, float]:
        """
        Aggregate app times by category.

        Args:
            app_times: Dictionary mapping app names to durations.

        Returns:
            Dictionary mapping category names to total duration in seconds.
        """
        category_times: dict[str, float] = defaultdict(float)
        for app, seconds in app_times.items():
            category = self.categorize_app(app)
            category_times[category] += seconds
        return dict(category_times)

    def aggregate_browser_domains(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Aggregate browser event durations by domain.

        Args:
            events: List of browser events.

        Returns:
            Dictionary mapping domain names to total duration in seconds.
        """
        domain_times: dict[str, float] = defaultdict(float)
        for event in events:
            url = event.get("data", {}).get("url", "")
            duration = event.get("duration", 0)
            if url:
                domain = extract_domain(url)
                domain_times[domain] += duration
        return dict(domain_times)

    def aggregate_editor_stats(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """
        Aggregate editor event statistics by language and project.

        Args:
            events: List of editor events.

        Returns:
            Dictionary with "by_language" and "by_project" sub-dictionaries,
            each mapping names to total duration in seconds.
        """
        language_times: dict[str, float] = defaultdict(float)
        project_times: dict[str, float] = defaultdict(float)

        for event in events:
            data = event.get("data", {})
            duration = event.get("duration", 0)

            language = data.get("language", "unknown")
            project = data.get("project", "unknown")

            # Simplify project path to just the directory name
            if project and "/" in project:
                project = project.rstrip("/").split("/")[-1]

            language_times[language] += duration
            project_times[project] += duration

        return {
            "by_language": dict(language_times),
            "by_project": dict(project_times),
        }


class DataProcessor:
    """
    Main data processor that combines AFK filtering and data aggregation.

    This class provides a high-level interface for processing raw ActivityWatch
    data and producing comprehensive statistics.

    Attributes:
        aggregator: The DataAggregator instance used for aggregation.
    """

    def __init__(
        self,
        categories: dict[str, list[str]],
        work_domains: list[str] | None = None,
    ) -> None:
        """
        Initialize the data processor.

        Args:
            categories: Dictionary mapping category names to app name patterns.
            work_domains: List of domains considered work-related for website summary.
        """
        self.aggregator = DataAggregator(categories)
        self.work_domains = work_domains or []

    def process(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process raw event data and return comprehensive statistics.

        This method performs the following steps:
        1. Filter events by AFK status
        2. Calculate total active time
        3. Aggregate window events by app and category
        4. Aggregate browser events by domain
        5. Aggregate editor events by language and project

        Args:
            raw_data: Dictionary containing "window", "afk", "browser",
                and "editor" event lists.

        Returns:
            Dictionary containing processed statistics including:
                - total_hours: Total recorded time in hours
                - not_afk_hours: Active (non-AFK) time in hours
                - by_app: Top 10 apps by usage time
                - by_category: Usage time by category
                - browser: Browser statistics with top domains
                - editor: Editor statistics by language and project
                - event_counts: Raw event counts by type
        """
        window_events = raw_data.get("window", [])
        afk_events = raw_data.get("afk", [])
        browser_events = raw_data.get("browser", [])
        editor_events = raw_data.get("editor", [])

        # Step 1: AFK filtering
        afk_filter = AFKFilter(afk_events)
        filtered_window = afk_filter.filter_events(window_events)
        filtered_browser = afk_filter.filter_events(browser_events)
        filtered_editor = afk_filter.filter_events(editor_events)

        # Step 2: Calculate active time
        not_afk_seconds = AFKFilter.get_total_active_seconds(afk_events)

        # Step 3: Window data aggregation
        app_times = self.aggregator.aggregate_by_app(filtered_window)
        category_times = self.aggregator.aggregate_by_category(app_times)
        total_seconds = sum(app_times.values())

        app_times_sorted = sorted(app_times.items(), key=lambda x: -x[1])
        category_times_sorted = sorted(category_times.items(), key=lambda x: -x[1])

        # Step 4: Browser data aggregation
        domain_times = self.aggregator.aggregate_browser_domains(filtered_browser)
        domain_times_sorted = sorted(domain_times.items(), key=lambda x: -x[1])
        browser_total = sum(domain_times.values())

        # Step 5: Editor data aggregation
        editor_stats = self.aggregator.aggregate_editor_stats(filtered_editor)
        editor_total = sum(editor_stats["by_language"].values())
        language_sorted = sorted(
            editor_stats["by_language"].items(), key=lambda x: -x[1]
        )
        project_sorted = sorted(
            editor_stats["by_project"].items(), key=lambda x: -x[1]
        )

        # Step 6: Build behavior views for AI analysis
        views = {
            "timeline": build_timeline_view(
                filtered_window,
                filtered_browser,
                min_duration_seconds=60,
            ),
            "sessions": build_session_view(
                filtered_window,
                min_session_minutes=10,
                merge_gap_seconds=120,
            ),
            "hourly_switches": build_hourly_switches(filtered_window),
            "website_summary": build_website_summary(
                filtered_browser,
                work_domains=self.work_domains,
            ),
        }

        return {
            "total_hours": seconds_to_hours(total_seconds),
            "not_afk_hours": seconds_to_hours(not_afk_seconds),
            "by_app": [
                (app, seconds_to_hours(s)) for app, s in app_times_sorted[:10]
            ],
            "by_category": [
                (cat, seconds_to_hours(s)) for cat, s in category_times_sorted
            ],
            "browser": {
                "total_hours": seconds_to_hours(browser_total),
                "top_domains": [
                    (d, seconds_to_hours(s)) for d, s in domain_times_sorted[:10]
                ],
            },
            "editor": {
                "total_hours": seconds_to_hours(editor_total),
                "by_language": [
                    (lang, seconds_to_hours(s)) for lang, s in language_sorted[:5]
                ],
                "by_project": [
                    (proj, seconds_to_hours(s)) for proj, s in project_sorted[:5]
                ],
            },
            "event_counts": {
                "window": len(window_events),
                "afk": len(afk_events),
                "browser": len(browser_events),
                "editor": len(editor_events),
            },
            "views": views,
        }
