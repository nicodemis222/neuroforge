"""bioRxiv + medRxiv preprints via their public details API."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

# bioRxiv exposes a server-by-server detail API but no full-text search.
# We use the Europe PMC mirror filter as the primary search path and fall
# back to direct details for hydration.
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class BiorxivConnector(Connector):
    key = "biorxiv"
    tier = "T1"
    polite_seconds = 0.5

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(EPMC, params={
                "query": f"{query} (SRC:PPR)",  # PPR = preprints
                "format": "json", "pageSize": limit, "resultType": "core",
            })
            r.raise_for_status()
            for item in r.json().get("resultList", {}).get("result", []):
                src = (item.get("source") or "").upper()
                if src not in {"PPR"} and "biorxiv" not in (item.get("doi", "") or "").lower() \
                        and "medrxiv" not in (item.get("doi", "") or "").lower():
                    continue
                yield Evidence(
                    source=self.key,
                    tier="T1",  # preprint counts as T1-adjacent (raw research)
                    url=item.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url")
                        or f"https://doi.org/{item.get('doi')}",
                    title=item.get("title", "").strip(),
                    abstract=item.get("abstractText", "") or "",
                    published=_parse_date(item.get("firstPublicationDate")),
                    authors=[a.strip() for a in (item.get("authorString", "") or "").split(",")][:8],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="preprint",
                    raw={"doi": item.get("doi")},
                )
