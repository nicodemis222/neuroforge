# NEUROFORGE — User Manual

A practical guide to running the platform, ingesting documents, reading the
dashboard, and extending the ontology. Written for a user comfortable with
a terminal but not assumed to be a developer.

> **Not medical advice.** Everything this platform produces is research output.
> Discuss anything surfaced here with your treating clinicians before any
> change in care.

---

## Table of contents

1. [What this platform is](#1-what-this-platform-is)
2. [First run — installation](#2-first-run--installation)
3. [The init screen](#3-the-init-screen)
4. [Adding documents to the corpus](#4-adding-documents-to-the-corpus)
5. [Reading the dashboard](#5-reading-the-dashboard)
6. [Reading a briefing](#6-reading-a-briefing)
7. [The safety screen](#7-the-safety-screen)
8. [Running searches — scheduler vs. once-mode](#8-running-searches--scheduler-vs-once-mode)
9. [Editing the ontology](#9-editing-the-ontology)
10. [Adding a new source connector](#10-adding-a-new-source-connector)
11. [Privacy model](#11-privacy-model)
12. [Troubleshooting](#12-troubleshooting)
13. [API reference](#13-api-reference)

---

## 1. What this platform is

NEUROFORGE is a **personal medical research platform** that does three things:

1. **Ingests your clinical documents locally** (PDF, DOCX, PPTX, XLSX, CSV,
   TXT, MD, HTML, RTF, JSON) and extracts a structured profile of findings,
   symptoms, medications, and open diagnoses.
2. **Searches the medical literature in five tiers** — from peer-reviewed
   journals down to community forums and holistic sources — anchored to
   that profile.
3. **Produces graded, safety-screened briefings** per candidate intervention,
   so you have a discussion-ready summary of what the literature says about,
   say, lion's mane mushroom for the specific kind of lesion in your reports.

It is **local-first**: documents never leave your machine. Only abstract
mechanism queries (e.g. "clemastine remyelination") are sent to public
medical-research APIs.

The architectural pattern is forked from
[DEADSTICK](https://github.com/) (an aerospace mortality intelligence
platform), with sources swapped for medical and the safety/grading layers
rewritten for clinical research.

---

## 2. First run — installation

### Requirements

| Component | Version | Required for |
|---|---|---|
| Python | 3.11+ | Backend, scheduler, document ingest |
| Node.js | 18+ | Web UI |
| Git | any | Cloning the repo |
| Ollama | any recent | Optional — only for LLM-driven document extraction |

### Clone

```bash
git clone https://github.com/nicodemis222/neuroforge.git
cd neuroforge
```

### Install — macOS / Linux

```bash
python3 scripts/init.py        # checks + installs everything
./scripts/run_api.sh           # API + scheduler on :8077
./scripts/run_web.sh           # UI on :3210 (auto-runs npm install)
```

### Install — Windows

From `cmd` or PowerShell:

```bat
scripts\init.bat               :: checks + installs everything
scripts\run_api.bat            :: API + scheduler on :8077
scripts\run_web.bat            :: UI on :3210
```

If Python or Node aren't installed, `init` will tell you exactly what's
missing and where to download it. After installing, re-run `init`.

### Optional — multi-format document ingest

The base install supports PDF, TXT, CSV, TSV, JSON, HTML, and Markdown.
For DOCX, PPTX, XLSX, and RTF, install the optional ingest extras:

```bash
pip install -e 'services/api[ingest]'
```

This pulls `python-docx`, `python-pptx`, `openpyxl`, and `striprtf`.

### Optional — Ollama for LLM extraction

The PDF extractor uses an LLM to convert document text into structured
findings. Install Ollama from <https://ollama.com>, then:

```bash
ollama pull qwen2.5:7b
ollama serve
```

If Ollama isn't running, the platform falls back to the synthetic
example profile and warns you.

---

## 3. The init screen

The first time you open <http://localhost:3210>, the UI calls
`/api/init/status`. If anything's missing, it shows the **init screen**
instead of the dashboard.

The init screen is a checklist:

- ✅ green dot = ready
- ⚠️ amber dot = warning (not blocking)
- ❌ red = blocking (must be fixed)

Click **Run init** to install missing Python or web dependencies, bootstrap
the database, and verify network reachability. Output streams live as
Server-Sent Events. When the script finishes successfully, the **Enter
dashboard** button activates.

You can also re-run init any time from the command line:

```bash
python3 scripts/init.py              # full check + install
python3 scripts/init.py --no-install # check only, never install
python3 scripts/init.py --json       # JSON-lines (used by the UI)
```

---

## 4. Adding documents to the corpus

**Three ways to ingest documents.** All three end up calling the same
extractor pipeline.

### 4a. Drop into the folder

```bash
cp ~/Documents/my-mri-report.pdf  data/patient_corpus/
cp ~/Documents/labs.xlsx          data/patient_corpus/
cp ~/Documents/visit-summary.docx data/patient_corpus/
./scripts/seed.sh                 # macOS / Linux
scripts\seed.bat                  :: Windows
```

### 4b. Upload through the UI

The dashboard (when fully built out) exposes an upload panel that posts
to `/api/corpus/upload`. The endpoint enforces the supported-extension
allowlist server-side and rejects anything else with a clear error.

### 4c. Upload via API

```bash
curl -F 'files=@my-report.docx' \
     -F 'files=@labs.xlsx' \
     -F 'files=@conference-slides.pptx' \
     http://localhost:8077/api/corpus/upload

curl -X POST http://localhost:8077/api/corpus/extract
curl http://localhost:8077/api/profile          # see the merged profile
```

### Supported formats

| Extension | Format | Library |
|---|---|---|
| `.pdf` | PDF | pypdf |
| `.docx` | Word | python-docx |
| `.pptx` | PowerPoint | python-pptx |
| `.xlsx` `.xlsm` | Excel | openpyxl |
| `.csv` `.tsv` | Tabular | stdlib |
| `.txt` `.md` `.markdown` `.log` | Plain text | stdlib |
| `.html` `.htm` | HTML | stdlib HTMLParser |
| `.rtf` | Rich text | striprtf |
| `.json` | JSON | stdlib |

### How extraction works

1. The extractor walks `data/patient_corpus/` and computes a SHA-256 hash
   of every file. Hashes are persisted to `manifest.json` — unchanged files
   are never re-processed.
2. Each document is converted to plain text via the format-specific extractor.
3. Text is chunked (1200-char windows, 200-char overlap) and each chunk is
   sent to the LLM with a strict-JSON prompt asking for findings, symptoms,
   medications, and diagnoses.
4. Per-document extractions are merged across all files. Duplicates (same
   `(label, location)` for findings, same `label` for symptoms) are
   collapsed. Medications, diagnoses, and risk factors are unioned.
5. The merged result is written to `data/patient_corpus/profile.json`.

If `profile.json` exists, the platform loads it; otherwise it falls back
to the synthetic `DEFAULT` example profile bundled in
`app/seed/patient_profile.py`.

### Reset the corpus

```bash
rm -f data/patient_corpus/profile.json data/patient_corpus/manifest.json
rm -f data/neuroforge.db
```

The next ingest will re-extract from scratch.

---

## 5. Reading the dashboard

The dashboard at <http://localhost:3210> has three regions:

```
┌──────────────────────┬──────────────────────────────────────────┐
│  Sidebar             │  Main panel                              │
│  (intervention list) │                                          │
│                      │   [evidence × plausibility scatter]      │
│   ● clemastine       │                                          │
│   ● lions_mane       │   ─────────────────                      │
│   ● 7,8-DHF          │                                          │
│   ●… (~42 total)     │   [refresh] [briefing markdown]          │
└──────────────────────┴──────────────────────────────────────────┘
```

### The sidebar

Every intervention in the ontology, listed with:

- **Coloured dot** — current safety verdict (see §7).
  - 🟢 ok — no flags
  - 🟡 caution — review the rationale
  - 🟠 warn — discuss with clinician before considering
  - 🔴 hard_block — do not proceed without prerequisites met
- **Name** + category (drug / supplement / device / behavioral / holistic / biologic)
- **Tier** — where evidence is *expected* to live (T1 = peer-reviewed,
  T5 = holistic / fringe). The grading layer makes the final call from
  retrieved evidence.
- **n** — how many evidence rows have been retrieved for this intervention.
- **q** — mean evidence quality (0–1, GRADE-inspired).
- **p** — mean mechanistic plausibility against the loaded profile.

Click any row to drill into the briefing.

### The scatter plot

X-axis = evidence quality. Y-axis = mechanistic plausibility. Both 0–1.

- **Top-right quadrant** = high-quality literature that's directly relevant
  to your profile. **This is where to spend your reading time.**
- **Top-left** = relevant in mechanism but weak evidence. Watch list — keep
  an eye on whether stronger evidence appears.
- **Bottom-right** = high-quality but not directly relevant to your specific
  findings. Useful background.
- **Bottom-left** = noise.

Dot color = safety verdict. A high-quality, high-plausibility intervention
with a red dot is a candidate for *future* discussion with your clinician
once safety prerequisites are met (e.g. EEG capture, ASM coverage, washout
of an interacting medication).

### Refresh

The **↻ refresh evidence** button on a selected intervention queues a
synchronous run of the scheduler for just that intervention — useful when
you've just changed the ontology or want fresh hits without waiting for
the 6-hour cycle.

---

## 6. Reading a briefing

Each briefing is a markdown document with six sections:

### 1. Verdict

The safety verdict + flags + a roll-up of evidence count, mean quality,
and mean plausibility. **Read this first.**

### 2. Why this is on the list

Category, expected evidence tier, and which mechanistic targets the
intervention engages (e.g. "BDNF, TrkB, axonal sprouting"). The notes
field flags non-obvious context (e.g. "Russian heptapeptide; limited
Western trials").

### 3. Strongest evidence

Top 5 retrieved studies, ranked by `quality × plausibility`. Each shows:

- Title (linked to source)
- Connector source (pubmed / clinicaltrials / reddit:Stroke / etc.)
- Study type (rct / systematic_review / preclinical / community / …)
- q (quality) and p (plausibility) scores

### 4. Best objections / counter-evidence

High-quality studies with explicit "no benefit", "failed", "negative",
"null", or "no effect" phrasing. The platform actively *looks for*
disconfirming evidence so the briefing isn't a one-sided rec.

### 5. Practical considerations

Seizure-risk axis label, encoded interaction notes, and the patient's
current medication list (from the loaded profile).

### 6. Open questions

Templated questions to bring to your clinician — chronicity match, dosing
compatibility, seizure-threshold studies, anatomy-specific outcomes.

### Saving briefings

The API exposes `GET /api/intervention/{key}/briefing` returning markdown.
Pipe to a file:

```bash
curl http://localhost:8077/api/intervention/clemastine/briefing \
  | jq -r .markdown > briefings/clemastine.md
```

You can then convert to PDF with any markdown→PDF tool (`pandoc`, `mdbook`,
or your editor's export).

---

## 7. The safety screen

The screen is **profile-derived**, not hard-coded. When the loaded
profile changes (e.g. a new document adds a medication), all verdicts
re-compute on the next API call.

### Three axes

#### Seizure axis

The screen scans the profile's findings, symptoms, and diagnoses for
keywords (`seizure`, `epilep`, `ictal`, `convulsion`, `spell`, `aura`).
If found AND no antiseizure medication appears in the medication list:

- Interventions with `seizure_risk = "raises"` → **HARD_BLOCK**
- Interventions with `seizure_risk = "mixed"` → **CAUTION**
- Interventions with `seizure_risk = "lowers"` → **OK** (favorable note)

Adding an ASM (e.g. levetiracetam, lamotrigine) to your profile lifts
the hard-blocks to WARN.

#### Serotonergic axis

If the profile contains an SSRI, SNRI, or other serotonin modulator
(vortioxetine, fluoxetine, sertraline, venlafaxine, lithium, etc.):

- Strongly serotonergic interventions (psilocybin, DMT, lithium-augmenting
  protocols) → **HARD_BLOCK** with a serotonin-syndrome rationale
- Anything with a literature note about your specific medication → **CAUTION** or **HARD_BLOCK** (depending on the note phrasing)

#### Catecholaminergic axis

If the profile contains an NRI or stimulant (atomoxetine, methylphenidate,
amphetamine, modafinil, bupropion, etc.):

- Strongly sympathomimetic interventions (semax) → **WARN** with a BP/HR
  monitoring rationale
- Anything with a literature note about your medication → **CAUTION**

### Verdict semantics

| Verdict | What it means |
|---|---|
| **OK** | No flags. Standard clinical caution still applies. |
| **CAUTION** | Mixed signals or non-blocking interaction note. Read the rationale. |
| **WARN** | Active concern. Don't consider without clinician sign-off. |
| **HARD_BLOCK** | Prerequisite-gated. Do not proceed without resolving the prerequisite (e.g. EEG capture, ASM coverage, vortioxetine washout). |

The screen is **conservative by design**. False positives (over-flagging
something safe) are preferred to false negatives.

### Inspecting verdicts

```bash
curl http://localhost:8077/api/safety/psilocybin
```

```json
{
  "intervention_key": "psilocybin",
  "overall": "hard_block",
  "flags": [
    {
      "severity": "hard_block",
      "axis": "serotonergic",
      "rationale": "Psilocybin is strongly serotonergic; coadministration with vortioxetine risks serotonin syndrome…"
    }
  ]
}
```

---

## 8. Running searches — scheduler vs. once-mode

### Scheduler

When `NEUROFORGE_SCHEDULER=1` (the default in `run_api.sh` / `run_api.bat`),
the API spawns a background scheduler that:

1. Cycles through every intervention with jittered cadence
2. Runs every connector for that intervention × target × patient-anchor
   query
3. Persists evidence + grades to SQLite
4. Re-rolls the per-intervention scores every 3 minutes
5. Re-runs the safety screen hourly (in case you changed the profile)

A full cycle through ~42 interventions across ~13 connectors takes ~6 hours
at the default polite-pacing settings. **Run it overnight.**

### Once-mode

To seed the database fast for a single intervention:

```bash
./scripts/once.sh clemastine     # macOS / Linux
scripts\once.bat clemastine      :: Windows
```

This runs the full connector sweep for one intervention synchronously,
prints progress, exits when done. Useful for:

- First-run smoke testing
- Validating a newly-added connector
- Refreshing one intervention after editing the ontology

### Monitor progress

```bash
sqlite3 data/neuroforge.db "SELECT intervention_keys, COUNT(*) FROM evidence GROUP BY intervention_keys;"
sqlite3 data/neuroforge.db "SELECT * FROM intervention_score ORDER BY mean_quality DESC LIMIT 10;"
```

---

## 9. Editing the ontology

The ontology lives in two files. Edit, save, restart the API. The
scheduler picks up new entries on the next cycle.

### Adding a target

`services/api/app/ontology/targets.py`:

```python
Target("p21",
       "P21 (CDKN1A)",
       ("p21", "CDKN1A"),
       "process",
       0.7,
       "Senescence regulator; relevant to remyelination context."),
```

Fields:

- `key` — internal slug (snake_case)
- `canonical` — display name
- `synonyms` — search-side query expansion
- `mechanism` — `neurotrophin` | `growth factor` | `receptor` | `process` | `cell` | `pathway`
- `patient_relevance` — 0–1 prior used in plausibility scoring
- `notes` — free text shown in the briefing

### Adding an intervention

`services/api/app/ontology/interventions.py`:

```python
Intervention(
    "rapamycin", "Rapamycin (sirolimus)",
    ("rapamycin", "sirolimus"),
    "drug",
    ("mtor", "neurogenesis"),    # target keys it engages
    "T2",
    "mixed",                      # 'lowers'|'neutral'|'raises'|'mixed'|'unknown'
    ("vortioxetine: monitor — limited interaction data",),
    "mTOR inhibitor; preclinical longevity signal."),
```

The safety screen reads the `seizure_risk` and `interactions` fields
automatically — no separate code change needed for the safety logic to
apply to new interventions.

### Adding to the strong-interaction lists

If a new intervention is strongly serotonergic or sympathomimetic, add
its `key` to the relevant set in `app/safety/screen.py`:

```python
STRONG_SEROTONERGIC = {"psilocybin", "dmt", "lithium_micro", "your_new_key"}
```

---

## 10. Adding a new source connector

Every connector inherits from `app.connectors.base.Connector` and
implements one method: `async search(query, *, target_key, intervention_key, limit)`.

Skeleton:

```python
# app/connectors/my_source.py
from typing import AsyncIterator
from .base import Connector, Evidence, _parse_date

class MySourceConnector(Connector):
    key = "my_source"
    tier = "T2"                  # T1..T5
    polite_seconds = 1.0          # min seconds between requests

    async def search(self, query: str, *, target_key=None,
                     intervention_key=None, limit: int = 25
                     ) -> AsyncIterator[Evidence]:
        async with await self._client() as c:
            await self._polite()
            r = await c.get("https://example.com/api/search",
                            params={"q": query, "limit": limit})
            r.raise_for_status()
            for item in r.json().get("results", []):
                yield Evidence(
                    source=self.key,
                    tier=self.tier,
                    url=item["url"],
                    title=item["title"],
                    abstract=item.get("abstract", ""),
                    published=_parse_date(item.get("date")),
                    authors=item.get("authors", []),
                    target_keys=[target_key] if target_key else [],
                    intervention_keys=[intervention_key] if intervention_key else [],
                    study_type="rct",         # see grade.py for taxonomy
                    raw={"id": item.get("id")},
                )
```

Then register it in `app/connectors/__init__.py`:

```python
from .my_source import MySourceConnector

def all_connectors() -> list[Connector]:
    return [
        # …existing
        MySourceConnector(),
    ]
```

Restart the API. The scheduler picks it up on the next cycle.

### Connector design rules

- **Polite pacing**: never hit a host faster than `polite_seconds`. The
  base class enforces this via `await self._polite()`.
- **No exceptions to the caller**: catch network errors and yield zero
  results rather than aborting the loop.
- **No PII to remote endpoints**: queries should be mechanism + intervention
  terms only.
- **Tier honesty**: T1 = peer-reviewed primary literature; T5 = community/
  fringe. Pick the tier based on what the *typical* result looks like;
  the grading layer will adjust per-record.

---

## 11. Privacy model

### What stays local

- All documents in `data/patient_corpus/`
- The extracted `profile.json`
- The SQLite database `data/neuroforge.db`
- Generated briefings (until you explicitly export them)

### What goes to remote APIs

- Mechanism + intervention search queries (e.g. `"clemastine" AND ("BDNF") AND ("axonal sprouting")`)
- Standard HTTP headers (User-Agent identifies the platform; no patient ID)

### What does NOT go to remote APIs

- Any text from your documents
- Any names, dates of birth, MRNs, financial numbers, addresses
- Any specific finding *language* — only the abstracted mechanism keywords
  derived from the ontology

### Repository hygiene

`.gitignore` blocks the corpus directory, the database, secrets, and
build artifacts. The shipped `DEFAULT` profile is fully synthetic. If
you fork this repo and want to push back, run a final scan:

```bash
git ls-files | xargs grep -lEi "your-name|your-mrn|your-clinic" 2>/dev/null
```

before any push.

---

## 12. Troubleshooting

### "Init fails on Python deps"

```
[ERR] py_deps: pip install failed: …
```

Usually a permissions issue or an old pip. Try:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e services/api
```

### "Init says Ollama unreachable"

Ollama is **optional**. Without it, the platform uses the synthetic
`DEFAULT` profile and skips the LLM extraction pass. Install Ollama if
you want documents auto-converted to a profile.

### "The dashboard is empty"

The scheduler hasn't run yet. Either wait (~minutes for the first
intervention to populate) or trigger one explicitly:

```bash
./scripts/once.sh clemastine
```

Then refresh the dashboard.

### "Connector X always fails"

Check rate limits. Reddit, fringe DDG-scraping, and USPTO are the most
sensitive. The scheduler logs warnings per connector — find them with:

```bash
grep -i "failed:" logs/*.log    # if you redirected logs
```

Or run the API in foreground and watch stderr.

### "Safety verdicts look wrong"

Check the loaded profile:

```bash
curl http://localhost:8077/api/profile | jq
```

The screen reads `medications`, `findings`, `symptoms`, and `diagnoses_*`
from the profile. If a medication isn't being detected as serotonergic or
catecholaminergic, the medication name in your profile may not match the
substring lists in `app/safety/screen.py`. Either:

- Use the canonical generic name in your document (e.g. "vortioxetine"
  not just "Trintellix"), or
- Add the brand name to `SEROTONERGIC_RX` / `CATECHOLAMINERGIC_RX` /
  `ANTISEIZURE_RX` in `screen.py`.

### "Briefing is mostly empty"

That intervention hasn't been searched yet, or no connector returned
results. Run:

```bash
./scripts/once.sh <intervention_key>
```

and refresh.

### "I want to change a hard-block"

Don't. The hard-blocks are conservative on purpose. If you genuinely
need to override (e.g. you've just been cleared by your clinician), edit
the profile to reflect the new state — add the ASM that justifies lifting
a seizure block, or note the medication washout that lifts a serotonergic
block. The verdict will recompute automatically.

---

## 13. API reference

All endpoints served at `http://localhost:8077`.

### Health / state

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/init/status` | Prerequisite checklist (used by init screen) |
| `GET` | `/api/init/run` | Stream init.py output as SSE |
| `GET` | `/api/profile` | Currently loaded patient profile |

### Corpus

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/corpus` | List files + supported extensions |
| `POST` | `/api/corpus/upload` | Multipart upload (one or more files) |
| `DELETE` | `/api/corpus/{name}` | Remove a file |
| `POST` | `/api/corpus/extract` | Re-run extractor (background) |

### Ontology

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/ontology/targets` | All targets |
| `GET` | `/api/ontology/interventions` | All interventions + safety + scores |

### Per-intervention

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/intervention/{key}/evidence` | Retrieved evidence rows |
| `GET` | `/api/intervention/{key}/briefing` | Markdown briefing |
| `POST` | `/api/intervention/{key}/refresh` | Queue a synchronous search |
| `GET` | `/api/safety/{key}` | Current safety verdict |

---

## Final word

This platform is a **research lens**, not a decision-maker. Its job is
to surface what's been studied, weight it by quality and relevance to
your specific findings, and flag the safety prerequisites you'd otherwise
have to track manually.

The decisions stay with you and your treating clinicians.
