# NEUROFORGE

Patient-anchored medical research platform investigating neuronal regrowth /
NGF treatments. Forked architectural pattern from `deadstick`, swapped for
medical sources (T1 peer-review → T5 holistic) and gated by a safety
screen specific to this patient's medication and seizure profile.

## What it does

1. **Loads a patient profile** from any documents you drop into
   `data/patient_corpus/`. Supported formats: **PDF, DOCX, PPTX, XLSX, CSV,
   TSV, TXT, MD, HTML, RTF, JSON**. The repository ships with a synthetic
   example profile so the platform boots without any patient data; the real
   profile is built locally from the documents you ingest.
2. **Cycles through ~35 interventions** across drugs, biologics, supplements,
   devices, behavioral, and holistic — each tagged to mechanistic targets
   (NGF, BDNF, remyelination, axonal sprouting, OPC, RhoA/ROCK, …).
3. **Queries five tiers of sources** for each intervention × target × patient anchor:
   - **T1** PubMed, Europe PMC, bioRxiv/medRxiv, OpenAlex
   - **T2** ClinicalTrials.gov, OpenFDA labels, WHO ICTRP
   - **T3** NIH RePORTER, USPTO patents
   - **T4** Reddit, Hacker News, RSS (Cochrane, Nature Neuroscience, ScienceDaily, Medical Xpress)
   - **T5** Examine, Longecity, ResearchGate, Erowid, SelfHacked (DDG site search)
4. **Grades each piece of evidence** on two axes (GRADE-inspired):
   - `evidence_quality` — tier × study_type × source × recency
   - `mechanistic_plausibility` — patient-target overlap + anatomy keywords
5. **Runs a safety screen** on every intervention against the loaded patient
   profile, derived dynamically:
   - **Seizure axis** — if the profile mentions seizure/epilepsy/spells and no
     antiseizure medication is listed, anything that lowers threshold is
     hard-blocked. Hard-blocks lift automatically once an ASM appears in the
     profile.
   - **Serotonergic axis** — if the profile lists an SSRI/SNRI/serotonin
     modulator (vortioxetine, fluoxetine, etc.), strongly serotonergic
     interventions (psilocybin, DMT, lithium-augmenting protocols) are
     hard-blocked due to serotonin-syndrome risk.
   - **Catecholaminergic axis** — if the profile lists an NRI/stimulant
     (atomoxetine, methylphenidate, etc.), strongly sympathomimetic
     interventions are downgraded with BP/HR-monitoring rationale.
6. **Generates a markdown briefing** per intervention with verdict, top
   evidence, counter-evidence, practical considerations, open questions.

## First run

NEUROFORGE ships a **cross-platform initializer** (`scripts/init.py`) that
verifies prerequisites, installs missing Python and Node packages, bootstraps
the database, and confirms network reachability. The web UI also exposes
this as an **init screen** that runs the first time it can't reach a ready
backend.

### macOS / Linux

```bash
git clone https://github.com/nicodemis222/neuroforge.git && cd neuroforge
./scripts/run_api.sh           # API + scheduler on :8077 (auto-creates .venv)
./scripts/run_web.sh           # UI on :3210 (auto-runs npm install)
```

`run_api.sh` bootstraps a venv at `.venv/` automatically — works on
Homebrew Python (PEP 668) without needing `--break-system-packages`.
For an explicit prerequisite check beforehand, run `python3 scripts/init.py`.

### Windows

```bat
:: From an elevated cmd or PowerShell:
cd neuroforge
scripts\init.bat               :: check + install everything
scripts\run_api.bat            :: API + scheduler on :8077
scripts\run_web.bat            :: UI on :3210
```

If Python or Node.js aren't installed, init will tell you and link to the
download. After installing, re-run init.

### What init does

| Step | Required | Action |
|---|---|---|
| Python ≥ 3.11 | yes | aborts if missing |
| pip | yes | aborts if missing |
| Python deps (fastapi, uvicorn, httpx, pypdf, feedparser) | yes | `pip install -e services/api` |
| Node ≥ 18 | UI only | warn-only if missing |
| npm | UI only | warn-only if missing |
| `web/node_modules` | UI only | `npm install` in `web/` |
| Patient corpus PDFs | recommended | warn if `data/patient_corpus/` empty |
| SQLite DB at `data/neuroforge.db` | yes | bootstrap schema |
| Ollama on :11434 | optional | warn-only (only needed for PDF extraction) |
| PubMed reachable | recommended | warn-only |

