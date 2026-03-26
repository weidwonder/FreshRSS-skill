---
name: freshrss
description: >
  Interact with a FreshRSS RSS reader instance through the FreshRSS API - list
  feeds, read articles, mark read/unread, star articles, and get unread counts.
  Use when the user mentions RSS, news feeds, FreshRSS, reading articles,
  checking unread items, or managing RSS subscriptions.
---

# FreshRSS

Manage RSS feeds and articles on a FreshRSS instance via CLI.

## Commands

All commands follow this pattern:

```bash
<skill_dir>/scripts/.venv/bin/python <skill_dir>/scripts/freshrss_cli.py <command> [args]
```

Where `<skill_dir>` is the directory containing this SKILL.md.

| Command | Description |
|---------|-------------|
| `list-feeds` | List all subscribed feeds with IDs and unread counts |
| `get-articles [--feed-id ID] [--count N] [--unread]` | Get article list |
| `get-content <article_id>` | Get full article content |
| `mark-read <ids>` | Mark as read (comma-separated IDs) |
| `mark-unread <ids>` | Mark as unread (comma-separated IDs) |
| `toggle-star <article_id>` | Toggle star/bookmark |
| `unread-count` | Get unread counts per feed |

## Configuration

Recommended environment variables in `scripts/.env`:

```dotenv
FRESHRSS_URL=http://your-freshrss-host:1201
FRESHRSS_API_URL=http://your-freshrss-host:1201/api/greader.php
FRESHRSS_USERNAME=your-username
FRESHRSS_API_PASSWORD=your-api-password
```

Compatibility fallback:

```dotenv
FRESHRSS_PASSWORD=your-password
```

The CLI accepts either `FRESHRSS_URL` or `FRESHRSS_API_URL`. If both are set, `FRESHRSS_API_URL` wins.

## Examples

```bash
# Check unread overview
<skill_dir>/scripts/.venv/bin/python <skill_dir>/scripts/freshrss_cli.py unread-count

# Get 10 unread articles from feed 3
<skill_dir>/scripts/.venv/bin/python <skill_dir>/scripts/freshrss_cli.py get-articles --feed-id 3 --count 10 --unread

# Read a full article by short item ID
<skill_dir>/scripts/.venv/bin/python <skill_dir>/scripts/freshrss_cli.py get-content 00064dec964114be

# Mark articles as read
<skill_dir>/scripts/.venv/bin/python <skill_dir>/scripts/freshrss_cli.py mark-read 00064dec964114be,00064dd80d49a44e
```

## Typical Workflows

**Check what's new:** `unread-count` -> `get-articles --unread` -> `get-content <id>` -> `mark-read <ids>`

**Browse a feed:** `list-feeds` -> `get-articles --feed-id <id>` -> `toggle-star <id>`

## Error Handling

If a command fails with missing credentials or authentication errors, the CLI prints an error with a path to `references/setup.md`. Follow that guide to configure the FreshRSS API endpoint and credentials.
