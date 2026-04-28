"""All connectors. The registry maps tier -> instances."""

from .base import Connector, Evidence
from .pubmed import PubMedConnector
from .europe_pmc import EuropePmcConnector
from .biorxiv import BiorxivConnector
from .openalex import OpenAlexConnector
from .clinicaltrials import ClinicalTrialsConnector
from .openfda import OpenFDAConnector
from .who_ictrp import WhoIctrpConnector
from .nih_reporter import NihReporterConnector
from .uspto_patents import UsptoPatentsConnector
from .reddit import RedditConnector
from .hackernews import HackerNewsConnector
from .rss import RssConnector, DEFAULT_FEEDS
from .fringe import FringeSiteConnector


def all_connectors() -> list[Connector]:
    return [
        # T1
        PubMedConnector(),
        EuropePmcConnector(),
        BiorxivConnector(),
        OpenAlexConnector(),
        # T2
        ClinicalTrialsConnector(),
        OpenFDAConnector(),
        WhoIctrpConnector(),
        # T3
        NihReporterConnector(),
        UsptoPatentsConnector(),
        # T4
        RedditConnector(),
        HackerNewsConnector(),
        RssConnector(DEFAULT_FEEDS),
        # T5
        FringeSiteConnector(),
    ]


def by_tier() -> dict[str, list[Connector]]:
    out: dict[str, list[Connector]] = {"T1": [], "T2": [], "T3": [], "T4": [], "T5": []}
    for c in all_connectors():
        out.setdefault(c.tier, []).append(c)
    return out


__all__ = ["Connector", "Evidence", "all_connectors", "by_tier"]
