#!/usr/bin/env python3
"""
Install scheduled tasks for efficiency-tracker.

This script installs launchd agents on macOS to run daily and weekly reports
automatically at scheduled times.

Usage:
    python scripts/install_scheduler.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_python_path() -> str:
    """Get the path to the current Python interpreter."""
    return sys.executable


def get_project_path() -> Path:
    """Get the absolute path to the project root."""
    return Path(__file__).parent.parent.resolve()


def install_launchd_agents() -> None:
    """Install launchd agents for daily and weekly reports."""
    project_path = get_project_path()
    python_path = get_python_path()
    scripts_dir = project_path / "scripts"
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    logs_dir = project_path / "logs"

    # Create logs directory
    logs_dir.mkdir(exist_ok=True)

    # Create LaunchAgents directory if it doesn't exist
    launch_agents_dir.mkdir(parents=True, exist_ok=True)

    plist_files = [
        "com.efficiency-tracker.daily.plist",
        "com.efficiency-tracker.weekly.plist",
    ]

    for plist_name in plist_files:
        src_plist = scripts_dir / plist_name
        dst_plist = launch_agents_dir / plist_name

        if not src_plist.exists():
            print(f"Error: {src_plist} not found")
            continue

        # Read template and replace placeholders
        content = src_plist.read_text()
        content = content.replace("__PYTHON_PATH__", python_path)
        content = content.replace("__PROJECT_PATH__", str(project_path))

        # Write to LaunchAgents directory
        dst_plist.write_text(content)
        print(f"Installed: {dst_plist}")

        # Load the agent
        subprocess.run(
            ["launchctl", "unload", str(dst_plist)],
            capture_output=True,
        )
        result = subprocess.run(
            ["launchctl", "load", str(dst_plist)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"Loaded: {plist_name}")
        else:
            print(f"Failed to load {plist_name}: {result.stderr}")


def main() -> None:
    """Main entry point."""
    if sys.platform != "darwin":
        print("Error: This script only supports macOS")
        print("For Linux, please set up cron jobs manually:")
        print("  30 21 * * * cd /path/to/efficiency-tracker && python main.py --period day")
        print("  30 21 * * 0 cd /path/to/efficiency-tracker && python main.py --period week")
        sys.exit(1)

    print("Installing efficiency-tracker scheduled tasks...")
    print(f"Project path: {get_project_path()}")
    print(f"Python path: {get_python_path()}")
    print()

    install_launchd_agents()

    print()
    print("Installation complete!")
    print()
    print("Schedule:")
    print("  - Daily report: Every day at 21:30")
    print("  - Weekly report: Every Sunday at 21:30")
    print()
    print("To check status:")
    print("  launchctl list | grep efficiency-tracker")
    print()
    print("To uninstall:")
    print("  python scripts/uninstall_scheduler.py")


if __name__ == "__main__":
    main()
