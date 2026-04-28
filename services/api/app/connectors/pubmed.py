"""
PubMed via NCBI E-utilities. Keyless; rate-limited to 3 req/s without an
API key, 10 req/s with one. We default to keyless and 0.4s pacing.
"""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedConnector(Connector):
    key = "pubmed"
    tier = "T1"
    polite_seconds = 0.4

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(ESEARCH, params={
                "db": "pubmed", "term": query, "retmax": limit,
                "retmode": "json", "sort": "relevance",
            })
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return
            await self._polite()
            s = await c.get(ESUMMARY, params={
                "db": "pubmed", "id": ",".join(ids), "retmode": "json",
            })
            s.raise_for_status()
            results = s.json().get("result", {})
            for pmid in ids:
                rec = results.get(pmid, {})
                if not rec:
                    continue
                title = rec.get("title", "").strip()
                pubdate = rec.get("pubdate") or rec.get("epubdate")
                authors = [a.get("name", "") for a in rec.get("authors", [])][:8]
                pubtypes = [pt.lower() for pt in rec.get("pubtype", [])]
                study_type = _classify(pubtypes)
                yield Evidence(
                    source=self.key,
                    tier=self.tier,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    title=title,
                    abstract="",  # efetch needed for full abstract; skipped to keep latency low
                    published=_parse_date(pubdate),
                    authors=authors,
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type=study_type,
                    raw={"pmid": pmid, "pubtype": pubtypes},
                )


def _classify(pubtypes: list[str]) -> str:
    text = " ".join(pubtypes)
    if "meta-analysis" in text or "systematic review" in text:
        return "systematic_review"
    if "randomized controlled trial" in text or "clinical trial, phase" in text:
        return "rct"
    if "clinical trial" in text:
        return "cohort"
    if "case reports" in text:
        return "case"
    if "review" in text:
        return "review"
    return "unknown"
