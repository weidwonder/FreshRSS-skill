#!/usr/bin/env python3
"""FreshRSS CLI - command line interface for FreshRSS."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from script directory
_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")

from web_client import FreshRSSWebClient, FreshRSSError, AuthenticationError


def get_client() -> FreshRSSWebClient:
    url = os.getenv("FRESHRSS_URL", "")
    user = os.getenv("FRESHRSS_USERNAME", "")
    pwd = os.getenv("FRESHRSS_PASSWORD", "")
    if not all([url, user, pwd]):
        print(
            "Error: missing FRESHRSS_URL, FRESHRSS_USERNAME, or FRESHRSS_PASSWORD.\n"
            f"Please refer to setup guide: {_script_dir.parent / 'references' / 'setup.md'}",
            file=sys.stderr,
        )
        sys.exit(1)
    client = FreshRSSWebClient(url, user, pwd)
    client.authenticate()
    return client


def cmd_list_feeds(args):
    client = get_client()
    feeds = client.get_feeds()
    if not feeds:
        print("No feeds found.")
        return
    print("Subscribed feeds:\n")
    for feed in feeds:
        unread = f" ({feed.unread_count} unread)" if feed.unread_count else ""
        print(f"  [{feed.id}] {feed.name}{unread}")


def cmd_get_articles(args):
    client = get_client()
    articles = client.get_articles(
        feed_id=args.feed_id or None,
        count=args.count,
        unread_only=args.unread,
    )
    if not articles:
        print("No articles found.")
        return
    print(f"{len(articles)} articles:\n")
    for a in articles:
        status = "[unread]" if not a.is_read else "[read]"
        star = " [starred]" if a.is_starred else ""
        date = a.date[:10] if a.date else ""
        print(f"{status}{star} [{a.id}] {a.title}")
        print(f"   Feed: {a.feed_name}  Date: {date}")
        print(f"   URL: {a.url}")
        if a.summary:
            print(f"   Summary: {a.summary[:120]}")
        if a.tags:
            print(f"   Tags: {' '.join('#' + t for t in a.tags)}")
        print()


def cmd_get_content(args):
    client = get_client()
    articles = client.get_articles(count=200)
    for a in articles:
        if a.id == args.article_id:
            print(f"Title: {a.title}")
            print(f"Feed: {a.feed_name}  Date: {a.date[:10] if a.date else ''}")
            print(f"URL: {a.url}")
            if a.authors:
                print(f"Author: {a.authors}")
            if a.tags:
                print(f"Tags: {' '.join('#' + t for t in a.tags)}")
            print()
            print(a.content or a.summary or "(no content)")
            return
    print(
        f"Article {args.article_id} not found (may be older than current page)",
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_mark_read(args):
    client = get_client()
    ids = [i.strip() for i in args.article_ids.split(",") if i.strip()]
    if not ids:
        print("No article IDs provided", file=sys.stderr)
        sys.exit(1)
    for aid in ids:
        ok = client.mark_read(aid)
        print(f"{'OK' if ok else 'FAIL'} mark-read {aid}")


def cmd_mark_unread(args):
    client = get_client()
    ids = [i.strip() for i in args.article_ids.split(",") if i.strip()]
    if not ids:
        print("No article IDs provided", file=sys.stderr)
        sys.exit(1)
    for aid in ids:
        ok = client.mark_unread(aid)
        print(f"{'OK' if ok else 'FAIL'} mark-unread {aid}")


def cmd_toggle_star(args):
    client = get_client()
    ok = client.toggle_star(args.article_id)
    print(f"{'OK' if ok else 'FAIL'} toggle-star {args.article_id}")


def cmd_unread_count(args):
    client = get_client()
    feeds = client.get_feeds()
    total = 0
    print("Unread counts:\n")
    for f in feeds:
        if f.unread_count:
            print(f"  {f.name}: {f.unread_count}")
            total += f.unread_count
    print(f"\n  Total: {total} unread")


def main():
    parser = argparse.ArgumentParser(description="FreshRSS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-feeds", help="List all subscribed feeds")

    p_articles = sub.add_parser("get-articles", help="Get articles")
    p_articles.add_argument("--feed-id", default="", help="Filter by feed ID")
    p_articles.add_argument("--count", type=int, default=20, help="Number of articles")
    p_articles.add_argument("--unread", action="store_true", help="Unread only")

    p_content = sub.add_parser("get-content", help="Get article full content")
    p_content.add_argument("article_id", help="Article ID")

    p_read = sub.add_parser("mark-read", help="Mark articles as read")
    p_read.add_argument("article_ids", help="Comma-separated article IDs")

    p_unread = sub.add_parser("mark-unread", help="Mark articles as unread")
    p_unread.add_argument("article_ids", help="Comma-separated article IDs")

    p_star = sub.add_parser("toggle-star", help="Toggle star on article")
    p_star.add_argument("article_id", help="Article ID")

    sub.add_parser("unread-count", help="Get unread counts per feed")

    args = parser.parse_args()

    handlers = {
        "list-feeds": cmd_list_feeds,
        "get-articles": cmd_get_articles,
        "get-content": cmd_get_content,
        "mark-read": cmd_mark_read,
        "mark-unread": cmd_mark_unread,
        "toggle-star": cmd_toggle_star,
        "unread-count": cmd_unread_count,
    }

    try:
        handlers[args.command](args)
    except AuthenticationError as e:
        print(
            f"Authentication error: {e}\n"
            f"Please check your credentials in: {_script_dir / '.env'}\n"
            f"Setup guide: {_script_dir.parent / 'references' / 'setup.md'}",
            file=sys.stderr,
        )
        sys.exit(1)
    except FreshRSSError as e:
        print(f"FreshRSS error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
