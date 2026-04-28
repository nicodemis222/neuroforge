"""OpenFDA drug labels + adverse events. Keyless tier (240/min, 1000/day)."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

LABEL = "https://api.fda.gov/drug/label.json"
EVENT = "https://api.fda.gov/drug/event.json"


class OpenFDAConnector(Connector):
    key = "openfda"
    tier = "T2"
    polite_seconds = 0.3

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 10) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(LABEL, params={
                "search": f'openfda.generic_name:"{query}" OR openfda.brand_name:"{query}"',
                "limit": limit,
            })
            if r.status_code == 404:
                return
            r.raise_for_status()
            for item in r.json().get("results", []):
                openfda = item.get("openfda", {})
                brand = (openfda.get("brand_name") or [""])[0]
                generic = (openfda.get("generic_name") or [query])[0]
                yield Evidence(
                    source=self.key, tier=self.tier,
                    url=f"https://labels.fda.gov/getapplication.cfm?id={item.get('id', '')}",
                    title=f"FDA Label: {brand} ({generic})",
                    abstract=" ".join(item.get("indications_and_usage", [""]))[:2000],
                    published=_parse_date(item.get("effective_time")),
                    authors=[],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="review",
                    raw={"warnings": item.get("warnings", [""])[0][:1000],
                         "contraindications": item.get("contraindications", [""])[0][:1000],
                         "drug_interactions": item.get("drug_interactions", [""])[0][:1000]},
                )
