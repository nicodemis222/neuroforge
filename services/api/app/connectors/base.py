"""
Connector base. Adapted from deadstick. Each connector emits Evidence
records with a uniform schema so the grading + briefing layers don't
care where data came from.

All connectors are async, polite (per-host pacing), and key-optional.
"""

from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, ClassVar

import httpx


@dataclass
class Evidence:
    source: str                 # connector key, e.g. "pubmed"
    tier: str                   # T1..T5
    url: str
    title: str
    abstract: str
    published: datetime | None
    authors: list[str] = field(default_factory=list)
    target_keys: list[str] = field(default_factory=list)
    intervention_keys: list[str] = field(default_factory=list)
    study_type: str = "unknown"  # rct | systematic_review | cohort | case | review | preclinical | preprint | community | unknown
    sample_size: int | None = None
    raw: dict = field(default_factory=dict)

    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.source}|{self.url}".encode()).hexdigest()[:16]


class Connector(ABC):
    key: ClassVar[str] = ""
    tier: ClassVar[str] = "T3"
    polite_seconds: ClassVar[float] = 1.0  # min seconds between requests
    user_agent: ClassVar[str] = "neuroforge/0.1 (+https://localhost local research)"

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def _polite(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self.polite_seconds - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = asyncio.get_event_loop().time()

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    @abstractmethod
    async def search(self, query: str, *, target_key: str | None = None,
                     intervention_key: str | None = None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        ...
        if False:  # pragma: no cover — typing
            yield  # type: ignore[unreachable]


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d", "%Y %b %d", "%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
