"""ClinicalTrials.gov v2 API."""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence, _parse_date

CT_API = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsConnector(Connector):
    key = "clinicaltrials"
    tier = "T2"
    polite_seconds = 0.4

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get(CT_API, params={
                "query.term": query, "pageSize": limit,
                "format": "json",
            })
            r.raise_for_status()
            for s in r.json().get("studies", []):
                proto = s.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status = proto.get("statusModule", {})
                design = proto.get("designModule", {})
                phase = ",".join(design.get("phases", []) or [])
                study_type = "rct" if "RANDOMIZED" in (design.get("designInfo", {}).get("allocation", "") or "").upper() else "cohort"
                nct = ident.get("nctId", "")
                yield Evidence(
                    source=self.key,
                    tier=self.tier,
                    url=f"https://clinicaltrials.gov/study/{nct}",
                    title=ident.get("briefTitle", ""),
                    abstract=proto.get("descriptionModule", {}).get("briefSummary", "") or "",
                    published=_parse_date(status.get("studyFirstPostDateStruct", {}).get("date")),
                    authors=[],
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type=study_type,
                    sample_size=design.get("enrollmentInfo", {}).get("count"),
                    raw={"nct": nct, "phase": phase,
                         "status": status.get("overallStatus", "")},
                )
