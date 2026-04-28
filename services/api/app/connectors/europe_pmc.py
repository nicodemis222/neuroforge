"""Europe PMC — full-text + abstracts, keyless."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class EuropePmcConnector(Connector):
    key = "europe_pmc"
    tier = "T1"
    polite_seconds = 0.5

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(EUROPE_PMC, params={
                "query": query, "format": "json", "pageSize": limit,
                "resultType": "core", "sort": "RELEVANCE",
            })
            r.raise_for_status()
            for item in r.json().get("resultList", {}).get("result", []):
                pubtype = (item.get("pubTypeList", {}).get("pubType") or [""])[0].lower()
                yield Evidence(
                    source=self.key,
                    tier=self.tier,
                    url=item.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url")
                        or f"https://europepmc.org/article/{item.get('source')}/{item.get('id')}",
                    title=item.get("title", "").strip(),
                    abstract=item.get("abstractText", "") or "",
                    published=_parse_date(item.get("firstPublicationDate")),
                    authors=[a.strip() for a in (item.get("authorString", "") or "").split(",")][:8],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type=_classify(pubtype),
                    raw={"id": item.get("id"), "source": item.get("source"),
                         "citedByCount": item.get("citedByCount", 0)},
                )


def _classify(pubtype: str) -> str:
    if "systematic review" in pubtype or "meta-analysis" in pubtype:
        return "systematic_review"
    if "randomized" in pubtype:
        return "rct"
    if "review" in pubtype:
        return "review"
    if "case" in pubtype:
        return "case"
    return "unknown"
