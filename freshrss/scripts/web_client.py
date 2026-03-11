"""FreshRSS Web Session Client - uses bcrypt challenge auth and HTML parsing."""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

import bcrypt
import requests

logger = logging.getLogger(__name__)


class FreshRSSError(Exception):
    pass


class AuthenticationError(FreshRSSError):
    pass


@dataclass
class Feed:
    id: str
    name: str
    url: str = ""
    unread_count: int = 0


@dataclass
class Article:
    id: str
    feed_id: str
    feed_name: str
    title: str
    url: str
    summary: str
    content: str
    authors: str
    date: str
    is_read: bool
    is_starred: bool
    tags: List[str] = field(default_factory=list)


class FreshRSSWebClient:
    """Authenticates via bcrypt challenge and interacts with FreshRSS via HTML parsing."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.freshrss_url = f"{self.base_url}/i"
        self.username = username
        self.password = password
        self._session: Optional[requests.Session] = None
        self._rid: Optional[str] = None
        self._csrf: Optional[str] = None

    def _new_session(self) -> requests.Session:
        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0 FreshRSS-MCP/1.0"
        s.headers["Connection"] = "close"  # Avoid keep-alive reuse issues
        return s

    def _get(self, path: str, retries: int = 2, **kwargs) -> requests.Response:
        url = f"{self.freshrss_url}/{path}"
        last_err = None
        for attempt in range(retries + 1):
            try:
                return self._session.get(url, timeout=20, **kwargs)
            except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                last_err = e
                if attempt < retries:
                    # Re-authenticate on connection reset
                    logger.warning(f"Connection error (attempt {attempt+1}), retrying... {e}")
                    self.authenticate()
        raise last_err

    def _get_csrf(self, body: str) -> str:
        m = re.search(r'"csrf":"([a-f0-9]+)"', body)
        return m.group(1) if m else ""

    def authenticate(self) -> bool:
        """Login via bcrypt challenge mechanism."""
        session = self._new_session()
        try:
            # Step 1: Get nonce and salt1 for this user
            resp = session.get(
                f"{self.freshrss_url}/?c=javascript&a=nonce&user={self.username}",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if "salt1" not in data or "nonce" not in data:
                raise AuthenticationError(f"User '{self.username}' not found")

            # Step 2: Compute bcrypt challenge
            salt1 = data["salt1"].encode()
            nonce = data["nonce"]
            s_hash = bcrypt.hashpw(self.password.encode(), salt1).decode()
            combined = (nonce + s_hash).encode()[:72]
            challenge = bcrypt.hashpw(combined, bcrypt.gensalt(rounds=4)).decode()

            # Step 3: Get CSRF token from login page
            login_page = session.get(
                f"{self.freshrss_url}/?c=auth&a=login", timeout=10
            )
            csrf = self._get_csrf(login_page.text)
            orig = re.search(r'name="original_request" value="([^"]+)"', login_page.text)

            # Step 4: Submit login form
            login_resp = session.post(
                f"{self.freshrss_url}/?c=auth&a=login",
                data={
                    "_csrf": csrf,
                    "username": self.username,
                    "challenge": challenge,
                    "original_request": orig.group(1) if orig else "",
                },
                timeout=10,
            )

            # Extract rid from redirect URL
            rid_match = re.search(r"rid=([a-f0-9]+)", login_resp.url)
            if not rid_match:
                raise AuthenticationError("Login failed - no rid in response URL")

            self._session = session
            self._rid = rid_match.group(1)
            # Refresh CSRF for subsequent requests
            self._csrf = self._get_csrf(login_resp.text)
            logger.info(f"Authenticated as '{self.username}', rid={self._rid}")
            return True

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e

    def _ensure_auth(self):
        if self._session is None or self._rid is None:
            self.authenticate()

    def _refresh_csrf(self):
        """Re-fetch CSRF from main page."""
        r = self._get(f"?rid={self._rid}")
        self._csrf = self._get_csrf(r.text)

    def get_feeds(self) -> List[Feed]:
        """Get list of subscribed feeds from sidebar HTML."""
        self._ensure_auth()
        r = self._get(f"?rid={self._rid}")
        body = r.text

        feeds = []
        # Parse feed entries from sidebar: data-feed="ID" with feed name
        # FreshRSS sidebar uses: ?get=f_ID links with feed names
        for m in re.finditer(
            r'href="[^"]*[?&]get=f_(\d+)[^"]*"[^>]*>\s*'
            r'(?:<img[^>]*>\s*)?<span[^>]*class="[^"]*nav-site-title[^"]*"[^>]*>([^<]+)</span>',
            body,
        ):
            feeds.append(Feed(id=m.group(1), name=m.group(2).strip()))

        if not feeds:
            # Fallback: parse from data-feed attributes
            feed_ids = set(re.findall(r'data-feed="(\d+)"', body))
            feed_names = {}
            for m in re.finditer(
                r'data-feed="(\d+)".*?data-website-name="([^"]*)"', body, re.DOTALL
            ):
                feed_names[m.group(1)] = m.group(2)
            for fid in sorted(feed_ids):
                feeds.append(Feed(id=fid, name=feed_names.get(fid, f"Feed {fid}")))

        # Get unread counts from sidebar
        for m in re.finditer(
            r'data-id="(\d+)"[^>]*>\s*<span[^>]*>(\d+)</span>', body
        ):
            for feed in feeds:
                if feed.id == m.group(1):
                    feed.unread_count = int(m.group(2))

        return feeds

    def _parse_articles(self, body: str) -> List[Article]:
        """Parse article list from FreshRSS HTML page."""
        articles = []

        # Find all flux divs: <div class="flux [not_read]" data-entry="ID" data-feed="FID" ...>
        flux_blocks = re.finditer(
            r'<div class="flux([^"]*?)"[^>]*data-entry="(\d+)"[^>]*data-feed="(\d+)"[^>]*>(.*?)'
            r'(?=<div class="flux|<div id="new-article"|</main>)',
            body,
            re.DOTALL,
        )

        for block in flux_blocks:
            classes = block.group(1)
            entry_id = block.group(2)
            feed_id = block.group(3)
            content = block.group(4)

            is_read = "not_read" not in classes
            is_starred = "favorite" in classes or "starred" in classes

            # Feed name
            feed_name_m = re.search(r'data-website-name="([^"]*)"', content)
            feed_name = feed_name_m.group(1) if feed_name_m else ""

            # Authors
            authors_m = re.search(r'data-article-authors="([^"]*)"', content)
            authors = authors_m.group(1) if authors_m else ""

            # Title and URL - attribute order may vary, extract independently
            title_anchor = re.search(r'<a[^>]*class="[^"]*item-element title[^"]*"[^>]*>(.*?)</a>', content, re.DOTALL)
            if title_anchor:
                title = re.sub(r"<[^>]+>", "", title_anchor.group(1)).strip()
                url_m = re.search(r'href="([^"]*)"', title_anchor.group(0))
                url = url_m.group(1) if url_m else ""
            else:
                title = ""
                url = ""

            # Date
            date_m = re.search(r'<time[^>]+datetime="([^"]+)"', content)
            date_str = date_m.group(1) if date_m else ""

            # Summary
            summary_m = re.search(r'<div class="summary">([^<]*)</div>', content)
            summary = summary_m.group(1).strip() if summary_m else ""

            # Full content text (strip HTML tags)
            text_m = re.search(r'<div class="text">(.*?)</div>\s*</div>', content, re.DOTALL)
            if text_m:
                raw = text_m.group(1)
                content_text = re.sub(r"<[^>]+>", " ", raw)
                content_text = re.sub(r"\s+", " ", content_text).strip()
            else:
                content_text = summary

            # Tags
            tags = re.findall(r'<a class="link-tag"[^>]*>#(\w+)</a>', content)

            # Check if starred via icon
            bookmark_m = re.search(r'<a[^>]*class="[^"]*bookmark[^"]*"[^>]*>', content)
            if bookmark_m:
                is_starred = "non-starred" not in content[
                    bookmark_m.start() : bookmark_m.start() + 200
                ]

            articles.append(
                Article(
                    id=entry_id,
                    feed_id=feed_id,
                    feed_name=feed_name,
                    title=title,
                    url=url,
                    summary=summary,
                    content=content_text,
                    authors=authors,
                    date=date_str,
                    is_read=is_read,
                    is_starred=is_starred,
                    tags=tags,
                )
            )

        return articles

    def get_articles(
        self,
        feed_id: Optional[str] = None,
        count: int = 20,
        unread_only: bool = False,
    ) -> List[Article]:
        """Get articles, optionally filtered by feed."""
        self._ensure_auth()

        params = f"nb={min(count, 200)}&rid={self._rid}"
        if feed_id:
            params += f"&f={feed_id}"

        r = self._get(f"?{params}")
        articles = self._parse_articles(r.text)

        if unread_only:
            articles = [a for a in articles if not a.is_read]

        return articles[:count]

    def mark_read(self, entry_id: str) -> bool:
        """Mark an article as read."""
        self._ensure_auth()
        r = self._get(f"?c=entry&a=read&id={entry_id}&rid={self._rid}")
        return r.status_code == 200

    def mark_unread(self, entry_id: str) -> bool:
        """Mark an article as unread."""
        self._ensure_auth()
        r = self._get(f"?c=entry&a=unread&id={entry_id}&rid={self._rid}")
        return r.status_code == 200

    def toggle_star(self, entry_id: str) -> bool:
        """Toggle star/bookmark on an article."""
        self._ensure_auth()
        r = self._get(f"?c=entry&a=bookmark&id={entry_id}&rid={self._rid}")
        return r.status_code == 200

    def get_unread_counts(self) -> dict:
        """Get unread count per feed."""
        feeds = self.get_feeds()
        return {f.name: f.unread_count for f in feeds}
