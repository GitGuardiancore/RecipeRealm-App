"""SignalInterceptor: fetches human signals for the alien to observe.

Signals come from two sources:
  1. RSS feeds (news headlines, tech blogs, science journals). These are
     the "electromagnetic emissions" the alien is intercepting.
  2. A manual queue for injecting specific topics during testing or for
     curating the agent's focus areas.

The interceptor does not interpret signals. It fetches, deduplicates, and
yields them. Interpretation is the SignalInterpreter's job.

Deduplication uses a simple in-memory set of headline hashes. The set is
bounded to prevent unbounded growth — once it hits 2000 entries, the
oldest half is evicted. This is a soft dedup, not a guarantee. Two RSS
feeds reporting the same event with different headlines will both pass.
That is acceptable; the alien seeing two perspectives on the same event
is realistic, not a bug.

Feed URLs are configured via environment variable or constructor arg.
The default set covers a broad cross-section of human activity: general
news, technology, science, sports, finance. The alien needs variety to
develop interesting theories.
"""
from __future__ import annotations

import hashlib
import logging
import os
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

import httpx

log = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reddit.com/r/worldnews/.rss",
    "https://hnrss.org/frontpage",
    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
]

MAX_SEEN = 2000


@dataclass
class Signal:
    """A single intercepted human signal."""

    source: str
    headline: str
    summary: str
    url: str = ""
    intercepted_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.headline.encode()).hexdigest()[:16]


class SignalInterceptor:
    """Fetches and deduplicates signals from configured sources."""

    def __init__(
        self,
        feeds: list[str] | None = None,
        timeout: float = 30.0,
    ):
        raw = os.environ.get("ALIEN_FEEDS", "")
        if feeds:
            self.feeds = feeds
        elif raw:
            self.feeds = [f.strip() for f in raw.split(",") if f.strip()]
        else:
            self.feeds = list(DEFAULT_FEEDS)
        self.timeout = timeout
        self._seen: OrderedDict[str, None] = OrderedDict()

    async def scan(self, max_per_feed: int = 5) -> list[Signal]:
        """Scan all feeds and return new (unseen) signals."""
        signals: list[Signal] = []
        for feed_url in self.feeds:
            try:
                batch = await self._fetch_feed(feed_url, max_per_feed)
                for s in batch:
                    if s.fingerprint not in self._seen:
                        self._mark_seen(s.fingerprint)
                        signals.append(s)
            except Exception as exc:  # noqa: BLE001
                log.warning("feed fetch failed url=%s err=%s", feed_url, exc)
        log.info("scan complete: %d new signals from %d feeds", len(signals), len(self.feeds))
        return signals

    def inject(self, headline: str, summary: str = "", source: str = "manual") -> Signal:
        """Manually inject a signal into the pipeline."""
        signal = Signal(source=source, headline=headline, summary=summary or headline)
        self._mark_seen(signal.fingerprint)
        return signal

    async def _fetch_feed(self, url: str, max_items: int) -> list[Signal]:
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            resp = await http.get(url)
            resp.raise_for_status()
        return self._parse_rss(resp.text, url, max_items)

    @staticmethod
    def _parse_rss(xml_text: str, source_url: str, max_items: int) -> list[Signal]:
        signals: list[Signal] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            log.warning("XML parse failed for %s", source_url)
            return signals

        items = root.findall(".//item")[:max_items]
        for item in items:
            title = item.findtext("title", "").strip()
            desc = item.findtext("description", "").strip()
            link = item.findtext("link", "").strip()
            if title:
                signals.append(Signal(
                    source=source_url,
                    headline=title,
                    summary=desc[:500] if desc else title,
                    url=link,
                ))
        return signals

    def _mark_seen(self, fingerprint: str) -> None:
        self._seen[fingerprint] = None
        if len(self._seen) > MAX_SEEN:
            to_remove = len(self._seen) - (MAX_SEEN // 2)
            for _ in range(to_remove):
                self._seen.popitem(last=False)
