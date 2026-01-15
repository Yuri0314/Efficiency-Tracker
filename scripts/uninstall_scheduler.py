#!/usr/bin/env python3
"""
Uninstall scheduled tasks for efficiency-tracker.

This script removes launchd agents that were installed for automatic
daily and weekly report generation.

Usage:
    python scripts/uninstall_scheduler.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def uninstall_launchd_agents() -> None:
    """Uninstall launchd agents for daily and weekly reports."""
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"

    plist_files = [
        "com.efficiency-tracker.daily.plist",
        "com.efficiency-tracker.weekly.plist",
    ]

    for plist_name in plist_files:
        plist_path = launch_agents_dir / plist_name

        if not plist_path.exists():
            print(f"Not found (skipping): {plist_name}")
            continue

        # Unload the agent
        result = subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"Unloaded: {plist_name}")
        else:
            print(f"Warning: Failed to unload {plist_name}: {result.stderr}")

        # Remove the plist file
        plist_path.unlink()
        print(f"Removed: {plist_path}")


def main() -> None:
    """Main entry point."""
    if sys.platform != "darwin":
        print("Error: This script only supports macOS")
        print("For Linux, please remove cron jobs manually:")
        print("  crontab -e")
        sys.exit(1)

    print("Uninstalling efficiency-tracker scheduled tasks...")
    print()

    uninstall_launchd_agents()

    print()
    print("Uninstallation complete!")


if __name__ == "__main__":
    main()
