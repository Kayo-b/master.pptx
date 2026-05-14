from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from googlenewsdecoder import gnewsdecoder


@dataclass(slots=True)
class NewsItem:
    title: str
    google_url: str
    article_url: str
    published_at: datetime
    source_name: str | None
    source_site: str | None


_SKIP_DOMAINS = {"instagram.com", "www.instagram.com", "x.com", "twitter.com", "www.youtube.com", "youtube.com", "tiktok.com", "www.tiktok.com"}


def _fetch_xml(url: str) -> str:
    request = Request(url, headers={"User-Agent": "master-pptx-mvp/0.1"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _google_news_rss_url(query: str, hours: int, hl: str, gl: str, ceid: str) -> str:
    q = f"{query} when:{hours}h" if hours > 0 else query
    return "https://news.google.com/rss/search?" + urlencode(
        {"q": q, "hl": hl, "gl": gl, "ceid": ceid}
    )


def _decode_google_news_url(url: str) -> str | None:
    result = gnewsdecoder(url, interval=1)
    if result.get("status") is True and result.get("decoded_url"):
        return str(result["decoded_url"])
    return None


def parse_google_news_feed(
    xml_text: str,
    *,
    limit: int,
    min_published_at: datetime | None,
    decode_url: Callable[[str], str | None] = _decode_google_news_url,
) -> list[NewsItem]:
    root = ElementTree.fromstring(xml_text)
    items: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        raw_link = (item.findtext("link") or "").strip()
        raw_title = (item.findtext("title") or "").strip()
        raw_pub_date = (item.findtext("pubDate") or "").strip()
        if not raw_link or not raw_title or not raw_pub_date:
            continue
        published_at = parsedate_to_datetime(raw_pub_date)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        published_at = published_at.astimezone(UTC)
        if min_published_at and published_at < min_published_at:
            continue
        article_url = decode_url(raw_link)
        if not article_url:
            continue
        if urlparse(article_url).netloc.lower() in _SKIP_DOMAINS:
            continue
        source_element = item.find("source")
        source_name = source_element.text.strip() if source_element is not None and source_element.text else None
        source_site = source_element.get("url") if source_element is not None else None
        title = raw_title.rsplit(" - ", 1)[0] if source_name and raw_title.endswith(f" - {source_name}") else raw_title
        items.append(
            NewsItem(
                title=title,
                google_url=raw_link,
                article_url=article_url,
                published_at=published_at,
                source_name=source_name,
                source_site=source_site,
            )
        )
        if len(items) >= limit:
            break
    return items


def fetch_google_news_items(
    query: str,
    *,
    hours: int = 4,
    limit: int = 10,
    hl: str = "pt-BR",
    gl: str = "BR",
    ceid: str = "BR:pt-419",
) -> list[NewsItem]:
    rss_url = _google_news_rss_url(query, hours, hl, gl, ceid)
    xml_text = _fetch_xml(rss_url)
    min_published_at = datetime.now(UTC) - timedelta(hours=hours) if hours > 0 else None
    return parse_google_news_feed(xml_text, limit=limit, min_published_at=min_published_at)
