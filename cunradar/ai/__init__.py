"""AI daily digest generator using DeepSeek API."""

import json
from datetime import datetime, timezone

import requests

from ..collectors.base import CollectedItem


AI_SYSTEM_PROMPT = """You are CunRadar's AI digest writer. Your job is to take today's
collection of updates from various sources and produce a concise,
well-organized daily digest in Chinese.

Rules:
1. Group related items by topic when possible.
2. Keep each item description to 1-2 sentences.
3. Focus on WHAT changed and WHY it matters.
4. If an item is from GitHub, note the repo name.
5. If an item is a video, note the creator name.
6. Output in MARKDOWN format with clear section headers.
7. Be factual and concise - no fluff or marketing language.
8. Total output should be 200-500 characters.
9. If there are very few updates (0-3 items), still write a short digest.
10. Write all explanations in Simplified Chinese. Keep useful original English
    product, project, and plugin names in parentheses for searchability.
11. For every update you mention, add a Chinese annotation explaining what
    changed and why it matters to AI, game technology, 3D animation, Unreal
    Engine, Autodesk Maya, animation pipelines, or production plugins.
12. Preserve the original URL for every update you mention. Format the title
    or a Chinese '查看原文' label as a Markdown link to that exact URL."""


def build_user_prompt(items: list[CollectedItem], date_str: str) -> str:
    """Build the user prompt from collected items."""
    lines = [f"Today's date: {date_str}", "", "Updates collected today:"]
    for i, item in enumerate(items, 1):
        source_tag = item.source.upper()
        published = item.published.strftime("%H:%M UTC") if item.published else "unknown time"
        lines.append(f"{i}. [{source_tag}] {item.title}")
        lines.append(f"   From: {item.source_name} | {published}")
        lines.append(f"   URL: {item.url}")
        if item.description:
            desc = item.description[:200].replace("\n", " ")
            lines.append(f"   {desc}")
        lines.append("")
    return "\n".join(lines)


def generate_digest(
    items: list[CollectedItem],
    date_str: str,
    api_key: str,
    model: str = "deepseek-chat",
    api_base: str = "https://api.deepseek.com",
    timeout: int = 120,
) -> str:
    """Generate an AI-powered daily digest using DeepSeek.

    Returns:
        The markdown digest text. Returns empty string on failure.
    """
    if not items:
        return "今日无新内容。"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(items, date_str)},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        print(f"  [AI Digest] Generated successfully ({len(content)} chars)")
        return content
    except Exception as e:
        print(f"  [AI Digest] Failed: {e}")
        return ""
