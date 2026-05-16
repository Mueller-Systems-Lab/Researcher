# ADR-006: Evidence-first Research Pipeline mit isoliertem Tool-Layer

**Status:** Proposed  
**Datum:** 2026-05-16  
**Autor:** Architecture Review Agent  
**Kontext:** Architecture Review von `deepresearch-agent-stack.md`

---

## Context

Das Researcher-Projekt soll skalierbare, lokale und reproduzierbare Deep Research betreiben. Der aktuelle Blueprint `deepresearch-agent-stack.md` trennt Research Coordinator, MCP Tool Layer, Search Workers, Extraction Workers, Validation Workers und Local LLM Synthesis. Der Architecture Review vom 2026-05-16 ergab folgende kritische Lücken:

1. Kein formaler Evidence Store → keine echte Reproduzierbarkeit
2. Pipeline falsch sequenziert (Contradiction Analysis nach Synthesis)
3. vLLM auf GTX 1070 nicht lauffähig (CC 6.1 vs. benötigt ≥7.5)
4. Vier Datenbanken ohne Rollenzuweisung (PostgreSQL + Qdrant + Chroma + SQLite)
5. Onion/Darknet-Security zu vage spezifiziert
6. Deterministische Reports nicht technisch abgesichert
7. Human-in-the-loop Gates fehlen für riskante Operationen
8. MCP-Tools unvollständig
9. Inference-Backend nicht abstrahiert (Ollama vs. llama-server)

---

## Decision

Wir führen eine **Evidence-first Research Pipeline** mit folgendem Architektur-Update ein:

### 1. Evidence Store (NEU)

Jede gefetchte Quelle wird vor Synthese als Evidence Artifact gespeichert:

```json
{
  "evidence_id": "ev-20260516-0001",
  "source_url": "https://...",
  "snapshot_hash": "sha256:...",
  "retrieved_at": "2026-05-16T...",
  "extract_start_char": 1234,
  "extract_end_char": 1602,
  "parser": "crawl4ai@0.8.x",
  "confidence": 0.78
}
```

### 2. Pipeline-Reihenfolge korrigiert

Contradiction Analysis VOR LLM-Synthese:

1. Research Planning / Topic Decomposition
2. Query Expansion / Source Strategy
3. Multi-source Retrieval
4. Fetch / Snapshot / Extraction
5. Normalization / Deduplication / Caching
6. Source Credibility + Evidence Scoring
7. Contradiction + Gap Analysis
8. LLM Synthesis mit Evidence Constraints
9. Final Claim Verification
10. Report Generation + Reproducibility Manifest

### 3. vLLM gestrichen

vLLM erfordert Compute Capability ≥7.5. GTX 1070 (CC 6.1) wird nicht unterstützt.

**Backend-Strategie:**
- MVP: Ollama (Port 11434)
- Reproducibility: llama-server (Port 8085/8086)
- Backend-Abstraktion: `INFERENCE_BACKEND=ollama|llama-server`

### 4. Storage-Klärung

| Store | Zweck | MVP |
|---|---|---|
| ChromaDB | Vektorsuche | ✅ |
| SQLite / PostgreSQL | Metadata, Research Runs, Claims, Citations, Audit | ✅ |
| Filesystem | Raw Snapshots | ✅ |
| Qdrant | Produktiver Vektor-Store (Upgrade-Pfad) | ❌ Später |

Kein gleichzeitiger Betrieb von Chroma + Qdrant ohne Migrationsstrategie.

### 5. Onion/Darknet-Isolation

Drei strikte Netzwerkzonen:

```text
Clearnet Zone
  - SearXNG, web-search, web-fetch, normale Extraktion

Onion Zone [disabled by default]
  - Tor-Client, onion-crawler, onion-parser

Offline Zone
  - Evidence Validator, LLM Synthesis, Citation Engine
```

Regeln:
- Onion-Worker nur über Tor-Egress
- Kein Clearnet-Worker löst `.onion`-Domains auf
- DNS im Onion-Worker nur über Tor/SOCKS
- Human Approval vor dauerhafter Speicherung
- Keine automatische Binary-Verarbeitung aus Onion-Quellen

