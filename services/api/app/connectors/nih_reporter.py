"""NIH RePORTER — funded grants, often a leading indicator for trials."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

REPORTER = "https://api.reporter.nih.gov/v2/projects/search"


class NihReporterConnector(Connector):
    key = "nih_reporter"
    tier = "T3"
    polite_seconds = 0.5

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.post(REPORTER, json={
                "criteria": {"advanced_text_search": {
                    "operator": "and", "search_field": "all",
                    "search_text": query,
                }},
                "limit": limit, "offset": 0,
                "sort_field": "fiscal_year", "sort_order": "desc",
            })
            if r.status_code != 200:
                return
            for p in r.json().get("results", []):
                yield Evidence(
                    source=self.key, tier=self.tier,
                    url=f"https://reporter.nih.gov/project-details/{p.get('appl_id')}",
                    title=p.get("project_title", ""),
                    abstract=p.get("abstract_text", "") or "",
                    published=_parse_date(p.get("project_start_date")),
                    authors=[c.get("full_name", "") for c in p.get("contact_pi_name", []) or []
                             if isinstance(c, dict)] or
                            ([p["contact_pi_name"]] if isinstance(p.get("contact_pi_name"), str) else []),
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="preclinical" if "R01" in (p.get("activity_code", "") or "") else "unknown",
                    raw={"appl_id": p.get("appl_id"),
                         "fiscal_year": p.get("fiscal_year"),
                         "agency": p.get("agency_ic_admin", {}).get("name"),
                         "amount": p.get("award_amount")},
                )
