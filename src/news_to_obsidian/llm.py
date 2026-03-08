"""LLM processing via openai-compatible API."""

from __future__ import annotations

from openai import OpenAI

from .config import LLMConfig, TagRule
from .freshrss import Entry

# System prompt injected before every user message
_SYSTEM_PROMPT = """\
You are an assistant that transforms news articles and tech blog posts into \
Obsidian Markdown notes. Follow the user's instructions precisely.
Always respond with valid Markdown only — no code fences, no preamble, no \
explanation outside the note itself.
"""


def build_user_message(entry: Entry, rule: TagRule) -> str:
    """Build the user-facing prompt sent to the LLM."""
    from markdownify import markdownify

    parts: list[str] = []

    parts.append(f"# Instructions\n{rule.consign}")
    parts.append(
        f"# Article metadata\n"
        f"- **Title**: {entry.title}\n"
        f"- **Author**: {entry.author}\n"
        f"- **Source feed**: {entry.feed_name}\n"
        f"- **URL**: {entry.link}\n"
        f"- **Date**: {entry.date.strftime('%Y-%m-%d')}\n"
    )

    if rule.include_content and entry.content:
        md_content = markdownify(entry.content, heading_style="ATX").strip()
        parts.append(f"# Article content\n{md_content}")

    return "\n\n---\n\n".join(parts)


def call_llm(entry: Entry, rule: TagRule, llm_cfg: LLMConfig) -> str:
    """
    Call the LLM via an OpenAI-compatible API and return the generated
    Markdown note content.

    Works with any OpenAI-compatible provider (GLM, Ollama, Azure OpenAI,
    local proxies, etc.) by adjusting base_url / api_key / model in config.
    """
    client = OpenAI(
        api_key=llm_cfg.api_key or "no-key",
        base_url=llm_cfg.base_url or None,
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(entry, rule)},
    ]

    response = client.chat.completions.create(
        model=llm_cfg.model,
        messages=messages,
        **llm_cfg.extra,
    )

    return response.choices[0].message.content.strip()
