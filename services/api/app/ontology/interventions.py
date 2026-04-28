"""
Interventions to track: pharmaceutical, supplement, behavioral, device,
holistic. Each has evidence-tier hints and known seizure / drug-interaction
flags relevant to this patient (atomoxetine + vortioxetine, suspected focal
aware seizures, no current ASM).

Tier hints describe where evidence is *expected* to live, not what we accept.
The grading layer makes the final call from retrieved evidence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Intervention:
    key: str
    name: str
    synonyms: tuple[str, ...]
    category: str            # drug | supplement | device | behavioral | holistic | biologic
    targets: tuple[str, ...]  # target keys it mechanistically engages
    expected_tier: str        # T1..T5
    seizure_risk: str         # 'lowers' | 'neutral' | 'raises' | 'mixed' | 'unknown'
    interactions: tuple[str, ...]  # known interaction concerns vs patient meds
    notes: str = ""


INTERVENTIONS: tuple[Intervention, ...] = (
    # --- Strong-evidence pharma / repurposed ---
    Intervention("clemastine", "Clemastine fumarate", ("clemastine",),
                 "drug", ("remyelination", "opcs"), "T1",
                 "neutral", (),
                 "ReBUILD trial — remyelination in MS. Strongest repurposed remyelination evidence."),
    Intervention("metformin", "Metformin", ("metformin",),
                 "drug", ("opcs", "remyelination"), "T1",
                 "neutral", (),
                 "Promotes OPC responsiveness in aged CNS."),
    Intervention("fasudil", "Fasudil", ("fasudil", "HA-1077"),
                 "drug", ("rho_rock", "axonal_sprouting"), "T1",
                 "neutral", (),
                 "ROCK inhibitor; axon regrowth in models."),
    Intervention("lithium_micro", "Low-dose lithium", ("lithium orotate", "microdose lithium"),
                 "drug", ("bdnf", "neurogenesis"), "T2",
                 "lowers", ("vortioxetine: serotonergic synergy — monitor",),
                 "Microdose may raise BDNF; full-dose has its own profile."),
    Intervention("cerebrolysin", "Cerebrolysin", ("Cerebrolysin", "FPF1070"),
                 "biologic", ("ngf", "bdnf"), "T1",
                 "neutral", (),
                 "Porcine brain peptide preparation; stroke + TBI trials."),
    Intervention("citicoline", "Citicoline", ("CDP-choline", "citicoline"),
                 "supplement", ("synaptic_plasticity",), "T1",
                 "neutral", (),
                 "Mixed stroke trials; benign profile."),

    # --- TrkB agonists / neurotrophin mimetics ---
    Intervention("dhf78", "7,8-Dihydroxyflavone", ("7,8-DHF", "78-DHF", "tropoflavin"),
                 "supplement", ("trkb", "bdnf"), "T2",
                 "lowers", (),
                 "Small-molecule TrkB agonist."),
    Intervention("lm22a4", "LM22A-4", ("LM22A-4",),
                 "drug", ("trkb",), "T3",
                 "unknown", (),
                 "Preclinical TrkB partial agonist."),
    Intervention("intranasal_ngf", "Intranasal NGF", ("intranasal NGF", "iNGF"),
                 "biologic", ("ngf",), "T2",
                 "unknown", (),
                 "Case series in pediatric TBI / stroke."),

    # --- Peptides / nootropics ---
    Intervention("semax", "Semax", ("semax", "ACTH(4-7) Pro-Gly-Pro"),
                 "supplement", ("bdnf", "ngf"), "T3",
                 "unknown", ("atomoxetine: dual catecholaminergic load — caution",),
                 "Russian heptapeptide; limited Western trials."),
    Intervention("selank", "Selank", ("selank",),
                 "supplement", ("bdnf",), "T3",
                 "unknown", (), ""),
    Intervention("cerebrolysin_alt", "P21 peptide", ("P021", "P21 peptide"),
                 "biologic", ("ngf", "bdnf"), "T3",
                 "unknown", (), ""),

    # --- Natural products ---
    Intervention("lions_mane", "Lion's Mane (Hericium erinaceus)",
                 ("Hericium erinaceus", "lions mane", "yamabushitake",
                  "hericenones", "erinacines"),
                 "supplement", ("ngf",), "T2",
                 "neutral", (),
                 "Hericenones cross BBB, induce NGF in vitro and in some human trials."),
    Intervention("curcumin", "Curcumin", ("curcumin", "turmeric"),
                 "supplement", ("bdnf", "microglia"), "T2",
                 "neutral", (),
                 "Anti-inflammatory; bioavailability is the limiter."),
    Intervention("epa_dha", "Omega-3 (EPA/DHA)", ("DHA", "EPA", "omega-3", "n-3 PUFA"),
                 "supplement", ("bdnf", "remyelination"), "T1",
                 "lowers", (),
                 "Modest seizure-protective signal."),
    Intervention("apigenin", "Apigenin", ("apigenin",),
                 "supplement", ("bdnf",), "T3", "neutral", (), ""),
    Intervention("magnolol", "Magnolol / Honokiol", ("magnolia bark",),
                 "supplement", ("trkb",), "T3", "neutral", (), ""),

    # --- Behavioral / lifestyle ---
    Intervention("hiit", "High-intensity interval training",
                 ("HIIT", "aerobic exercise", "exercise"),
                 "behavioral", ("bdnf", "neurogenesis"), "T1",
                 "lowers", (),
                 "Strongest non-pharma BDNF inducer."),
    Intervention("ketogenic", "Ketogenic diet",
                 ("keto diet", "ketogenic", "BHB", "beta-hydroxybutyrate"),
                 "behavioral", ("bdnf",), "T1",
                 "lowers", (),
                 "Established anti-seizure; raises BDNF."),
    Intervention("fasting", "Intermittent fasting",
                 ("intermittent fasting", "time-restricted eating", "TRE"),
                 "behavioral", ("bdnf", "neurogenesis"), "T2",
                 "lowers", (), ""),
    Intervention("sleep", "Sleep optimization",
                 ("sleep architecture", "slow-wave sleep", "deep sleep"),
                 "behavioral", ("synaptic_plasticity",), "T1",
                 "lowers", (),
                 "Sleep deprivation lowers seizure threshold — high priority."),
    Intervention("meditation", "Meditation / contemplative practice",
                 ("mindfulness", "meditation", "vipassana"),
                 "behavioral", ("bdnf", "synaptic_plasticity"), "T2",
                 "lowers", (), ""),

    # --- Devices ---
    Intervention("pbm", "Photobiomodulation",
                 ("PBM", "transcranial LED", "tPBM", "low-level laser therapy", "LLLT"),
                 "device", ("bdnf", "microglia"), "T2",
                 "neutral", (),
                 "tPBM: 810/1064nm; emerging stroke + TBI evidence."),
    Intervention("hbot", "Hyperbaric oxygen therapy",
                 ("HBOT", "hyperbaric oxygen"),
                 "device", ("neurogenesis", "axonal_sprouting"), "T2",
                 "mixed", (),
                 "1.5-2.0 ATA protocols; controversial in chronic TBI."),
    Intervention("vns", "Vagus nerve stimulation",
                 ("VNS", "tVNS", "transcutaneous vagus"),
                 "device", ("bdnf", "axonal_sprouting"), "T1",
                 "lowers", (),
                 "FDA-approved for refractory epilepsy AND stroke rehab — dual win."),
    Intervention("tdcs", "Transcranial direct-current stimulation",
                 ("tDCS",), "device", ("synaptic_plasticity",), "T2",
                 "neutral", (), ""),
    Intervention("tms", "Transcranial magnetic stimulation",
                 ("rTMS", "TMS"), "device", ("bdnf", "synaptic_plasticity"), "T1",
                 "raises", (),
                 "Caution: rTMS can lower seizure threshold."),

    # --- Cell / regenerative ---
    Intervention("msc", "Mesenchymal stem cell therapy",
                 ("MSC", "mesenchymal stem cells", "BM-MSC"),
                 "biologic", ("npcs", "remyelination"), "T2",
                 "unknown", (), ""),
    Intervention("exosomes", "Exosome therapy",
                 ("MSC-exosomes", "extracellular vesicles"),
                 "biologic", ("axonal_sprouting",), "T3",
                 "unknown", (), ""),

    # --- Psychedelic / fringe but mechanistically interesting ---
    Intervention("psilocybin", "Psilocybin", ("psilocybin", "psilocin"),
                 "drug", ("synaptic_plasticity", "bdnf"), "T2",
                 "mixed", ("vortioxetine: serotonin syndrome risk — contraindicated",
                           "atomoxetine: pressor risk — caution"),
                 "Spine density increase shown; SSRI/SNRI interaction is hard contraindication."),
    Intervention("ketamine", "Ketamine / esketamine",
                 ("ketamine", "esketamine", "Spravato"),
                 "drug", ("bdnf", "synaptic_plasticity"), "T1",
                 "lowers", (),
                 "Rapid BDNF surge; FDA-approved (esketamine) for TRD."),
    Intervention("dmt", "DMT / ayahuasca",
                 ("DMT", "ayahuasca"), "drug",
                 ("bdnf", "synaptic_plasticity"), "T3",
                 "mixed", ("vortioxetine: serotonin syndrome — contraindicated",), ""),

    # --- Holistic / TCM / Ayurveda ---
    Intervention("ashwagandha", "Ashwagandha (Withania somnifera)",
                 ("ashwagandha", "Withania somnifera", "withanolides"),
                 "holistic", ("bdnf", "neurogenesis"), "T3",
                 "lowers", (), ""),
    Intervention("bacopa", "Bacopa monnieri", ("bacopa", "brahmi"),
                 "holistic", ("bdnf",), "T2",
                 "lowers", (), ""),
    Intervention("gotu_kola", "Gotu Kola (Centella asiatica)",
                 ("Centella asiatica", "gotu kola"),
                 "holistic", ("bdnf", "axonal_sprouting"), "T3",
                 "neutral", (),
                 "Asiaticoside — preclinical axon regrowth signal."),
    Intervention("ginkgo", "Ginkgo biloba", ("ginkgo", "EGb 761"),
                 "holistic", ("bdnf",), "T2",
                 "neutral", (), ""),
    Intervention("rhodiola", "Rhodiola rosea", ("rhodiola", "salidroside"),
                 "holistic", ("bdnf",), "T3",
                 "lowers", (), ""),
    Intervention("huperzine", "Huperzine A", ("huperzine A", "Huperzia"),
                 "holistic", ("synaptic_plasticity",), "T3",
                 "lowers", (), "AChE inhibitor; some seizure-protective signal."),

    # --- Wellness inputs ---
    Intervention("creatine", "Creatine monohydrate", ("creatine",),
                 "supplement", ("synaptic_plasticity",), "T1",
                 "neutral", (), ""),
    Intervention("magnesium_threonate", "Magnesium L-threonate",
                 ("magnesium threonate", "Magtein"),
                 "supplement", ("synaptic_plasticity",), "T2",
                 "lowers", (), ""),
    Intervention("nac", "N-Acetylcysteine", ("NAC", "N-acetylcysteine"),
                 "supplement", ("microglia",), "T2",
                 "neutral", (), ""),
    Intervention("alcar", "Acetyl-L-carnitine", ("ALCAR", "acetyl-L-carnitine"),
                 "supplement", ("ngf",), "T2",
                 "neutral", (), ""),
)


INTERVENTIONS_BY_KEY = {i.key: i for i in INTERVENTIONS}


def query_terms(intervention: Intervention) -> list[str]:
    return [intervention.name, *intervention.synonyms]
