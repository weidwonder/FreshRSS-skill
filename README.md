# FreshRSS Skill for Claude Code

**[中文版本 / Chinese Version](README_zh.md)**

A Claude Code skill that connects your AI assistant to your self-hosted [FreshRSS](https://freshrss.org/) instance, enabling natural language interaction with your RSS feeds and articles.

## What It Does

This skill gives Claude Code direct access to your FreshRSS RSS reader. Instead of switching between your terminal and a browser, you can manage your RSS subscriptions conversationally:

- **List feeds** — see all subscribed feeds with unread counts
- **Browse articles** — filter by feed, read status, or count
- **Read full content** — fetch complete article text without leaving the terminal
- **Manage read status** — mark articles as read or unread in batch
- **Star articles** — bookmark important articles for later

## Why Use This Skill

### Natural Language RSS Management

Ask Claude things like "show me unread articles from my tech feeds" or "what's new today?" — no need to remember CLI flags or navigate a web UI.

### Stays in Your Workflow

If you already work in the terminal with Claude Code, this skill keeps your news reading in the same context. Read an article, discuss it with Claude, and continue coding — all in one session.

### Self-Hosted & Private

Connects to your own FreshRSS instance. Your credentials stay local in a `.env` file. No third-party services involved beyond your own server.

### Smart Workflows

Claude can chain commands intelligently: check unread counts, fetch interesting articles, read the full content, then mark them as read — all from a single conversation.

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
# Edit .env with your FreshRSS URL, username, and password
```

3. **Verify**

```bash
.venv/bin/python freshrss_cli.py list-feeds
```

See [references/setup.md](freshrss/references/setup.md) for detailed setup instructions.

## Available Commands

| Command | Description |
|---------|-------------|
| `list-feeds` | List all subscribed feeds with IDs and unread counts |
| `get-articles [--feed-id ID] [--count N] [--unread]` | Get article list with filters |
| `get-content <article_id>` | Get full article content |
| `mark-read <ids>` | Mark articles as read (comma-separated IDs) |
| `mark-unread <ids>` | Mark articles as unread (comma-separated IDs) |
| `toggle-star <article_id>` | Toggle star/bookmark on an article |
| `unread-count` | Get unread counts per feed |

## Example Workflows

**Morning news check:**
> "How many unread articles do I have?" → "Show me the latest 5 from my tech feeds" → "Read the one about Rust" → "Mark them all as read"

**Research bookmark:**
> "Find articles about LLMs in my feeds" → "Star the most relevant ones"

## Technical Details

- Authenticates via FreshRSS's bcrypt challenge mechanism (web session)
- Parses FreshRSS HTML responses directly — no API extension required
- Auto-retries on connection errors with re-authentication
- Dependencies: `requests`, `bcrypt`, `python-dotenv`
