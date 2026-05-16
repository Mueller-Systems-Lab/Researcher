# Deep Research Agent Stack Blueprint

## Goal

Build a scalable autonomous research stack using:

- GPT Researcher concepts
- local LLMs
- MCP orchestration
- RAG pipelines
- evidence validation
- reproducible outputs

---

# Core Principle

Research quality is more important than generation quantity.

The system MUST prioritize:

- evidence
- citations
- reproducibility
- validation
- source quality

---

# Architecture

```text
Research Coordinator
    ↓
MCP Tool Layer
    ↓
Search Workers
    ↓
Extraction Workers
    ↓
Validation Workers
    ↓
Local LLM Synthesis
```

---

# Recommended Components

## Search

- crawl4ai
- browser-use
- custom scrapers
- onion crawlers

## Storage

- ChromaDB — Vektorspeicher für Embeddings
- SQLite/PostgreSQL — Evidence, Metadata, Research Runs, Claims, Citations, Audit
- Filesystem — Raw Snapshots und Reproducibility Manifests
- Whoosh — lokaler Onion-/Darknet-Volltextindex im MVP
- Qdrant — späterer produktiver Vektor-Store als Upgrade-Pfad

## Inference

- llama-server
- Ollama

---

# Mandatory Validation

Every claim MUST:

- contain source references
- contain extraction context
- contain timestamp metadata
- contain confidence metadata

---

# Research Pipeline

## Phase 1

Topic decomposition

## Phase 2

Multi-source retrieval

## Phase 3

Deduplication

## Phase 4

Source credibility scoring

## Phase 5

Evidence extraction

## Phase 6

Contradiction analysis

## Phase 7

LLM synthesis

## Phase 8

Final report generation

---

# Hallucination Reduction Rules

The LLM MUST:

- separate facts from assumptions
- reject unsupported claims
- mark uncertainty explicitly
- avoid unsupported summaries

---

# Security Rules

The system MUST:

- isolate darknet access
- separate scraping workers
- sandbox browser execution
- validate downloads
- prohibit arbitrary binary execution

---

# Recommended MCP Tools

- web-search
- web-fetch
- onion-search
- browser-use
- markdown-export
- vector-search
- citation-engine
- evidence-store
- claim-validator
- audit-log
- human-review-request
- document-parser
- screenshot-analysis

---

# Acceptance Criteria

The system is complete only if:

- citations are reproducible
- reports are deterministic
- evidence chains exist
- unsupported claims are rejected
- sources are traceable

---

# Architecture Review 2026-05-16

**Bewertung:** 8/10 — Die kritischen Architekturentscheidungen sind dokumentiert; mehrere Gates und Tooling-Aspekte bleiben als geplante Umsetzung offen.

## Ergebnisse

Der Architecture Review zu Issue #14 identifizierte 10 Gaps. Der verbindliche Nachweis steht in ADR-009; die Zielarchitektur wird durch ADR-006, ADR-007 und ADR-008 konkretisiert.

| # | AC | Gap | Status | Referenz |
|---|---|---|---|---|
| 1 | AC-1 | ADR-006 war Proposed und musste akzeptiert werden. | ✅ Erledigt | ADR-006, ADR-009 |
| 2 | AC-2 | Blueprint brauchte einen Architecture-Review-Abschnitt. | ✅ Erledigt | dieser Abschnitt, ADR-009 |
| 3 | AC-3 | Storage-Rollen waren unklar. | ✅ Erledigt | ADR-006, ADR-008, ADR-009 |
| 4 | AC-4 | vLLM war trotz GTX 1070 / CC 6.1 gelistet. | ✅ Erledigt | ADR-006, ADR-009 |
| 5 | AC-5 | Onion-Security war zu vage. | ✅ Erledigt | ADR-006, ADR-007, ADR-009 |
| 6 | AC-6 | Inference-Backend war nicht abstrahiert. | ✅ Erledigt | ADR-006, `.env.example`, ADR-009 |
| 7 | AC-7 | Deterministisches Profil war nicht technisch definiert. | ⏳ Geplant | ADR-006, ADR-009 |
| 8 | AC-8 | MCP-Tools für Evidence/Governance fehlten. | ⏳ Geplant | ADR-006, ADR-009 |
| 9 | AC-9 | Contradiction Analysis kam nach LLM-Synthese. | ✅ Erledigt | ADR-006, ADR-009 |
| 10 | AC-10 | Human Gates für Onion, Binary-Downloads und Low-Confidence fehlten. | ⏳ Geplant | ADR-006, ADR-007, ADR-009 |

## ADR-Referenzen

- `docs/adr/006-evidence-first-pipeline.md` — akzeptierte Evidence-first Pipeline, Storage-Rollen, Netzwerkzonen, deterministisches Profil, MCP-Tools, Human Gates.
- `docs/adr/007-onion-discovery-engine.md` — Onion Discovery Engine, disabled-by-default Onion Zone, Tor/SOCKS, Human Approval.
- `docs/adr/008-onion-search-index.md` — Whoosh als MVP-Index, Qdrant/Meilisearch/Typesense/OpenSearch als spätere Upgrade-/Review-Pfade.
- `docs/adr/009-architecture-review-gaps.md` — Gap-für-Gap-Nachweis für Issue #14.
