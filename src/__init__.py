"""
Efficiency Tracker - Personal productivity tracking based on ActivityWatch.

This package provides modules for collecting, processing, and analyzing
computer usage data from ActivityWatch to generate efficiency reports.
"""

from src.collector import (
    ActivityWatchCollector,
    get_custom_range,
    get_today_range,
    get_week_range,
)
from src.processor import DataProcessor
from src.analyzer import AIAnalyzer
from src.reporter import ConsolePrinter, ReportGenerator

__version__ = "0.3.0"
__author__ = "Your Name"

__all__ = [
    # Collector
    "ActivityWatchCollector",
    "get_today_range",
    "get_week_range",
    "get_custom_range",
    # Processor
    "DataProcessor",
    # Analyzer
    "AIAnalyzer",
    # Reporter
    "ReportGenerator",
    "ConsolePrinter",
]
