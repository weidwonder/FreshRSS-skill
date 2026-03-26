# FreshRSS Skill for Claude Code

**[中文版本 / Chinese Version](README_zh.md)**

A Claude Code skill that connects your AI assistant to a self-hosted [FreshRSS](https://freshrss.org/) instance through the FreshRSS API, so you can browse feeds and manage articles in natural language.

## What It Does

This skill gives Claude Code direct access to your FreshRSS reader without relying on fragile web-page parsing:

- **List feeds** — show subscribed feeds with unread counts
- **Browse articles** — filter by feed, unread status, or count
- **Read full content** — fetch a specific article by ID from the API
- **Manage read state** — mark entries read or unread in batch
- **Star articles** — toggle the FreshRSS starred state

## Why This Version Is Better

### API-first and reliable

The skill now uses FreshRSS's Google Reader compatible API instead of HTML parsing and browser-session tricks. That makes login, listing, and state changes much more stable.

### Keeps the CLI stable

Existing commands are preserved:

- `list-feeds`
- `get-articles [--feed-id ID] [--count N] [--unread]`
- `get-content <article_id>`
- `mark-read <ids>`
- `mark-unread <ids>`
- `toggle-star <article_id>`
- `unread-count`

### Flexible deployment

You can point the skill at either:

- `FRESHRSS_URL` — the FreshRSS base URL, and the client derives `/api/greader.php`
- `FRESHRSS_API_URL` — the exact Google Reader API endpoint, useful when the API is exposed via another host or reverse proxy

## Quick Start

1. **Install dependencies**

```bash
cd freshrss/scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

2. **Configure credentials**

```bash
cp .env.example .env
```

Recommended `.env`:

```dotenv
FRESHRSS_URL=http://your-freshrss-host:1201
FRESHRSS_API_URL=http://your-freshrss-host:1201/api/greader.php
FRESHRSS_USERNAME=your-username
FRESHRSS_API_PASSWORD=your-api-password
```

Compatibility fallback is still supported:

```dotenv
FRESHRSS_PASSWORD=your-password
```

3. **Verify**

```bash
.venv/bin/python freshrss_cli.py list-feeds
.venv/bin/python freshrss_cli.py unread-count
.venv/bin/python freshrss_cli.py get-articles --unread --count 3
```

See [references/setup.md](freshrss/references/setup.md) for setup details.

## Available Commands

| Command | Description |
|---------|-------------|
| `list-feeds` | List all subscribed feeds with IDs and unread counts |
| `get-articles [--feed-id ID] [--count N] [--unread]` | Get article list with filters |
| `get-content <article_id>` | Fetch a specific article by ID |
| `mark-read <ids>` | Mark articles as read (comma-separated IDs) |
| `mark-unread <ids>` | Mark articles as unread (comma-separated IDs) |
| `toggle-star <article_id>` | Toggle star/bookmark on an article |
| `unread-count` | Get unread counts per feed |

## Notes About Article IDs

The API returns Google Reader item IDs. The CLI displays the short item ID suffix, and commands accept either:

- short form like `00064dec964114be`
- full form like `tag:google.com,2005:reader/item/00064dec964114be`

## Lightweight Verification

To quickly verify unread state consistency:

```bash
.venv/bin/python freshrss_cli.py unread-count
.venv/bin/python freshrss_cli.py get-articles --unread --count 5
```

If `unread-count` shows unread items for a feed, `get-articles --unread` should return entries whose status is shown as `[unread]`.

A simple round-trip check for one article is:

```bash
.venv/bin/python freshrss_cli.py mark-read <article_id>
.venv/bin/python freshrss_cli.py mark-unread <article_id>
```

## Technical Details

- Uses the FreshRSS Google Reader compatible API at `/api/greader.php`
- Authenticates with `accounts/ClientLogin`
- Uses `/reader/api/0/token` + `/reader/api/0/edit-tag` for read/unread/star changes
- Converts article HTML snippets to readable text only after the API returns structured item data
- Dependencies: `requests`, `python-dotenv`
