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
        trend_info: str | None = None,
    ) -> tuple[str, str]:
        """
        Build an AI analysis prompt from processed statistics and behavior views.

        Args:
            stats: Processed statistics dictionary from DataProcessor,
                including 'views' with timeline, sessions, hourly_switches,
                and website_summary.
            start: Start datetime of the report period.
            end: End datetime of the report period.
            period_name: Human-readable name for the period (e.g., "Weekly").
            trend_info: Optional formatted string with trend comparison data.

        Returns:
            A tuple of (prompt, data_summary) where:
                - prompt: The full prompt to send to the AI
                - data_summary: The formatted data summary for the report
        """
        period = f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}"

        # Basic statistics for reference
        app_list = "\n".join(
            [f"  - {app}: {hours}h" for app, hours in stats["by_app"]]
        )
        category_list = "\n".join(
            [f"  - {cat}: {hours}h" for cat, hours in stats["by_category"]]
        )

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

        # Data summary for report (kept for backward compatibility)
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
{editor_section}
"""

        # Calculate activity rate
        activity_rate = (
            round(stats["not_afk_hours"] / stats["total_hours"] * 100, 1)
            if stats["total_hours"] > 0
            else 0
        )

        # Get behavior views
        views = stats.get("views", {})
        timeline_view = views.get("timeline", "（无数据）")
        session_view = views.get("sessions", "（无数据）")
        hourly_switches_view = views.get("hourly_switches", "（无数据）")
        website_summary_view = views.get("website_summary", "（无数据）")

        # Build trend section if comparison data is available
        trend_section = ""
        if trend_info:
            trend_section = f"\n{trend_info}\n"

        # Build prompt with behavior views for AI insight discovery
        prompt = f"""以下是我{period_name}（{period}）的电脑使用行为数据：

## 基础信息
- 总记录时长: {stats['total_hours']} 小时
- 活跃时长（非AFK）: {stats['not_afk_hours']} 小时
- 活跃率: {activity_rate}%

## 应用使用时间线
（展示应用切换的时间序列，带持续时长）
{timeline_view}

## 连续使用段落
（相邻同应用事件合并后的使用段落，超过10分钟的）
{session_view}

## 各小时切换频率
（每小时应用切换次数，可反映注意力碎片化程度）
{hourly_switches_view}

## 网站访问摘要
{website_summary_view}

## 应用使用统计
{app_list}

{trend_section}
---

请分析上述数据，帮我发现行为模式和效率洞察。

## 分析要点

1. **打断模式**：有没有某个应用/网站经常打断工作流？从时间线中寻找线索。
2. **低效时段**：哪个时间段切换最频繁？这可能是效率较低的时段。
3. **专注时段**：从连续使用段落中，找出能保持较长专注的时间段。
4. **趋势变化**：对比历史数据，有什么显著的进步或退步？
5. **有趣发现**：任何你注意到的模式、规律或异常。

## 输出格式

### 📊 整体概览
（1-2句话总结本周期的整体状况）

### ⏰ 时间分配
（指出时间主要花在哪些应用/类别，占比最高的2-3项）

### 💡 发现与洞察
（基于行为数据发现的具体模式，用要点列出，要具体到时间点或应用）

### 📈 趋势变化
（如有历史对比数据，指出显著的进步或退步，没有历史数据则跳过此节）

### ✅ 改进建议
（1-2条具体可行的建议，针对发现的问题）
例如好的建议："14:00-15:00 切换频繁，考虑把会议安排在这个时段"
例如差的建议："建议减少切换次数"（太泛泛）

### 🎯 锐评
（用一句犀利、直接的话点评今天的工作状态，可以毒舌但要基于数据，像朋友间的吐槽）
例如："花了3小时在浏览器上，你是在工作还是在网上冲浪？"
例如："切换了200次应用，你的注意力比金鱼还短。"
例如："今天状态不错，终于像个正经打工人了。"

注意：
- 基于数据说话，不要编造不存在的信息
- 建议要具体、可执行，不要泛泛而谈
- 锐评要有趣、直接，但不要人身攻击
- 严格按照上述格式输出，不要添加额外章节
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

            # Handle different response formats
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                message = choice.get("message", {})

                # Standard OpenAI format
                if "content" in message and message["content"]:
                    return message["content"]

                # Reasoning model format (like o1/DeepSeek) - has reasoning_content
                if "reasoning_content" in message:
                    # For reasoning models, the actual answer should be in 'content'
                    # If content is empty but we have reasoning, return reasoning
                    content = message.get("content") or message.get("reasoning_content")
                    if content:
                        return content

                # Some APIs use 'text' directly
                if "text" in choice:
                    return choice["text"]

            # If we get here, the response format is unexpected
            return f"AI 响应格式异常: {result}"

        except requests.exceptions.Timeout:
            return "AI 调用超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            return f"AI 调用失败: {e}"
        except (KeyError, IndexError) as e:
            return f"AI 响应解析失败: {e}"
