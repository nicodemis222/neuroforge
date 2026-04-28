"""HN search via Algolia."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from .base import Connector, Evidence

HN = "https://hn.algolia.com/api/v1/search"


class HackerNewsConnector(Connector):
    key = "hackernews"
    tier = "T4"
    polite_seconds = 0.5

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(HN, params={"query": query, "tags": "story",
                                        "hitsPerPage": limit})
            r.raise_for_status()
            for h in r.json().get("hits", []):
                yield Evidence(
                    source=self.key, tier=self.tier,
                    url=h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    title=h.get("title", ""),
                    abstract=h.get("story_text", "") or "",
                    published=datetime.fromtimestamp(h.get("created_at_i", 0), tz=timezone.utc),
                    authors=[h.get("author", "")],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="community",
                    raw={"points": h.get("points", 0), "comments": h.get("num_comments", 0)},
                )
