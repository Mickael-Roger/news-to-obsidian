"""LLM processing via litellm."""

from __future__ import annotations

import os
from typing import Any

from markdownify import markdownify

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
    Call the LLM and return the generated Markdown note content.

    Uses litellm so the same code works with any provider (Anthropic,
    OpenAI, Ollama, Azure, etc.) by just changing the model string and
    optional api_base / api_key in the config.
    """
    # Import here so the rest of the module is importable without litellm
    import litellm  # noqa: PLC0415

    # Override the API key / base if provided
    kwargs: dict[str, Any] = {}
    if llm_cfg.api_key:
        kwargs["api_key"] = llm_cfg.api_key
    if llm_cfg.api_base:
        kwargs["api_base"] = llm_cfg.api_base

    # Pass any extra keys from the config (e.g. temperature, max_tokens)
    kwargs.update(llm_cfg.extra)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(entry, rule)},
    ]

    response = litellm.completion(
        model=llm_cfg.model,
        messages=messages,
        **kwargs,
    )

    return response.choices[0].message.content.strip()
