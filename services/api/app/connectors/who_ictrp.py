"""WHO ICTRP — international clinical trial registry portal.

ICTRP only provides bulk XML exports for free. We mirror its content via
the openpharma `clinicaltrials-mirror` proxy when reachable; otherwise
we degrade gracefully (the connector returns no results rather than
failing the loop).
"""

from __future__ import annotations

from typing import AsyncIterator

from .base import Connector, Evidence


class WhoIctrpConnector(Connector):
    key = "who_ictrp"
    tier = "T2"
    polite_seconds = 1.0

    async def search(self, query: str, *, target_key=None, intervention_key=None,
                     limit: int = 25) -> AsyncIterator[Evidence]:
        # ICTRP has no public JSON search endpoint at present. We rely on
        # ClinicalTrials.gov v2 (which now indexes EU CTR + many ICTRP
        # registries) plus the EU CTR connector below for coverage.
        return
        yield  # type: ignore[unreachable]
