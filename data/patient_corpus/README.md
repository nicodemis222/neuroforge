# Patient corpus

Drop your own clinical documents here. Supported formats:

| Format | Extension(s) | Library used |
|---|---|---|
| PDF | `.pdf` | `pypdf` |
| Word | `.docx` | `python-docx` |
| Plain text | `.txt`, `.md`, `.markdown`, `.log` | stdlib |
| CSV / TSV | `.csv`, `.tsv` | stdlib `csv` |
| Excel | `.xlsx`, `.xlsm` | `openpyxl` |
| PowerPoint | `.pptx` | `python-pptx` |
| HTML | `.html`, `.htm` | stdlib `html.parser` |
| RTF | `.rtf` | `striprtf` |
| JSON | `.json` | stdlib |

After adding files, run:

```bash
# macOS / Linux
./scripts/seed.sh
# Windows
scripts\seed.bat
```

This will:
1. Compute a content hash for each file (idempotent — won't re-process unchanged files).
2. Extract text via the appropriate parser.
3. Chunk + run an LLM extraction pass (needs Ollama running with a chat model — defaults to `qwen2.5:7b`).
4. Merge findings/symptoms/medications across documents into `profile.json`.
5. The platform's `app.seed.patient_profile.load()` prefers `profile.json` over the synthetic default.

## Privacy

This directory is in `.gitignore`. Nothing here is committed to the repository. The platform runs entirely on your local machine — no document content leaves your computer except for the search queries the connectors send to public medical-research APIs (PubMed, ClinicalTrials.gov, etc.), and those queries do not contain document content. They use only the high-level mechanism + intervention terms from the ontology.

If you want to remove all extracted state and start over:

```bash
rm -f data/patient_corpus/profile.json data/patient_corpus/manifest.json
rm -f data/neuroforge.db
```
