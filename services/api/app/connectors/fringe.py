"""T5 holistic / fringe connectors.

These wrap site search via DuckDuckGo HTML results so we don't depend on
the host site exposing a JSON API. We keep them tier=T5 so the grading
layer downweights them automatically.

Sites covered:
  - Examine.com (rigorous-leaning supplement reviews)
  - Longecity (life-extension forum)
  - ResearchGate (preprint/abstract metadata)
  - Erowid (psychedelic experience reports — for psilocybin/DMT mechanism context)
  - SelfHacked / SelfDecode (functional medicine commentary)
"""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence

DDG_HTML = "https://duckduckgo.com/html/"

SITES = [
    ("examine", "examine.com", "T5"),
    ("longecity", "longecity.org", "T5"),
    ("researchgate", "researchgate.net", "T5"),  # T5 because metadata-only
    ("erowid", "erowid.org", "T5"),
    ("selfhacked", "selfhacked.com", "T5"),
]


class FringeSiteConnector(Connector):
    """Site-restricted DuckDuckGo HTML scrape — tolerates blocks."""

    key = "fringe"
    tier = "T5"
    polite_seconds = 2.5

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 10) -> AsyncIterator[Evidence]:
        from html.parser import HTMLParser

        class ResultParser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.results: list[tuple[str, str, str]] = []
                self._cur_url: str | None = None
                self._cur_title: list[str] = []
                self._mode: str | None = None

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if tag == "a" and "result__a" in (a.get("class") or ""):
                    self._cur_url = a.get("href")
                    self._cur_title = []
                    self._mode = "title"
                elif tag == "a" and "result__snippet" in (a.get("class") or ""):
                    self._mode = "snippet"

            def handle_data(self, data):
                if self._mode == "title":
                    self._cur_title.append(data)

            def handle_endtag(self, tag):
                if tag == "a" and self._mode == "title" and self._cur_url:
                    self.results.append((self._cur_url, "".join(self._cur_title).strip(), ""))
                    self._cur_url = None
                self._mode = None

        async with await self._client() as c:
            for label, site, tier in SITES:
                await self._polite()
                q = f"site:{site} {query}"
                try:
                    r = await c.post(DDG_HTML, data={"q": q}, headers={
                        "User-Agent": "Mozilla/5.0 neuroforge research"})
                    if r.status_code != 200:
                        continue
                except Exception:
                    continue
                p = ResultParser()
                try:
                    p.feed(r.text)
                except Exception:
                    continue
                for url, title, _ in p.results[:limit]:
                    if site not in url:
                        continue
                    yield Evidence(
                        source=f"fringe:{label}", tier=tier,
                        url=url,
                        title=title,
                        abstract="",
                        published=None,
                        authors=[],
                        target_keys=[target_key] if target_key else [],
                        intervention_keys=[intervention_key] if intervention_key else [],
                        study_type="community",
                        raw={"site": site},
                    )
