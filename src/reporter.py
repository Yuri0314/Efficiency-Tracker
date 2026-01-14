"""
Report Generation Module.

This module handles formatting and saving efficiency reports,
as well as console output for progress indication.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any


class ReportGenerator:
    """
    Generator for creating and saving Markdown efficiency reports.

    This class formats the AI analysis and data summary into a
    complete Markdown report and saves it to disk.

    Attributes:
        output_dir: Directory path where reports will be saved.

    Example:
        >>> generator = ReportGenerator("./reports")
        >>> filepath = generator.save(ai_report, summary, start, end, "Weekly")
    """

    def __init__(self, output_dir: str = "./reports") -> None:
        """
        Initialize the report generator.

        Args:
            output_dir: Directory path for saving reports. Defaults to "./reports".
        """
        self.output_dir = output_dir

    def generate_markdown(
        self,
        ai_report: str,
        data_summary: str,
        start: datetime,
        end: datetime,
        period_name: str,
    ) -> str:
        """
        Generate complete Markdown report content.

        Args:
            ai_report: The AI-generated analysis text.
            data_summary: The formatted data summary.
            start: Start datetime of the report period.
            end: End datetime of the report period.
            period_name: Human-readable name for the period.

        Returns:
            The complete Markdown report as a string.
        """
        return f"""# 个人效率报告
> {period_name} | {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}
> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 AI 分析

{ai_report}

---

## 📈 原始数据

{data_summary}
"""

    def save(
        self,
        ai_report: str,
        data_summary: str,
        start: datetime,
        end: datetime,
        period_name: str,
    ) -> str:
        """
        Save the report to a Markdown file.

        Creates the output directory if it doesn't exist.

        Args:
            ai_report: The AI-generated analysis text.
            data_summary: The formatted data summary.
            start: Start datetime of the report period.
            end: End datetime of the report period.
            period_name: Human-readable name for the period.

        Returns:
            The path to the saved report file.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        date_str = end.strftime("%Y-%m-%d")
        filename = f"{self.output_dir}/report_{period_name}_{date_str}.md"

        content = self.generate_markdown(
            ai_report, data_summary, start, end, period_name
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        return filename


class ConsolePrinter:
    """
    Utility class for console output during report generation.

    All methods are static and handle printing progress messages,
    statistics, and reports to the console with consistent formatting.
    """

    @staticmethod
    def print_header() -> None:
        """Print the application header banner."""
        print("=" * 50)
        print("🚀 个人效率感知系统 v0.3")
        print("=" * 50)

    @staticmethod
    def print_period(period_name: str, start: datetime, end: datetime) -> None:
        """
        Print the report time period.

        Args:
            period_name: Human-readable name for the period.
            start: Start datetime.
            end: End datetime.
        """
        print(
            f"\n📅 {period_name}: "
            f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"
        )

    @staticmethod
    def print_collecting() -> None:
        """Print the data collection status message."""
        print("\n📊 正在采集数据...")

    @staticmethod
    def print_buckets_info(info: dict[str, Any]) -> None:
        """
        Print information about discovered ActivityWatch buckets.

        Args:
            info: Dictionary containing bucket information.
        """
        print(f"   - Window: {info.get('window', '未找到')}")
        print(f"   - AFK: {info.get('afk') or '未找到'}")
        print(f"   - Browser: {info.get('browser') or '未找到'}")
        print(f"   - Editors: {info.get('editor_count', 0)} 个")

    @staticmethod
    def print_event_counts(counts: dict[str, int]) -> None:
        """
        Print the count of events by type.

        Args:
            counts: Dictionary mapping event types to counts.
        """
        print("\n   事件数量:")
        print(f"   - Window: {counts.get('window', 0)}")
        print(f"   - AFK: {counts.get('afk', 0)}")
        print(f"   - Browser: {counts.get('browser', 0)}")
        print(f"   - Editor: {counts.get('editor', 0)}")

    @staticmethod
    def print_processing() -> None:
        """Print the data processing status message."""
        print("\n⚙️  正在处理数据...")

    @staticmethod
    def print_stats_summary(stats: dict[str, Any]) -> None:
        """
        Print a summary of the processed statistics.

        Args:
            stats: Processed statistics dictionary.
        """
        print(f"   - 总时长: {stats['total_hours']} 小时")
        print(f"   - 活跃时长: {stats['not_afk_hours']} 小时")
        print(f"   - 编程时长: {stats['editor']['total_hours']} 小时")
        print(f"   - 浏览器时长: {stats['browser']['total_hours']} 小时")

    @staticmethod
    def print_ai_calling() -> None:
        """Print the AI API call status message."""
        print("\n🤖 正在调用 AI 分析...")

    @staticmethod
    def print_ai_skipped() -> None:
        """Print the AI skipped status message."""
        print("\n⏭️  跳过 AI 分析")

    @staticmethod
    def print_saved(filename: str) -> None:
        """
        Print the report saved confirmation.

        Args:
            filename: Path to the saved report file.
        """
        print(f"\n💾 报告已保存: {filename}")

    @staticmethod
    def print_report(report: str) -> None:
        """
        Print the final report content.

        Args:
            report: The report content to display.
        """
        print("\n" + "=" * 50)
        print("📋 效率分析报告")
        print("=" * 50)
        print(report)
        print("\n" + "=" * 50)

    @staticmethod
    def print_error(message: str) -> None:
        """
        Print an error message.

        Args:
            message: The error message to display.
        """
        print(f"❌ {message}")
