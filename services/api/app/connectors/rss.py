"""Generic RSS connector — feeds list defined in app.connectors.rss_feeds.

Used by Substack, Cochrane summaries, neuro blogs, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import AsyncIterator

from .base import Connector, Evidence


class RssConnector(Connector):
    key = "rss"
    tier = "T4"
    polite_seconds = 0.2

    def __init__(self, feeds: list[tuple[str, str, str]]) -> None:
        """feeds: list of (label, url, tier)."""
        super().__init__()
        self.feeds = feeds

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        try:
            import feedparser  # type: ignore
        except ImportError:
            return
        q = query.lower()
        async with await self._client() as c:
            for label, url, tier in self.feeds:
                await self._polite()
                try:
                    r = await c.get(url, headers={"Accept": "application/rss+xml,*/*"})
                    if r.status_code != 200:
                        continue
                    feed = feedparser.parse(r.text)
                except Exception:
                    continue
                for entry in feed.entries[:limit]:
                    haystack = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if q and q not in haystack:
                        continue
                    pub = entry.get("published") or entry.get("updated") or ""
                    try:
                        when = parsedate_to_datetime(pub) if pub else None
                    except Exception:
                        when = None
                    yield Evidence(
                        source=f"rss:{label}", tier=tier,
                        url=entry.get("link", ""),
                        title=entry.get("title", ""),
                        abstract=entry.get("summary", "")[:2000],
                        published=when,
                        authors=[entry.get("author", "")] if entry.get("author") else [],
                        target_keys=[target_key] if target_key else [],
                        intervention_keys=[intervention_key] if intervention_key else [],
                        study_type="review" if tier == "T1" else "community",
                        raw={},
                    )


# Curated default feed catalog covering tiers T1, T4, T5.
DEFAULT_FEEDS: list[tuple[str, str, str]] = [
    # T1-ish editorial / review
    ("cochrane_neuro", "https://www.cochranelibrary.com/cdsr/reviews/topics/neurology/feed", "T1"),
    ("nature_neurosci", "https://www.nature.com/neuro.rss", "T1"),
    # T4 community / news
    ("sciencedaily_neuro", "https://www.sciencedaily.com/rss/mind_brain.xml", "T4"),
    ("medical_xpress_neuro", "https://medicalxpress.com/rss-feed/neuroscience-news/", "T4"),
    # T5 holistic / fringe
    ("life_extension", "https://www.lifeextension.com/wellness/feed", "T5"),
    ("greenmedinfo", "https://www.greenmedinfo.com/rss.xml", "T5"),
]
