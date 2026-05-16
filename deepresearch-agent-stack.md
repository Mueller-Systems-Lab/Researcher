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

- PostgreSQL
- Qdrant
- Chroma
- SQLite

## Inference

- llama-server
- Ollama
- vLLM

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

LLM synthesis

## Phase 7

Contradiction analysis

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
- onion-search
- browser-use
- markdown-export
- vector-search
- citation-engine
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

# Architecture Review (2026-05-16)

**Bewertung:** 6.5/10 — Architektonische Richtung gut, aber noch nicht implementierbar.

## Ergebnisse

Der Architecture Review identifizierte 9 kritische Lücken:

| # | Problem | Impact |
|---|---|---|
| 1 | Kein Evidence Store | Ohne Snapshots keine echte Reproduzierbarkeit |
| 2 | Pipeline falsch sequenziert | Contradiction Analysis kommt nach der Synthese |
| 3 | vLLM auf GTX 1070 | vLLM braucht CC ≥7.5, GTX 1070 hat nur 6.1 |
| 4 | 4 Datenbanken ohne Rollenzuweisung | PostgreSQL + Qdrant + Chroma + SQLite zu redundant |
| 5 | Onion-Security zu vage | Netzwerkisolation nicht spezifiziert |
| 6 | Deterministische Reports nicht technisch | temperature 0.7 widerspricht Ziel |
| 7 | Keine Human-in-the-loop Gates | Onion-Zugriff braucht Freigabe |
| 8 | MCP-Tools unvollständig | web-fetch, evidence-store, claim-validator fehlen |
| 9 | Inference-Backend nicht abstrahiert | Ollama vs. llama-server nicht vereinheitlicht |

## ADR-006

Details und Lösungsweg: `docs/adr/006-evidence-first-pipeline.md`
