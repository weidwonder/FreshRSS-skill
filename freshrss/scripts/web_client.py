"""基于 FreshRSS Google Reader API 的客户端。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

READING_LIST_STREAM = "user/-/state/com.google/reading-list"
READ_TAG = "user/-/state/com.google/read"
STARRED_TAG = "user/-/state/com.google/starred"
LABEL_PREFIX = "user/-/label/"
ITEM_ID_PREFIX = "tag:google.com,2005:reader/item/"


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


class _HTMLTextExtractor(HTMLParser):
    _BLOCK_TAGS = {
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._BLOCK_TAGS:
            self._append_break()

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self._append_break()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._parts and not self._parts[-1].endswith(("\n", " ")):
            self._parts.append(" ")
        self._parts.append(text)

    def text(self) -> str:
        joined = "".join(self._parts)
        lines = [line.strip() for line in joined.splitlines()]
        return "\n".join(line for line in lines if line)

    def _append_break(self) -> None:
        if self._parts and self._parts[-1] != "\n":
            self._parts.append("\n")


class FreshRSSWebClient:
    """通过 Google Reader 兼容 API 访问 FreshRSS。"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        api_url: Optional[str] = None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_url = self._build_api_url(self.base_url, api_url)
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "FreshRSS-CLI/2.0",
                "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
            }
        )
        self._auth_token: Optional[str] = None
        self._edit_token: Optional[str] = None

    @staticmethod
    def _build_api_url(base_url: str, api_url: Optional[str]) -> str:
        candidate = (api_url or base_url or "").rstrip("/")
        if not candidate:
            raise FreshRSSError(
                "缺少 FreshRSS 地址，请配置 FRESHRSS_API_URL 或 FRESHRSS_URL。"
            )
        if candidate.endswith("/api/greader.php"):
            return candidate
        if candidate.endswith("/api"):
            return f"{candidate}/greader.php"
        return f"{candidate}/api/greader.php"

    @staticmethod
    def _parse_key_value_response(body: str) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for line in body.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _normalize_feed_stream(feed_id: Optional[str]) -> str:
        if not feed_id:
            return READING_LIST_STREAM
        return feed_id if feed_id.startswith("feed/") else f"feed/{feed_id}"

    @staticmethod
    def _normalize_article_id(article_id: str) -> str:
        article_id = article_id.strip()
        if article_id.startswith(ITEM_ID_PREFIX):
            return article_id
        if "/reader/item/" in article_id:
            return article_id
        return f"{ITEM_ID_PREFIX}{article_id}"

    @staticmethod
    def _short_article_id(article_id: str) -> str:
        return article_id.rsplit("/", 1)[-1]

    @staticmethod
    def _strip_html(value: str) -> str:
        if not value:
            return ""
        parser = _HTMLTextExtractor()
        parser.feed(unescape(value))
        parser.close()
        return parser.text()

    @staticmethod
    def _iso_datetime(timestamp: Optional[int]) -> str:
        if not timestamp:
            return ""
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        require_auth: bool = True,
        timeout: int = 20,
    ) -> requests.Response:
        headers = {}
        if require_auth:
            self._ensure_auth()
            headers["Authorization"] = f"GoogleLogin auth={self._auth_token}"

        url = f"{self.api_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise FreshRSSError(f"请求 FreshRSS API 失败：{exc}") from exc

        if response.status_code in (401, 403):
            self._auth_token = None
            self._edit_token = None
            details = response.text.strip() or "未提供错误详情"
            raise AuthenticationError(
                "FreshRSS API 认证失败。"
                "请确认 API 已启用，并优先使用 FreshRSS 的 API 密码"
                f"（当前接口：{self.api_url}，详情：{details}）。"
            )

        if response.status_code == 404:
            raise FreshRSSError(
                f"FreshRSS API 地址不可用：{url}。"
                "请检查 FRESHRSS_API_URL 或 FRESHRSS_URL 是否正确。"
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            details = response.text.strip()
            raise FreshRSSError(
                f"FreshRSS API 请求失败：HTTP {response.status_code} {details}"
            ) from exc

        return response

    def _request_json(self, method: str, path: str, **kwargs) -> dict:
        response = self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise FreshRSSError(
                f"FreshRSS API 返回了无法解析的 JSON：{response.text[:200]}"
            ) from exc

    def authenticate(self) -> bool:
        if not self.username or not self.password:
            raise AuthenticationError(
                "缺少 FreshRSS 用户名或密码，请配置 FRESHRSS_USERNAME 和 "
                "FRESHRSS_API_PASSWORD（或兼容使用 FRESHRSS_PASSWORD）。"
            )

        response = self._request(
            "POST",
            "/accounts/ClientLogin",
            data={"Email": self.username, "Passwd": self.password},
            require_auth=False,
            timeout=10,
        )
        values = self._parse_key_value_response(response.text)
        auth_token = values.get("Auth")
        if not auth_token:
            error_code = values.get("Error") or response.text.strip() or "未知错误"
            raise AuthenticationError(
                "FreshRSS Google Reader API 登录失败。"
                f"返回信息：{error_code}。"
                "请检查用户名/密码，若已启用 API 密码，请使用 FRESHRSS_API_PASSWORD。"
            )

        self._auth_token = auth_token
        self._edit_token = None
        logger.info("已通过 Google Reader API 登录 FreshRSS：%s", self.username)
        return True

    def _ensure_auth(self) -> None:
        if not self._auth_token:
            self.authenticate()

    def _get_edit_token(self) -> str:
        if not self._edit_token:
            response = self._request("GET", "/reader/api/0/token")
            token = response.text.strip()
            if not token:
                raise FreshRSSError("无法获取 FreshRSS 编辑令牌。")
            self._edit_token = token
        return self._edit_token

    def _get_item_categories(self, article_id: str) -> List[str]:
        article = self.get_article(article_id)
        categories = [READING_LIST_STREAM]
        categories.extend(f"{LABEL_PREFIX}{tag}" for tag in article.tags)
        if article.is_read:
            categories.append(READ_TAG)
        if article.is_starred:
            categories.append(STARRED_TAG)
        return categories

    def _parse_article(self, item: dict) -> Article:
        categories = item.get("categories") or []
        origin = item.get("origin") or {}
        feed_stream_id = origin.get("streamId", "")
        summary_html = (item.get("summary") or {}).get("content", "")
        content_html = (item.get("content") or {}).get("content", summary_html)
        url = ""
        alternates = item.get("alternate") or item.get("canonical") or []
        if alternates:
            url = alternates[0].get("href", "")

        authors = item.get("author") or ""
        if isinstance(authors, list):
            authors = ", ".join(str(author) for author in authors if author)

        tags = [tag[len(LABEL_PREFIX) :] for tag in categories if tag.startswith(LABEL_PREFIX)]

        return Article(
            id=self._short_article_id(item.get("id", "")),
            feed_id=feed_stream_id.split("/", 1)[-1] if feed_stream_id.startswith("feed/") else feed_stream_id,
            feed_name=origin.get("title", ""),
            title=item.get("title", "") or "(untitled)",
            url=url,
            summary=self._strip_html(summary_html),
            content=self._strip_html(content_html),
            authors=authors,
            date=self._iso_datetime(item.get("published")),
            is_read=READ_TAG in categories,
            is_starred=STARRED_TAG in categories,
            tags=tags,
        )

    def _fetch_stream_items(
        self,
        stream_id: str,
        *,
        count: int,
        unread_only: bool,
    ) -> List[dict]:
        items: List[dict] = []
        continuation: Optional[str] = None
        encoded_stream_id = quote(stream_id, safe="/-.:")

        while len(items) < count:
            remaining = max(count - len(items), 1)
            params = {"n": min(remaining, 1000), "output": "json"}
            if unread_only:
                params["xt"] = READ_TAG
            if continuation:
                params["c"] = continuation

            payload = self._request_json(
                "GET",
                f"/reader/api/0/stream/contents/{encoded_stream_id}",
                params=params,
            )
            batch = payload.get("items") or []
            items.extend(batch)
            continuation = payload.get("continuation")
            if not continuation or not batch:
                break

        return items[:count]

    def get_feeds(self) -> List[Feed]:
        subscriptions = self._request_json(
            "GET", "/reader/api/0/subscription/list", params={"output": "json"}
        )
        unread_payload = self._request_json(
            "GET", "/reader/api/0/unread-count", params={"output": "json"}
        )

        unread_by_feed: Dict[str, int] = {}
        for entry in unread_payload.get("unreadcounts") or []:
            raw_id = entry.get("id", "")
            if raw_id.startswith("feed/"):
                unread_by_feed[raw_id.split("/", 1)[1]] = int(entry.get("count", 0))

        feeds: List[Feed] = []
        for subscription in subscriptions.get("subscriptions") or []:
            raw_id = subscription.get("id", "")
            feed_id = raw_id.split("/", 1)[1] if raw_id.startswith("feed/") else raw_id
            feed_url = subscription.get("htmlUrl") or subscription.get("url") or ""
            feeds.append(
                Feed(
                    id=feed_id,
                    name=subscription.get("title", f"Feed {feed_id}"),
                    url=feed_url,
                    unread_count=unread_by_feed.get(feed_id, 0),
                )
            )

        return feeds

    def get_articles(
        self,
        feed_id: Optional[str] = None,
        count: int = 20,
        unread_only: bool = False,
    ) -> List[Article]:
        stream_id = self._normalize_feed_stream(feed_id)
        items = self._fetch_stream_items(
            stream_id,
            count=max(count, 1),
            unread_only=unread_only,
        )
        return [self._parse_article(item) for item in items]

    def get_article(self, article_id: str) -> Article:
        payload = self._request_json(
            "POST",
            "/reader/api/0/stream/items/contents",
            data={
                "i": self._normalize_article_id(article_id),
                "output": "json",
            },
        )
        items = payload.get("items") or []
        if not items:
            raise FreshRSSError(f"未找到文章：{article_id}")
        return self._parse_article(items[0])

    def _edit_tag(self, article_id: str, *, add: Optional[str] = None, remove: Optional[str] = None) -> bool:
        data = {
            "i": self._normalize_article_id(article_id),
            "T": self._get_edit_token(),
        }
        if add:
            data["a"] = add
        if remove:
            data["r"] = remove

        response = self._request("POST", "/reader/api/0/edit-tag", data=data)
        return response.text.strip() == "OK"

    def mark_read(self, entry_id: str) -> bool:
        return self._edit_tag(entry_id, add=READ_TAG)

    def mark_unread(self, entry_id: str) -> bool:
        return self._edit_tag(entry_id, remove=READ_TAG)

    def toggle_star(self, entry_id: str) -> bool:
        categories = self._get_item_categories(entry_id)
        if STARRED_TAG in categories:
            return self._edit_tag(entry_id, remove=STARRED_TAG)
        return self._edit_tag(entry_id, add=STARRED_TAG)

    def get_unread_counts(self) -> Dict[str, int]:
        return {feed.name: feed.unread_count for feed in self.get_feeds()}
