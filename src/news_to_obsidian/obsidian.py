"""Obsidian vault note writer."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from slugify import slugify

from .config import TagRule
from .freshrss import Entry


def _render_filename(template: str, entry: Entry) -> str:
    """
    Expand a filename template using entry metadata.

    Supported placeholders:
        {title}  - article title (slugified)
        {date}   - publication date as YYYY-MM-DD
        {feed}   - source feed name (slugified)
        {id}     - FreshRSS entry id
    """
    raw = template.format(
        title=slugify(entry.title, max_length=80, separator="-"),
        date=entry.date.strftime("%Y-%m-%d"),
        feed=slugify(entry.feed_name, max_length=40, separator="-"),
        id=str(entry.id),
    )
    # Ensure the result has a .md extension
    if not raw.endswith(".md"):
        raw += ".md"
    return raw


def _build_frontmatter(entry: Entry, rule: TagRule) -> str:
    """Build YAML frontmatter for the Obsidian note."""
    date_str = entry.date.strftime("%Y-%m-%d")
    created_str = datetime.now().strftime("%Y-%m-%d")
    tag_slug = slugify(rule.tag, separator="-")

    lines = [
        "---",
        f'title: "{entry.title.replace(chr(34), chr(39))}"',
        f"source: {entry.link}",
        f"author: {entry.author}",
        f"feed: {entry.feed_name}",
        f"published: {date_str}",
        f"created: {created_str}",
        f"freshrss_tag: {rule.tag}",
        f"tags:",
        f"  - news",
        f"  - {tag_slug}",
        "---",
        "",
    ]
    return "\n".join(lines)


def write_note(
    vault_path: Path,
    rule: TagRule,
    entry: Entry,
    content: str,
    dry_run: bool = False,
) -> Path:
    """
    Write the LLM-generated content as a Markdown note in the Obsidian vault.

    Returns the path of the note that was (or would be) written.
    """
    filename = _render_filename(rule.filename_template, entry)

    # Determine target directory
    if rule.output_folder:
        target_dir = vault_path / rule.output_folder
    else:
        target_dir = vault_path

    note_path = target_dir / filename

    frontmatter = _build_frontmatter(entry, rule)
    full_content = frontmatter + content + "\n"

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

        # Handle filename collision by appending the entry id
        if note_path.exists():
            stem = note_path.stem
            note_path = target_dir / f"{stem}-{entry.id}.md"

        note_path.write_text(full_content, encoding="utf-8")

    return note_path