### 6. Deterministisches Research-Profil

Zwei Betriebsmodi:

| Modus | Temperature | Zweck |
|---|---|---|
| `research-exploratory` | 0.7 | Brainstorming, Query Expansion |
| `research-deterministic` | 0 | Reproduzierbare Synthese, Final Report |

Erfordert: fixe Modellversion, fixe Prompt-Version, fixe Evidence-Snapshots, fixe Quellen-Sortierung.

### 7. MCP-Tools erweitert

| Kategorie | Tools |
|---|---|
| Retrieval | `web-search`, `web-fetch`, `archive-fetch`, `onion-search`, `local-index-search` |
| Extraction | `document-parser`, `html-to-markdown`, `pdf-extract`, `metadata-extract` |
| Evidence | `evidence-store`, `citation-engine`, `source-snapshot`, `claim-extractor`, `claim-validator` |
| RAG | `vector-search`, `vector-upsert`, `reranker` |
| Synthesis | `summarizer`, `report-generator`, `markdown-export`, `reproducibility-manifest` |
| Governance | `policy-check`, `human-review-request`, `audit-log` |

### 8. Human-in-the-loop Gates

Erforderlich bei:
- Onion/Darknet-Quellen (Default: blockiert)
- Potenziell illegalen Inhalten
- Personenbezogenen Daten
- Niedriger Confidence (< 0.5)
- Widersprüchlichen Quellen
- Binary-Downloads

---

## Alternatives Considered

### Alternative A: Bestehender linearer Blueprint

**Pipeline:** Search → Extraction → Validation → Synthesis

**Vorteile:** Einfach, geringe Komplexität, schnell umsetzbar

**Nachteile:** Keine belastbare Reproduzierbarkeit, schwache Evidence Chain, Widerspruchsanalyse zu spät, Onion-Security unzureichend

**Bewertung:** Nicht ausreichend für skalierbare Deep Research

---

### Alternative B: GPT Researcher direkt erweitern, ohne MCP-Layer

**Vorteile:** Weniger Infrastruktur, schneller MVP, weniger Tool-Abstraktion

**Nachteile:** Stärkere Kopplung an GPT Researcher Interna, schwerere Sicherheitsgrenzen, schlechtere Auditierbarkeit, schwieriger mehrere Worker-Typen zu isolieren

**Bewertung:** Für Prototyp möglich, langfristig schlechter

---

### Alternative C: Vollständige Microservice-Architektur (PostgreSQL + Qdrant + Object Storage)

**Vorteile:** Skalierbar, klare Persistenzgrenzen, gut auditierbar

**Nachteile:** Zu komplex für GTX-1070-MVP, mehr Betriebsaufwand, mehr Fehlerquellen

**Bewertung:** Zielbild für spätere Version, nicht MVP

---

## Consequences

### Wird einfacher

- Reproduzierbare Zitate durch Evidence Store und Snapshots
- Claim-Level-Validierung
- Auditierbarkeit aller Research Runs
- Security Review durch Netzwerkzonen
- Spätere Migration von Chroma zu Qdrant
- Deterministische Report-Replays

### Wird schwieriger

- Höhere Implementierungskomplexität
- Mehr Metadatenpflege
- Mehr Tests erforderlich (Evidence-, Security-, Reproducibility-Tests)
- Höhere Anforderungen an Storage- und Tool-Schemas
- Human Review kann Automatisierung verlangsamen
- Inference-Backend muss abstrahiert werden

### Risiken

- Fehlende Human-Review-Kapazität als Bottleneck
- Storage-Anforderungen steigen mit Evidence-Archivierung
- Tool-Breite erfordert mehr Wartung
- Rechtliche Grauzonen bei Onion-Nutzung

---

## Implementation Plan

1. `deepresearch-agent-stack.md` um Review-Abschnitt ergänzen
2. `design.md` aktualisieren (ADR-006 referenzieren)
3. Inference-Abstraktion in `.env.example` aufnehmen: `INFERENCE_BACKEND`
4. Evidence-Store-Schema als Draft in `specs/delta-specs.md` dokumentieren
5. GitHub Issues für Teilaufgaben erstellen (T-015 bis T-020)
