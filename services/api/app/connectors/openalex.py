"""OpenAlex — broad scholarly index, ported from deadstick."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

OPENALEX = "https://api.openalex.org/works"


class OpenAlexConnector(Connector):
    key = "openalex"
    tier = "T1"
    polite_seconds = 0.3

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(OPENALEX, params={
                "search": query, "per-page": limit, "sort": "relevance_score:desc",
                "mailto": "neuroforge@local",
            })
            r.raise_for_status()
            for w in r.json().get("results", []):
                pubtype = (w.get("type") or "").lower()
                study_type = "review" if pubtype == "review" else (
                    "rct" if "clinical trial" in pubtype else "unknown")
                yield Evidence(
                    source=self.key, tier=self.tier,
                    url=w.get("doi") or w.get("id"),
                    title=(w.get("title") or "").strip(),
                    abstract=_reconstruct_abstract(w.get("abstract_inverted_index") or {}),
                    published=_parse_date(w.get("publication_date")),
                    authors=[a.get("author", {}).get("display_name", "")
                             for a in w.get("authorships", [])][:8],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type=study_type,
                    raw={"id": w.get("id"), "cited_by_count": w.get("cited_by_count", 0)},
                )


def _reconstruct_abstract(inv: dict) -> str:
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    return " ".join(w for _, w in pos)
