"""Reddit search via .json endpoint — keyless, rate-limited."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from .base import Connector, Evidence

SUBREDDITS = (
    "MultipleSclerosis", "Stroke", "BrainInjury", "Nootropics",
    "TBI", "epilepsy", "Neuropsychology", "Biohackers",
)


class RedditConnector(Connector):
    key = "reddit"
    tier = "T4"
    polite_seconds = 2.0  # Reddit is strict
    user_agent = "neuroforge/0.1 personal research (no commercial)"

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            for sub in SUBREDDITS:
                await self._polite()
                r = await c.get(
                    f"https://www.reddit.com/r/{sub}/search.json",
                    params={"q": query, "restrict_sr": "1", "limit": min(limit, 25),
                            "sort": "relevance", "t": "year"},
                )
                if r.status_code != 200:
                    continue
                for ch in r.json().get("data", {}).get("children", []):
                    d = ch.get("data", {})
                    yield Evidence(
                        source=f"reddit:{sub}", tier=self.tier,
                        url=f"https://reddit.com{d.get('permalink','')}",
                        title=d.get("title", ""),
                        abstract=(d.get("selftext", "") or "")[:2000],
                        published=datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc),
                        authors=[d.get("author", "")],
                        target_keys=[target_key] if target_key else [],
                        intervention_keys=[intervention_key] if intervention_key else [],
                        study_type="community",
                        raw={"score": d.get("score", 0), "num_comments": d.get("num_comments", 0)},
                    )