### Run a single intervention synchronously (seed the DB fast)

```bash
# macOS / Linux
./scripts/once.sh clemastine
# Windows
scripts\once.bat clemastine
```

### Re-extract patient profile from PDFs (needs Ollama)

```bash
./scripts/seed.sh        # macOS / Linux
scripts\seed.bat         # Windows
```

Open http://localhost:3210 — the dashboard is a 2D scatter (evidence
quality × mechanistic plausibility) with safety-coded dots; click any
intervention to see its full briefing.

## Add documents to the corpus

Three options:

1. **Drop files manually** into `data/patient_corpus/` and run
   `./scripts/seed.sh` (or `scripts\seed.bat` on Windows) to extract.
2. **Upload via the UI** — the dashboard has a "Corpus" panel that posts
   to `POST /api/corpus/upload` (multipart). The endpoint enforces the
   supported-extension allowlist server-side.
3. **POST programmatically**:

   ```bash
   curl -F 'files=@my-report.docx' -F 'files=@labs.xlsx' \
        http://localhost:8077/api/corpus/upload
   curl -X POST http://localhost:8077/api/corpus/extract
   ```

The extractor is idempotent (content-hash gated) and merges findings,
symptoms, medications, and diagnoses across all documents into
`data/patient_corpus/profile.json`. `app.seed.patient_profile.load()`
prefers that file over the synthetic `DEFAULT`.

### Privacy

`data/patient_corpus/` is gitignored. Documents never leave your machine.
The connectors only send high-level mechanism + intervention queries to
public APIs — no document text or patient identifiers are transmitted.

To install the optional ingest dependencies (needed for non-PDF formats):

```bash
pip install -e 'services/api[ingest]'
```

## Add a new intervention or target

Edit `services/api/app/ontology/interventions.py` or `targets.py`. The
scheduler picks them up next cycle; safety + grading apply automatically
based on the declared `seizure_risk`, `interactions`, and `targets`
fields.

## Architecture notes

- **Local-first**: SQLite at `data/neuroforge.db` for the MVP. Schema is
  Postgres-compatible if you want to migrate later.
- **No keys required** for the default connector set. USPTO ODP picks up
  `NEUROFORGE_USPTO_KEY` from env if you have one.
- **Polite pacing** on every connector via per-host async lock. No source
  is hit faster than ~1 req/s.
- **Safety is a hard gate**, not a soft signal: anything that lowers
  seizure threshold while the patient is off ASM is `HARD_BLOCK`,
  serotonin-syndrome co-administrations are `HARD_BLOCK`, and the
  briefing surfaces these in section 1 before any evidence summary.

## Architecture honesty (v3)

Despite the "agent / cockpit" framing, **v3 is a deterministic pipeline**
with one LLM call (document extraction). What's actually doing what:

| Layer | Implementation | Uses LLM? |
|---|---|---|
| Document → profile extraction | `app/seed/extractor.py` calls Ollama | yes (default `llama3.2:latest`) |
| 13 source connectors | templated HTTP clients | no |
| Scheduler (3 loops) | asyncio + per-loop locks + jitter | no |
| Evidence grading | rule-based formula (tier × study_type × source × recency × anatomy hits) | no |
| Safety screen | drug-class taxonomies + per-intervention metadata | no |
| Briefing generator | f-string template over DB queries | no |
| Synopsis | SQL aggregation | no |

This works because the ontology + safety rules + grading formula encode
enough domain knowledge to produce useful output deterministically. It's
also fast, predictable, and cheap to run.

**Where actual agents would help (see [docs/V4_AGENTS_AND_RAG.md](docs/V4_AGENTS_AND_RAG.md)):**

1. **Synthesis agent** — RAG over retrieved abstracts → grounded prose
   in the briefing's "what the literature actually says" section
2. **Critic agent** — adversarial pass for disconfirming evidence and
   patient-mismatch flags
3. **Coverage agent** — picks next-best-query based on ontology gaps
   instead of round-robin
4. **Triage agent** — synchronous top-up when an opened briefing has
   thin evidence

These are designed but not built. v4 trigger: when the templated briefing
becomes the bottleneck.

## What this is NOT

This is a research-platform output. Nothing here is a recommendation,
prescription, or clinical advice. Discuss any consideration surfaced
here with the treating neurologist, epilepsy team, and psychiatrist
before any change.
