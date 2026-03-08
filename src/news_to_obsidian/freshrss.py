"""FreshRSS SQLite database access layer."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator


@dataclass
class Entry:
    """A FreshRSS entry (article/news item)."""

    id: int
    title: str
    author: str
    link: str
    date: datetime
    content: str
    feed_name: str
    feed_website: str
    # The FreshRSS label (tag) that matched this entry
    matched_tag: str
    matched_tag_id: int


class FreshRSSDB:
    """Read-write access to the FreshRSS SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        # Ensure foreign key enforcement
        self._conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FreshRSSDB":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_tag_id(self, tag_name: str) -> int | None:
        """Return the id of a tag by name, or None if not found."""
        row = self._conn.execute(
            "SELECT id FROM tag WHERE name = ?", (tag_name,)
        ).fetchone()
        return row["id"] if row else None

    def entries_for_tag(self, tag_name: str) -> list[Entry]:
        """Return all entries that carry the given label/tag."""
        rows = self._conn.execute(
            """
            SELECT
                e.id,
                e.title,
                e.author,
                e.link,
                e.date,
                e.content,
                f.name  AS feed_name,
                f.website AS feed_website,
                t.id    AS tag_id
            FROM entry e
            JOIN feed f ON f.id = e.id_feed
            JOIN entrytag et ON et.id_entry = e.id
            JOIN tag t ON t.id = et.id_tag
            WHERE t.name = ?
            ORDER BY e.date ASC
            """,
            (tag_name,),
        ).fetchall()

        entries = []
        for row in rows:
            ts = row["date"]
            dt = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                if ts
                else datetime.now(tz=timezone.utc)
            )
            entries.append(
                Entry(
                    id=row["id"],
                    title=self._decode(row["title"]),
                    author=self._decode(row["author"]).lstrip(";"),
                    link=row["link"] or "",
                    date=dt,
                    content=self._decode(row["content"]),
                    feed_name=self._decode(row["feed_name"]),
                    feed_website=row["feed_website"] or "",
                    matched_tag=tag_name,
                    matched_tag_id=row["tag_id"],
                )
            )
        return entries

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def remove_tag_from_entry(self, entry_id: int, tag_id: int) -> None:
        """Remove a label from a single entry (does not delete the tag itself)."""
        self._conn.execute(
            "DELETE FROM entrytag WHERE id_entry = ? AND id_tag = ?",
            (entry_id, tag_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
