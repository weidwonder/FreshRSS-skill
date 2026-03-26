#!/usr/bin/env python3
"""FreshRSS CLI。"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")

from web_client import AuthenticationError, FreshRSSError, FreshRSSWebClient


def get_client() -> FreshRSSWebClient:
    url = os.getenv("FRESHRSS_URL", "")
    api_url = os.getenv("FRESHRSS_API_URL", "")
    user = os.getenv("FRESHRSS_USERNAME", "")
    pwd = os.getenv("FRESHRSS_API_PASSWORD") or os.getenv("FRESHRSS_PASSWORD", "")

    if not ((url or api_url) and user and pwd):
        print(
            "Error: missing FreshRSS API config.\n"
            "Required: FRESHRSS_USERNAME and one of FRESHRSS_API_PASSWORD/FRESHRSS_PASSWORD,\n"
            "plus one of FRESHRSS_API_URL/FRESHRSS_URL.\n"
            f"Please refer to setup guide: {_script_dir.parent / 'references' / 'setup.md'}",
            file=sys.stderr,
        )
        sys.exit(1)

    client = FreshRSSWebClient(
        base_url=url or api_url,
        username=user,
        password=pwd,
        api_url=api_url or None,
    )
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
    article = client.get_article(args.article_id)
    print(f"Title: {article.title}")
    print(f"Feed: {article.feed_name}  Date: {article.date[:10] if article.date else ''}")
    print(f"URL: {article.url}")
    if article.authors:
        print(f"Author: {article.authors}")
    if article.tags:
        print(f"Tags: {' '.join('#' + t for t in article.tags)}")
    print()
    print(article.content or article.summary or "(no content)")


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
    for feed in feeds:
        if feed.unread_count:
            print(f"  {feed.name}: {feed.unread_count}")
            total += feed.unread_count
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
    except AuthenticationError as exc:
        print(
            f"Authentication error: {exc}\n"
            f"Please check your credentials in: {_script_dir / '.env'}\n"
            f"Setup guide: {_script_dir.parent / 'references' / 'setup.md'}",
            file=sys.stderr,
        )
        sys.exit(1)
    except FreshRSSError as exc:
        print(f"FreshRSS error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
