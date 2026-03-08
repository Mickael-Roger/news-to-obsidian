"""Command-line interface for news-to-obsidian."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .config import Config
from .freshrss import FreshRSSDB
from .llm import call_llm
from .obsidian import write_note


@click.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    default="config.yaml",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the YAML configuration file.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Process entries and print output without writing notes or removing tags.",
)
@click.option(
    "--tag",
    "-t",
    "filter_tags",
    multiple=True,
    help="Only process rules for the given tag(s). Can be repeated.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Print detailed progress.",
)
def main(
    config_path: Path,
    dry_run: bool,
    filter_tags: tuple[str, ...],
    verbose: bool,
) -> None:
    """
    Read FreshRSS labelled entries, apply LLM consigns, and write Obsidian notes.

    \b
    Workflow for each rule in the configuration:
      1. Find all FreshRSS entries carrying the rule's tag/label.
      2. Send each entry + consign to the configured LLM.
      3. Write the generated Markdown as a note in the Obsidian vault.
      4. Remove the tag from the entry so it is not processed again.
    """
    # Load config
    try:
        cfg = Config.from_file(config_path)
    except Exception as exc:
        click.echo(f"[error] Cannot load config: {exc}", err=True)
        sys.exit(1)

    # CLI --dry-run overrides config
    if dry_run:
        cfg.dry_run = True

    if cfg.dry_run:
        click.echo("[dry-run] No notes will be written, no tags removed.")

    # Filter rules if --tag was provided
    rules = cfg.rules
    if filter_tags:
        rules = [r for r in rules if r.tag in filter_tags]
        if not rules:
            click.echo(
                f"[warning] No rules matched the requested tag(s): {', '.join(filter_tags)}",
                err=True,
            )
            sys.exit(0)

    with FreshRSSDB(cfg.freshrss_db) as db:
        total_processed = 0
        total_errors = 0

        for rule in rules:
            entries = db.entries_for_tag(rule.tag)

            if not entries:
                if verbose:
                    click.echo(f"[{rule.tag}] No entries found.")
                continue

            click.echo(
                f"[{rule.tag}] {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to process."
            )

            for entry in entries:
                label = f"[{rule.tag}] '{entry.title[:60]}'"
                try:
                    if verbose:
                        click.echo(f"  -> Calling LLM for {label} ...")

                    note_content = call_llm(entry, rule, cfg.llm)

                    note_path = write_note(
                        vault_path=cfg.obsidian_vault,
                        rule=rule,
                        entry=entry,
                        content=note_content,
                        dry_run=cfg.dry_run,
                    )

                    if cfg.dry_run:
                        click.echo(f"  [dry-run] Would write: {note_path}")
                        click.echo("  --- LLM output preview (first 400 chars) ---")
                        click.echo(note_content[:400])
                        click.echo("  ---")
                    else:
                        click.echo(f"  -> Written: {note_path}")

                    if cfg.remove_tag_after_processing and not cfg.dry_run:
                        db.remove_tag_from_entry(entry.id, entry.matched_tag_id)
                        if verbose:
                            click.echo(f"  -> Removed tag '{rule.tag}' from entry.")

                    total_processed += 1

                except Exception as exc:  # noqa: BLE001
                    click.echo(f"  [error] {label}: {exc}", err=True)
                    total_errors += 1

    click.echo(f"\nDone. {total_processed} note(s) processed, {total_errors} error(s).")
    if total_errors:
        sys.exit(1)
