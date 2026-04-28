# v4 — Real Agents and RAG

**Status:** designed, not built. v3 (current) is a deterministic pipeline.

The platform calls itself a "research cockpit" but as of v3 there are
**no LLM-driven agents in the runtime path.** Connectors are templated HTTP
clients, grading is rule-based, briefings are f-string templates, and the
synopsis is a SQL aggregation. The only LLM call is in `app/seed/extractor.py`
for document → profile extraction.

This document captures what an actual agent + RAG layer would look like and
why each piece would move the needle. It is the v4 design, not a roadmap
commitment.

## What's missing

### 1. Synthesis agent (highest leverage)

**Today:** `briefing/generator.py` returns a templated bullet list of the
top 5 retrieved studies. The user has to read each abstract themselves to
know what the literature *says*.

**v4:** RAG over the abstracts and full-text snippets retrieved for an
intervention. The synthesis agent prompts an LLM with:

- The current hypothesis statement
- Patient anchors (anatomy, chronicity, meds)
- Top 10 retrieved evidence rows by `quality × plausibility`
- Their abstracts (chunked + embedded for selective retrieval)

…and produces section 3 of the briefing as grounded prose: *"Three RCTs
(Cree 2017, Mei 2014, Green 2017) report …, with pooled effect size …
on …. The most relevant to this patient's chronic CST lesion is …
because …."* Citations stay attached to claims via inline markers.

**Why it works:** RAG forces the LLM to ground claims in the actual
abstracts. Hallucination risk drops sharply when the model is asked to
summarize a fixed window of retrieved text rather than recall from
training.

### 2. Critic agent

**Today:** the briefing surfaces "best objections" by keyword search for
"failed", "no benefit", etc. — brittle.

**v4:** an adversarial pass that:

- Re-queries connectors with negation/null phrasing
- Checks dose-feasibility (does the BBB-permeable dose match the
  benefit dose?)
- Flags "patient mismatch" claims (e.g. evidence is acute-injury but
  patient has chronic lesion)

Output replaces section 4 of the briefing with concrete, sourced
counter-evidence rather than keyword artifacts.

### 3. Coverage agent

**Today:** `intervention_loop` round-robins through 42 interventions.

**v4:** an agent that decides next-best-query based on coverage gaps in
the database. Reads `coverage_by_target × tier` and picks the most
under-explored cell. Avoids over-indexing on whatever happens to be
alphabetically first.

### 4. Triage agent on briefing open

**Today:** clicking a low-`n` intervention shows an empty briefing.

**v4:** before rendering, check if the evidence base is too thin (e.g.
`n_evidence < 8` or no T1 hits) and synchronously top up by calling
2-3 specific connectors with targeted queries before generating the
briefing.

## Embeddings + RAG infrastructure

The pieces above all need a vector store and embedding pipeline. Sketch:

| Component | Implementation |
|---|---|
| Embedding model | `nomic-embed-text` via Ollama (already used in deadstick) |
| Vector store | Postgres + pgvector (replace SQLite at the same time, since we'd want concurrent writes) |
| Chunking | abstracts get chunked at 600 tokens with 100-token overlap; metadata = `(intervention_key, target_keys, fingerprint, study_type, tier)` |
| Retrieval | cosine + metadata filter (e.g. "only RCTs in T1 mentioning CST") |
| Reranker | optional cross-encoder or just `quality × plausibility × cosine_sim` |

Synthesis agent sees the top-K chunks within a claim's intervention scope.

## Suggested model tiers

Mirror deadstick's three-tier pattern:

| Tier | Model | Used for |
|---|---|---|
| triage | `llama3.2:latest` (3B) | Document extraction (current), classification, keyword expansion |
| fast  | `qwen3.5:latest` or `qwen2.5:7b` | Synthesis agent, critic agent |
| deep  | `qwen2.5:32b` or larger | Cross-evidence reasoning, end-of-day synopsis narrative |

`OLLAMA_NUM_PARALLEL=2` so the user-facing chat (if any) doesn't queue
behind a long agent run.

## Failure modes to plan for

- **Hallucinated citations** — every quoted claim must include an inline
  pointer to the exact retrieved chunk; if missing, the renderer flags it
- **Stale embedding index** — invalidate on evidence delete + on
  re-grading
- **Context bloat** — retrieve top-K chunks not full abstracts; cap
  total context at 8K tokens
- **Slow first response** — cache synthesis output keyed by the set of
  fingerprints retrieved + the model version

## Why not now

- v3 platform produces useful output without it. Adding agents while the
  rule-based output is still being validated would conflate "is the
  ontology right" with "is the agent reasoning right."
- Local hardware budget: synthesis agent at qwen3.5 takes ~30s per
  briefing. Acceptable on demand, not in every scheduler tick.
- Schema migration to Postgres is non-trivial (pyproject + connectors
  upsert layer + Alembic).

## Triggers to start v4

Build this when one of these is true:

1. The bullet-list briefing format becomes the bottleneck — i.e. you
   regularly want more synthesis than the template can give
2. The user starts asking cross-evidence questions ("which interventions
   in my list have the most overlap with the Cree 2017 cohort?")
3. The ontology stabilizes such that adding an intervention is rare —
   so we know the deterministic core works and additions are agent-driven
