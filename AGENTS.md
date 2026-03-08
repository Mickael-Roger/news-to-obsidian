# news-to-obsidian — Agent Guidelines

## Overview

Bridge application between **FreshRSS** (RSS aggregator with LLM-enriched articles) and **Obsidian** (note-keeping vault).

The app reads the FreshRSS **SQLite database** directly, looks for entries carrying specific user-defined labels (FreshRSS "tags"), sends each entry to an LLM with a user-defined consign, writes the result as a Markdown note in Obsidian, then removes the label so the entry is not processed again.

## Key Files

| File | Purpose |
|------|---------|
| `src/news_to_obsidian/config.py` | YAML config loading (`Config`, `LLMConfig`, `TagRule`) |
| `src/news_to_obsidian/freshrss.py` | SQLite read/write (`FreshRSSDB`, `Entry`) |
| `src/news_to_obsidian/llm.py` | LLM call via openai SDK (OpenAI-compatible); prompt construction |
| `src/news_to_obsidian/obsidian.py` | Obsidian note writing (frontmatter + content) |
| `src/news_to_obsidian/cli.py` | Click CLI entry point (`news-to-obsidian`) |
| `config.example.yaml` | Annotated example configuration |
| `pyproject.toml` | Project metadata and dependencies |
| `db.sqlite` | Local copy of the FreshRSS DB (for development) |

## Database Schema (relevant tables)

- `entry` — articles: `id`, `title`, `author`, `content` (HTML), `link`, `date` (Unix ts), `id_feed`
- `tag` — FreshRSS labels: `id`, `name`
- `entrytag` — many-to-many: `id_tag`, `id_entry`
- `feed` — RSS feeds: `id`, `name`, `website`

The `author` field is prefixed with `;` in the DB — strip it on read (done in `freshrss.py`).

## Architecture

```
config.yaml
     │
     ▼
Config.from_file()
     │
     ├─► FreshRSSDB.entries_for_tag(tag)  ── JOIN entry + feed + entrytag + tag
     │
     ├─► call_llm(entry, rule, llm_cfg)   ── openai.chat.completions.create()
     │        └── build_user_message()    ── consign + metadata + (optional) HTML→MD content
     │
     ├─► write_note(vault, rule, entry, content)
     │        └── frontmatter + LLM output → .md file
     │
     └─► FreshRSSDB.remove_tag_from_entry(entry_id, tag_id)
```

## Configuration Format

```yaml
freshrss_db: ~/path/to/db.sqlite
obsidian_vault: ~/path/to/vault
remove_tag_after_processing: true

llm:
  model: glm-4-flash            # model name as expected by the endpoint
  api_key: ""                   # or set OPENAI_API_KEY env var
  base_url: "https://open.bigmodel.cn/api/paas/v4/"  # any OpenAI-compatible endpoint

rules:
  - tag: "My FreshRSS label"
    consign: |
      Detailed instruction for the LLM...
    output_folder: "Subfolder/In/Vault"     # optional
    filename_template: "{date}-{title}"     # optional; supports {title},{date},{feed},{id}
    include_content: true                   # send HTML article content to LLM
```

## Development Setup

```bash
uv venv .venv
uv pip install -e .
.venv/bin/news-to-obsidian --help
```

## Running

```bash
# Normal run
.venv/bin/news-to-obsidian --config config.yaml

# Dry-run (no writes, no tag removal)
.venv/bin/news-to-obsidian --config config.yaml --dry-run

# Process only specific tag(s)
.venv/bin/news-to-obsidian --config config.yaml --tag "To Note"

# Verbose output
.venv/bin/news-to-obsidian --config config.yaml --verbose
```

## Cron example

```cron
*/15 * * * * /path/to/.venv/bin/news-to-obsidian --config /path/to/config.yaml >> /var/log/news-to-obsidian.log 2>&1
```

## Lessons Learned

- The FreshRSS `author` column is prefixed with `;` — always strip it.
- The FreshRSS DB uses Unix timestamps (seconds) for `entry.date`.
- Tag removal must target the `entrytag` join table, not the `tag` table itself.
- Use `uv pip install -e .` on NixOS (system Python is externally managed).
- The openai SDK is used for LLM calls; it works with any OpenAI-compatible endpoint via `base_url`.
- `api_key` defaults to the `OPENAI_API_KEY` env var if not set in config; set `"no-key"` is used as placeholder when key is empty (some local endpoints require a non-empty string).
