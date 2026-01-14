"""
AI Analysis Module.

This module handles building prompts and calling AI APIs to generate
efficiency analysis reports from processed ActivityWatch data.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests


class AIAnalyzer:
    """
    AI-powered analyzer for generating efficiency reports.

    This class builds prompts from processed statistics and calls an
    OpenAI-compatible API to generate natural language analysis.

    Attributes:
        api_base: The base URL of the AI API.
        api_key: The API key for authentication.
        model: The model identifier to use.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature for generation.

    Example:
        >>> analyzer = AIAnalyzer(
        ...     api_base="https://api.example.com/v1",
        ...     api_key="your-key",
        ...     model="gpt-4"
        ... )
        >>> prompt, summary = analyzer.build_prompt(stats, start, end, "Weekly")
        >>> report = analyzer.analyze(prompt)
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str = "glm-4.7",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> None:
        """
        Initialize the AI analyzer.

        Environment variables OPENAI_BASE_URL and OPENAI_API_KEY take
        precedence over the provided arguments.

        Args:
            api_base: The base URL of the AI API.
            api_key: The API key for authentication.
            model: The model identifier to use. Defaults to "glm-4.7".
            max_tokens: Maximum tokens in the response. Defaults to 2000.
            temperature: Sampling temperature. Defaults to 0.7.
        """
        self.api_base = os.getenv("OPENAI_BASE_URL", api_base)
        self.api_key = os.getenv("OPENAI_API_KEY", api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def build_prompt(
        self,
        stats: dict[str, Any],
        start: datetime,
        end: datetime,
        period_name: str,
    ) -> tuple[str, str]:
        """
        Build an AI analysis prompt from processed statistics.

        Args:
            stats: Processed statistics dictionary from DataProcessor.
            start: Start datetime of the report period.
            end: End datetime of the report period.
            period_name: Human-readable name for the period (e.g., "Weekly").

        Returns:
            A tuple of (prompt, data_summary) where:
                - prompt: The full prompt to send to the AI
                - data_summary: The formatted data summary for the report
        """
        period = f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"

        app_list = "\n".join(
            [f"  - {app}: {hours}h" for app, hours in stats["by_app"]]
        )
        category_list = "\n".join(
            [f"  - {cat}: {hours}h" for cat, hours in stats["by_category"]]
        )

        # Browser statistics section
        browser_section = ""
        if stats["browser"]["top_domains"]:
            domain_list = "\n".join(
                [f"  - {d}: {h}h" for d, h in stats["browser"]["top_domains"][:5]]
            )
            browser_section = f"""
## 浏览器使用（共 {stats['browser']['total_hours']}h）
{domain_list}
"""

        # Editor statistics section
        editor_section = ""
        if stats["editor"]["by_language"]:
            lang_list = "\n".join(
                [f"  - {lang}: {h}h" for lang, h in stats["editor"]["by_language"]]
            )
            proj_list = "\n".join(
                [f"  - {proj}: {h}h" for proj, h in stats["editor"]["by_project"][:3]]
            )
            editor_section = f"""
## 编程统计（共 {stats['editor']['total_hours']}h）
按语言:
{lang_list}

按项目:
{proj_list}
"""

        data_summary = f"""
## 报告类型
{period_name}

## 时间范围
{period}

## 概览
- 总记录时长: {stats['total_hours']} 小时
- 活跃时长（非AFK）: {stats['not_afk_hours']} 小时

## 应用使用 TOP 10
{app_list}

## 按类别统计
{category_list}
{browser_section}
{editor_section}
"""

        # Calculate activity rate
        activity_rate = (
            round(stats["not_afk_hours"] / stats["total_hours"] * 100, 1)
            if stats["total_hours"] > 0
            else 0
        )

        prompt = f"""以下是我{period_name}的电脑使用数据统计：

{data_summary}

补充信息：
- 活跃率：{activity_rate}%（活跃时长/总记录时长）

请分析这些数据，生成一份简洁的效率报告。

## 输出格式

### 📊 整体概览
（用1-2句话总结本周期的效率表现，包含活跃率评价）

### ⏰ 时间分配
（分析时间主要花在哪些应用/类别，指出占比最高的2-3项）

### 💡 发现与洞察
（基于数据发现的模式、趋势或潜在问题，用要点列出）

### ✅ 改进建议
（1-2条具体可行的建议，针对发现的问题）

注意：严格按照上述格式输出，不要添加额外章节。
"""
        return prompt, data_summary

    def analyze(self, prompt: str) -> str:
        """
        Call the AI API to analyze the data and generate a report.

        Args:
            prompt: The analysis prompt to send to the AI.

        Returns:
            The AI-generated analysis report, or an error message if the
            API call fails.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一位专业的个人效率分析师。你的任务是分析用户的电脑使用数据，"
                        "提供客观、有洞察力的效率报告。\n\n"
                        "要求：\n"
                        "- 基于数据说话，不要编造或假设不存在的信息\n"
                        "- 语气友好但专业，像一位关心用户的效率教练\n"
                        "- 建议要具体可行，不要泛泛而谈\n"
                        "- 使用 Markdown 格式输出，结构清晰"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            resp = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return "AI 调用超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            return f"AI 调用失败: {e}"
        except (KeyError, IndexError) as e:
            return f"AI 响应解析失败: {e}"
