"""
Data Processing Module.

This module handles AFK filtering, data aggregation, and statistics calculation
for ActivityWatch event data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse


def parse_timestamp(ts_str: str) -> datetime | None:
    """
    Parse an ISO format timestamp string.

    Args:
        ts_str: The timestamp string to parse.

    Returns:
        A datetime object if parsing succeeds, None otherwise.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            normalized = ts_str[:26].replace("+00:00", "")
            return datetime.strptime(normalized, fmt.replace("%z", ""))
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

    def __init__(self, categories: dict[str, list[str]]) -> None:
        """
        Initialize the data processor.

        Args:
            categories: Dictionary mapping category names to app name patterns.
        """
        self.aggregator = DataAggregator(categories)

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
        }
