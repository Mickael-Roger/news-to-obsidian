"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    """LLM endpoint configuration."""

    model: str
    api_key: str = ""
    api_base: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        known = {"model", "api_key", "api_base"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            model=data["model"],
            api_key=data.get("api_key", os.environ.get("LLM_API_KEY", "")),
            api_base=data.get("api_base", ""),
            extra=extra,
        )


@dataclass
class TagRule:
    """A single tag → LLM consign mapping."""

    tag: str
    consign: str
    # Output subfolder inside the vault (optional, defaults to root)
    output_folder: str = ""
    # Note filename template: supports {title}, {date}, {feed}
    filename_template: str = "{title}"
    # Whether to include the original HTML content in the LLM context
    include_content: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagRule":
        return cls(
            tag=data["tag"],
            consign=data["consign"],
            output_folder=data.get("output_folder", ""),
            filename_template=data.get("filename_template", "{title}"),
            include_content=data.get("include_content", True),
        )


@dataclass
class Config:
    """Full application configuration."""

    freshrss_db: Path
    obsidian_vault: Path
    llm: LLMConfig
    rules: list[TagRule]
    # Remove the tag from the entry after processing
    remove_tag_after_processing: bool = True
    # Dry-run: do not write notes or remove tags
    dry_run: bool = False

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        with open(path) as f:
            raw = yaml.safe_load(f)

        llm_cfg = LLMConfig.from_dict(raw["llm"])

        rules = [TagRule.from_dict(r) for r in raw.get("rules", [])]
        if not rules:
            raise ValueError("Configuration must define at least one rule.")

        return cls(
            freshrss_db=Path(raw["freshrss_db"]).expanduser(),
            obsidian_vault=Path(raw["obsidian_vault"]).expanduser(),
            llm=llm_cfg,
            rules=rules,
            remove_tag_after_processing=raw.get("remove_tag_after_processing", True),
            dry_run=raw.get("dry_run", False),
        )
