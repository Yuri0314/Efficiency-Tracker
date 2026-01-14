#!/usr/bin/env python3
"""
Personal Efficiency Tracking System v0.3.

A personal productivity tracking tool based on ActivityWatch.
This module provides the CLI entry point for the application.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from src.analyzer import AIAnalyzer
from src.collector import (
    ActivityWatchCollector,
    get_custom_range,
    get_today_range,
    get_week_range,
)
from src.processor import DataProcessor
from src.reporter import ConsolePrinter, ReportGenerator


def load_config(config_path: str = "config/config.yaml") -> dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Configuration dictionary. Returns default config if file not found.
    """
    path = Path(config_path)
    if not path.exists():
        print(f"⚠️  Config file not found: {config_path}, using defaults")
        return get_default_config()

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_default_config() -> dict[str, Any]:
    """
    Get the default configuration.

    Returns:
        Default configuration dictionary with all required settings.
    """
    return {
        "activitywatch": {"host": "http://localhost:5600"},
        "ai": {
            "api_base": "https://your-company-api/v1",
            "api_key": "your-api-key",
            "model": "glm-4.7",
            "max_tokens": 2000,
            "temperature": 0.7,
        },
        "output": {"reports_dir": "./reports"},
        "categories": {
            "coding": [
                "VS Code", "Code", "PyCharm", "IntelliJ",
                "WebStorm", "Xcode", "Terminal", "iTerm", "Cursor",
            ],
            "browser": ["Chrome", "Safari", "Firefox", "Arc", "Edge"],
            "communication": [
                "钉钉", "企业微信", "Slack", "飞书",
                "腾讯会议", "Zoom", "微信", "Messages",
            ],
            "writing": ["Notion", "Obsidian", "Word", "Pages", "Typora", "Bear"],
        },
        "editor_watchers": [
            "aw-watcher-vscode",
            "aw-watcher-pycharm",
            "aw-watcher-intellij",
            "aw-watcher-webstorm",
        ],
        "work_domains": [
            "alidocs.dingtalk.com",
            "yuque.antfin.com",
            "aliyuque.antfin.com",
            "code.alibaba-inc.com",
        ],
    }


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Personal Efficiency Tracker - ActivityWatch-based productivity tool"
    )
    parser.add_argument(
        "--period",
        choices=["day", "week"],
        default="week",
        help="Report period: day (daily) or week (weekly). Default: week",
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (format: YYYY-MM-DD) for custom period",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date (format: YYYY-MM-DD) for custom period",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI analysis, output statistics only",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Config file path. Default: config/config.yaml",
    )
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the efficiency tracker.

    This function orchestrates the full workflow:
    1. Load configuration
    2. Determine time range
    3. Collect data from ActivityWatch
    4. Process and aggregate data
    5. Generate AI analysis (optional)
    6. Save and display report
    """
    args = parse_args()
    printer = ConsolePrinter()

    # Step 1: Load configuration
    config = load_config(args.config)

    printer.print_header()

    # Step 2: Determine time range
    if args.start and args.end:
        start, end = get_custom_range(args.start, args.end)
        period_name = "自定义周期"
    elif args.period == "day":
        start, end = get_today_range()
        period_name = "日报"
    else:
        start, end = get_week_range()
        period_name = "周报"

    printer.print_period(period_name, start, end)

    # Step 3: Collect data
    printer.print_collecting()

    collector = ActivityWatchCollector(config["activitywatch"]["host"])

    try:
        raw_data = collector.collect_all(
            start, end, config.get("editor_watchers", [])
        )
    except Exception as e:
        printer.print_error(f"Data collection failed: {e}")
        printer.print_error("Please verify ActivityWatch is running")
        sys.exit(1)

    if not raw_data.get("window"):
        printer.print_error(
            "No window events found. Please verify ActivityWatch is running"
        )
        sys.exit(1)

    printer.print_buckets_info(raw_data["buckets_info"])

    # Step 4: Process data
    printer.print_processing()

    processor = DataProcessor(
        categories=config["categories"],
        work_domains=config.get("work_domains", []),
    )
    stats = processor.process(raw_data)

    printer.print_event_counts(stats["event_counts"])
    printer.print_stats_summary(stats)

    # Step 5: AI analysis
    ai_config = config["ai"]
    analyzer = AIAnalyzer(
        api_base=ai_config["api_base"],
        api_key=ai_config["api_key"],
        model=ai_config["model"],
        max_tokens=ai_config.get("max_tokens", 2000),
        temperature=ai_config.get("temperature", 0.7),
    )

    prompt, data_summary = analyzer.build_prompt(stats, start, end, period_name)

    if args.no_ai:
        printer.print_ai_skipped()
        ai_report = "(AI analysis skipped)"
    else:
        printer.print_ai_calling()
        ai_report = analyzer.analyze(prompt)

    # Step 6: Generate report
    reporter = ReportGenerator(config["output"]["reports_dir"])
    filename = reporter.save(
        ai_report, data_summary, start, end, period_name, stats.get("views")
    )

    printer.print_saved(filename)
    printer.print_report(ai_report)


if __name__ == "__main__":
    main()
