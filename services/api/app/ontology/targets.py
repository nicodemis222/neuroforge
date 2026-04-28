"""
Biological targets for neuronal regrowth / NGF research.

Each target has:
  - canonical name + synonyms (for query expansion across sources)
  - mechanism class
  - relevance score for THIS patient's findings (chronic CST lesion +
    crossed cerebellar diaschisis + periventricular nonenhancing lesions
    + suspected focal aware seizures)

Relevance is a 0-1 prior. The scheduler uses it to weight retrieval.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Target:
    key: str
    canonical: str
    synonyms: tuple[str, ...]
    mechanism: str
    patient_relevance: float
    notes: str = ""


TARGETS: tuple[Target, ...] = (
    # --- Neurotrophins ---
    Target("ngf", "Nerve Growth Factor", ("NGF", "beta-NGF", "NGFB"),
           "neurotrophin", 1.0,
           "Primary axis. Intranasal NGF trialed in TBI/stroke."),
    Target("bdnf", "Brain-Derived Neurotrophic Factor", ("BDNF", "TrkB ligand"),
           "neurotrophin", 1.0,
           "Strongest evidence for adult neurogenesis + plasticity. TrkB agonists."),
    Target("gdnf", "Glial-Derived Neurotrophic Factor", ("GDNF",),
           "neurotrophin", 0.7,
           "Dopaminergic + motor neurons; some CST relevance."),
    Target("cntf", "Ciliary Neurotrophic Factor", ("CNTF",),
           "neurotrophin", 0.6, ""),
    Target("nt3", "Neurotrophin-3", ("NT-3", "NTF3"),
           "neurotrophin", 0.7,
           "Relevant to corticospinal tract sprouting in animal models."),
    Target("fgf2", "Fibroblast Growth Factor 2", ("FGF-2", "bFGF"),
           "growth factor", 0.6, ""),
    Target("igf1", "Insulin-like Growth Factor 1", ("IGF-1", "somatomedin C"),
           "growth factor", 0.6, ""),

    # --- Receptors ---
    Target("trkb", "TrkB receptor", ("NTRK2", "TrkB agonist"),
           "receptor", 0.9, "Small-molecule agonists: 7,8-DHF, LM22A-4."),
    Target("trka", "TrkA receptor", ("NTRK1",),
           "receptor", 0.7, ""),
    Target("p75ntr", "p75 neurotrophin receptor", ("NGFR", "p75NTR"),
           "receptor", 0.5, ""),

    # --- Process targets ---
    Target("neurogenesis", "Adult neurogenesis",
           ("dentate gyrus neurogenesis", "subventricular zone", "SVZ",
            "subgranular zone", "SGZ"),
           "process", 0.95, ""),
    Target("remyelination", "Remyelination",
           ("myelin repair", "OPC differentiation", "oligodendrocyte progenitor"),
           "process", 1.0,
           "Periventricular lesions raise demyelination as DDx — directly relevant."),
    Target("axonal_sprouting", "Axonal sprouting",
           ("axon regeneration", "collateral sprouting", "CST sprouting"),
           "process", 1.0, "Most direct mechanism for CST lesion recovery."),
    Target("synaptic_plasticity", "Synaptic plasticity",
           ("LTP", "long-term potentiation", "spine density"),
           "process", 0.8, ""),
    Target("crossed_diaschisis", "Crossed cerebellar diaschisis recovery",
           ("CCD recovery", "cerebellar reorganization"),
           "process", 0.9, "Patient-specific finding."),

    # --- Cellular ---
    Target("opcs", "Oligodendrocyte progenitor cells",
           ("OPC", "NG2 cells"),
           "cell", 0.95, ""),
    Target("npcs", "Neural progenitor cells",
           ("NPC", "neural stem cells", "NSC"),
           "cell", 0.85, ""),
    Target("microglia", "Microglial polarization",
           ("M1/M2 microglia", "neuroinflammation"),
           "cell", 0.7, ""),

    # --- Pathways ---
    Target("mtor", "mTOR pathway", ("mTORC1", "mTORC2", "rapamycin target"),
           "pathway", 0.6, "Caution: seizure interactions."),
    Target("wnt", "Wnt signaling", ("Wnt/beta-catenin",),
           "pathway", 0.6, ""),
    Target("creb", "CREB pathway", ("cAMP response element-binding",),
           "pathway", 0.7, ""),
    Target("rho_rock", "RhoA/ROCK pathway", ("ROCK inhibition", "fasudil target"),
           "pathway", 0.85, "Inhibition promotes axon regrowth."),
)


TARGETS_BY_KEY = {t.key: t for t in TARGETS}


def query_terms(target: Target) -> list[str]:
    """All search terms for this target — canonical + synonyms."""
    return [target.canonical, *target.synonyms]
