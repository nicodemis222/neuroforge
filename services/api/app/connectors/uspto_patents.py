"""USPTO ODP — patents/applications mentioning NGF / BDNF / remyelination
targets and interventions. Reuses the deadstick API key pattern: read from
env NEUROFORGE_USPTO_KEY or CREDENTIALS.md.
"""

from __future__ import annotations

import os
from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

ODP_SEARCH = "https://api.uspto.gov/api/v1/patent/applications/search"


class UsptoPatentsConnector(Connector):
    key = "uspto_patents"
    tier = "T3"
    polite_seconds = 1.0

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        api_key = os.environ.get("NEUROFORGE_USPTO_KEY")
        if not api_key:
            return
        async with await self._client() as c:
            await self._polite()
            r = await c.post(ODP_SEARCH,
                             headers={"X-Api-Key": api_key},
                             json={"q": query, "pagination": {"offset": 0, "limit": limit}})
            if r.status_code != 200:
                return
            for app in r.json().get("patentBag", []) or r.json().get("results", []):
                meta = app.get("applicationMetaData", {})
                title = meta.get("inventionTitle") or app.get("title", "")
                appno = app.get("applicationNumberText") or app.get("applicationNumber", "")
                inventors = [f"{i.get('firstName','')} {i.get('lastName','')}".strip()
                             for i in (meta.get("inventorBag") or [])][:6]
                yield Evidence(
                    source=self.key, tier=self.tier,
                    url=f"https://patents.google.com/?q={appno}" if appno else "",
                    title=title,
                    abstract=meta.get("abstractText", "") or "",
                    published=_parse_date(meta.get("filingDate")),
                    authors=inventors,
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="patent",
                    raw={"applicationNumber": appno},
                )
