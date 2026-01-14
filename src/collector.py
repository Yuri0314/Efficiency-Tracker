"""
Data Collection Module.

This module is responsible for fetching event data from the ActivityWatch API.
It provides the ActivityWatchCollector class for interacting with the AW server
and utility functions for generating time ranges.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests


class ActivityWatchCollector:
    """
    ActivityWatch data collector.

    This class handles communication with the ActivityWatch server API
    to retrieve bucket information and event data.

    Attributes:
        host: The ActivityWatch server URL.

    Example:
        >>> collector = ActivityWatchCollector("http://localhost:5600")
        >>> buckets = collector.get_buckets()
        >>> events = collector.get_events("aw-watcher-window_hostname", start, end)
    """

    def __init__(self, host: str = "http://localhost:5600") -> None:
        """
        Initialize the collector.

        Args:
            host: The ActivityWatch server URL. Defaults to localhost:5600.
        """
        self.host = host
        self._buckets_cache: dict[str, Any] | None = None

    def get_buckets(self) -> dict[str, Any]:
        """
        Retrieve all buckets from the ActivityWatch server.

        Results are cached after the first call.

        Returns:
            A dictionary mapping bucket IDs to their metadata.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        if self._buckets_cache is None:
            resp = requests.get(f"{self.host}/api/0/buckets", timeout=30)
            resp.raise_for_status()
            self._buckets_cache = resp.json()
        return self._buckets_cache

    def get_events(
        self,
        bucket_id: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """
        Retrieve events from a specific bucket within a time range.

        Args:
            bucket_id: The ID of the bucket to query.
            start: The start of the time range.
            end: The end of the time range.

        Returns:
            A list of event dictionaries.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        resp = requests.get(
            f"{self.host}/api/0/buckets/{bucket_id}/events",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def find_bucket(self, client_prefix: str) -> str | None:
        """
        Find a single bucket by client name prefix.

        Args:
            client_prefix: The prefix to match against bucket client names.

        Returns:
            The bucket ID if found, None otherwise.
        """
        buckets = self.get_buckets()
        for bucket_id, info in buckets.items():
            if info.get("client", "").startswith(client_prefix):
                return bucket_id
        return None

    def find_all_buckets(self, client_prefix: str) -> list[str]:
        """
        Find all buckets matching a client name prefix.

        Args:
            client_prefix: The prefix to match against bucket client names.

        Returns:
            A list of matching bucket IDs.
        """
        buckets = self.get_buckets()
        return [
            bucket_id
            for bucket_id, info in buckets.items()
            if info.get("client", "").startswith(client_prefix)
        ]

    def collect_all(
        self,
        start: datetime,
        end: datetime,
        editor_prefixes: list[str],
    ) -> dict[str, Any]:
        """
        Collect all types of event data from ActivityWatch.

        This method fetches window, AFK, browser, and editor events
        within the specified time range.

        Args:
            start: The start of the time range.
            end: The end of the time range.
            editor_prefixes: List of editor watcher client prefixes
                (e.g., ["aw-watcher-vscode", "aw-watcher-pycharm"]).

        Returns:
            A dictionary containing:
                - window: List of window events
                - afk: List of AFK events
                - browser: List of browser events
                - editor: List of editor events
                - buckets_info: Metadata about found buckets
        """
        # Find buckets
        window_bucket = self.find_bucket("aw-watcher-window")
        afk_bucket = self.find_bucket("aw-watcher-afk")
        browser_bucket = self.find_bucket("aw-watcher-web")

        editor_buckets: list[str] = []
        for prefix in editor_prefixes:
            editor_buckets.extend(self.find_all_buckets(prefix))

        # Collect events
        result: dict[str, Any] = {
            "window": [],
            "afk": [],
            "browser": [],
            "editor": [],
            "buckets_info": {
                "window": window_bucket,
                "afk": afk_bucket,
                "browser": browser_bucket,
                "editor_count": len(editor_buckets),
            },
        }

        if window_bucket:
            result["window"] = self.get_events(window_bucket, start, end)

        if afk_bucket:
            result["afk"] = self.get_events(afk_bucket, start, end)

        if browser_bucket:
            result["browser"] = self.get_events(browser_bucket, start, end)

        for bucket in editor_buckets:
            result["editor"].extend(self.get_events(bucket, start, end))

        return result


# =============================================================================
# Time Range Utilities
# =============================================================================


def get_today_range() -> tuple[datetime, datetime]:
    """
    Get the time range for today.

    Returns:
        A tuple of (start_of_today, now).
    """
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def get_week_range() -> tuple[datetime, datetime]:
    """
    Get the time range for the current week (Monday to now).

    Returns:
        A tuple of (start_of_week, now).
    """
    now = datetime.now()
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def get_custom_range(start_str: str, end_str: str) -> tuple[datetime, datetime]:
    """
    Get a custom time range from date strings.

    Args:
        start_str: Start date in YYYY-MM-DD format.
        end_str: End date in YYYY-MM-DD format.

    Returns:
        A tuple of (start_datetime, end_datetime).
        The end time is set to 23:59:59 of the end date.
    """
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59
    )
    return start, end


def get_yesterday_range() -> tuple[datetime, datetime]:
    """
    Get the time range for yesterday (full day).

    Returns:
        A tuple of (start_of_yesterday, end_of_yesterday).
    """
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def get_last_week_range() -> tuple[datetime, datetime]:
    """
    Get the time range for last week (Monday to Sunday).

    Returns:
        A tuple of (start_of_last_week, end_of_last_week).
    """
    now = datetime.now()
    # Start of this week (Monday)
    this_week_start = now - timedelta(days=now.weekday())
    this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Last week is 7 days before this week
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)  # Sunday 23:59:59
    return last_week_start, last_week_end
