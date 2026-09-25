from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Optional

import yaml

from ..config import BASE_DIR
from ..models import HttpCache
from ..timeutil import utcnow
from . import http
from .base import NewsObs, NewsProvider

FEEDS_PATH = BASE_DIR / "data" / "feeds.yaml"
_TAG = re.compile(r"<[^>]+>")


def load_feeds(path=FEEDS_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("feeds", [])


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _text(el: ET.Element, *names: str) -> Optional[str]:
    for child in el:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return None


def _clean(s: Optional[str], limit: int = 500) -> Optional[str]:
    if not s:
        return None
    return unescape(_TAG.sub(" ", s)).strip()[:limit] or None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_feed(xml_text: str, source: str, currency: Optional[str]) -> list[NewsObs]:
    """Handles RSS 2.0, RSS 1.0 (RDF) and Atom."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        return []
    out: list[NewsObs] = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        title = _clean(_text(el, "title"), 400)
        link = _text(el, "link")
        if not link:  # Atom style <link href="..."/>
            for child in el:
                if _local(child.tag) == "link" and child.get("href"):
                    link = child.get("href")
                    break
        if not title or not link:
            continue
        when = _parse_dt(_text(el, "pubdate", "published", "updated", "date")) or utcnow()
        out.append(NewsObs(headline=title, published_at=when, source=source, source_url=link.strip(),
                           summary=_clean(_text(el, "description", "summary", "content")), currency=currency))
    return out


class RssNews(NewsProvider):
    name = "rss"
    requires_key = False

    def __init__(self, feeds: Optional[list[dict]] = None) -> None:
        self.feeds = feeds if feeds is not None else load_feeds()
        self.errors: list[str] = []

    def fetch(self, session=None) -> list[NewsObs]:
        self.errors = []
        out: list[NewsObs] = []
        for feed in self.feeds:
            url = feed["url"]
            headers: dict[str, str] = {}
            cache = session.get(HttpCache, url) if session is not None else None
            if cache and cache.etag:
                headers["If-None-Match"] = cache.etag
            if cache and cache.last_modified:
                headers["If-Modified-Since"] = cache.last_modified
            try:
                r = http.get(url, headers=headers, allow_304=True, retries=1, timeout=15)
            except Exception as e:  # noqa: BLE001 - one dead feed must not break the rest
                self.errors.append(f"{feed['name']}: {e}")
                continue
            if r.status_code == 304:
                continue
            if session is not None:
                if cache is None:
                    cache = HttpCache(url=url)
                    session.add(cache)
                cache.etag = r.headers.get("etag")
                cache.last_modified = r.headers.get("last-modified")
                session.flush()
            items = parse_feed(r.text, feed["name"], feed.get("currency"))
            if not items and r.text.strip():
                self.errors.append(f"{feed['name']}: feed parsed to zero items")
            out += items
        return out
