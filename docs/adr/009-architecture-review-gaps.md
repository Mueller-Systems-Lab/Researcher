# ADR-009: Architecture Review Gaps für Evidence-first Pipeline

**Status:** Accepted  
**Datum:** 2026-05-16  
**Autor:** Architecture Review Agent  
**Kontext:** Issue #14 — Evidence-first Pipeline & Security Gates

---

## Context

Issue #14 verlangt den Nachweis, dass zehn Architektur-Lücken aus dem Review von `deepresearch-agent-stack.md` geschlossen oder bewusst als Folgearbeit markiert wurden. Die Entscheidung baut auf ADR-001 bis ADR-008 auf:

- ADR-001 in `design.md`: Ollama statt llama.cpp direkt (`design.md:42-45`).
- ADR-002 in `design.md`: CompositeRetriever-Pattern (`design.md:47-50`).
- ADR-003 in `design.md`: Embeddings auf CPU (`design.md:52-56`).
- ADR-004 in `design.md`: Whoosh statt Elasticsearch/Meilisearch für Darknet-Index (`design.md:58-61`).
- ADR-005 in `design.md`: synthetische URIs für Darknet-Quellen (`design.md:63-67`).
- ADR-006: Evidence-first Pipeline, Storage-Rollen, Netzwerkzonen, deterministisches Profil, MCP-Tools und Human Gates (`docs/adr/006-evidence-first-pipeline.md:26-135`).
- ADR-007: Onion Discovery als disabled-by-default Onion-Zone-Worker mit Tor/SOCKS, Human Approval und no-live-retrieval (`docs/adr/007-onion-discovery-engine.md:72-80`).
- ADR-008: Whoosh bleibt MVP-Suchindex; Meilisearch/Typesense/OpenSearch sind keine MVP-Abhängigkeiten (`docs/adr/008-onion-search-index.md:22-34`).

---

## Decision

ADR-006 wird akzeptiert und die zehn Review-Gaps werden in Blueprint, ADR-006, ADR-009 und `.env.example` nachvollziehbar abgebildet. Nicht vollständig implementierte Fähigkeiten bleiben als geplante Architekturarbeit markiert, statt stillschweigend als erledigt zu gelten.

---

## Alternatives Considered

### Alternative A: Nur ADR-006 akzeptieren

- **Vorteil:** Minimaler Dokumentationsaufwand.
- **Nachteil:** Kein Gap-für-Gap-Nachweis, keine nachvollziehbare Trennung zwischen gelöst, geplant und abgelehnt.
- **Bewertung:** Abgelehnt, weil Issue #14 explizit eine vollständige Review-Abdeckung fordert.

### Alternative B: Gaps nur im Blueprint dokumentieren

- **Vorteil:** Review ist direkt am Blueprint sichtbar.
- **Nachteil:** Blueprint ist kein ADR; Entscheidungen, Alternativen und Konsequenzen wären nicht ADR-konform dokumentiert.
- **Bewertung:** Abgelehnt, weil signifikante Architekturentscheidungen ADR-pflichtig sind.

### Alternative C: ADR-009 als Review-Nachweis plus Blueprint-Zusammenfassung

- **Vorteil:** ADR-009 liefert den stabilen Entscheidungsnachweis; der Blueprint erhält eine kurze lesbare Review-Zusammenfassung.
- **Nachteil:** Zwei Dokumente müssen konsistent bleiben.
- **Bewertung:** Gewählt.

---

## Gap Review

### Gap 1 — AC-1: ADR-006 dokumentiert und akzeptiert

- **Gap:** ADR-006 war im Review-Kontext nur vorgeschlagen; Issue #14 verlangt Statusprüfung und Annahme.
- **Bewertung:** Gelöst. ADR-006 steht auf `Accepted` und enthält Context, Decision, Alternatives, Consequences, Traceability und References (`docs/adr/006-evidence-first-pipeline.md:1-6`, `docs/adr/006-evidence-first-pipeline.md:138-199`).
- **Entscheidung:** ADR-006 wird als verbindliche Architekturentscheidung akzeptiert.
- **Status:** ✅ Erledigt

### Gap 2 — AC-2: Architecture Review im Blueprint

- **Gap:** Der Blueprint braucht einen expliziten Architecture-Review-Abschnitt mit Gap-Status und ADR-Referenzen.
- **Bewertung:** Gelöst durch Aktualisierung von `deepresearch-agent-stack.md`; der bisherige Review-Abschnitt enthielt nur neun Lücken (`deepresearch-agent-stack.md:167-189`) und wurde auf zehn Gaps erweitert.
- **Entscheidung:** Der Blueprint enthält am Ende `## Architecture Review 2026-05-16` mit Status je Gap und Referenzen auf ADR-006, ADR-007, ADR-008 und ADR-009.
- **Status:** ✅ Erledigt

### Gap 3 — AC-3: Storage-Rollen definiert

- **Gap:** PostgreSQL, Qdrant, Chroma und SQLite waren ohne klare Rollen gelistet (`deepresearch-agent-stack.md:57-63`). Dadurch drohen redundante Stores, erhöhte Kopplung und unklare Reproduzierbarkeit.
- **Bewertung:** Teilweise implementiert und architektonisch gelöst. ChromaDB ist als persistenter Vektorspeicher implementiert (`vectordb/store.py:21-39`, `vectordb/store.py:79-180`); Whoosh ist als Volltextindex implementiert (`darknet_search/index.py:27-36`, `darknet_search/index.py:117-166`). ADR-006 definiert zusätzlich SQLite/PostgreSQL für Evidence/Metadata/Audit, Filesystem für Raw Snapshots und Qdrant als Upgrade-Pfad (`docs/adr/006-evidence-first-pipeline.md:71-80`).
- **Entscheidung:** MVP nutzt ChromaDB für Vektoren, Whoosh für Onion-Volltext, SQLite/PostgreSQL für Evidence-/Metadata-/Audit-Daten, Filesystem für Snapshots; Qdrant bleibt Upgrade-Pfad.
- **Status:** ✅ Erledigt

### Gap 4 — AC-4: vLLM entfernen

- **Gap:** vLLM war im Blueprint als Inference-Komponente gelistet (`deepresearch-agent-stack.md:64-69`), passt aber nicht zur GTX 1070 / Compute Capability 6.1.
- **Bewertung:** Gelöst. ADR-006 streicht vLLM aus dem MVP und definiert Ollama sowie llama-server als unterstützte Backends (`docs/adr/006-evidence-first-pipeline.md:62-70`); der Blueprint listet vLLM nicht mehr als empfohlenes Backend.
- **Entscheidung:** vLLM wird aus dem Blueprint-MVP entfernt; Inference läuft über Ollama oder llama-server.
- **Status:** ✅ Erledigt

### Gap 5 — AC-5: Onion-Security mit drei Netzwerkzonen

- **Gap:** Blueprint-Sicherheitsregeln waren zu allgemein: isolate darknet access, separate scraping workers, sandbox browser execution, validate downloads (`deepresearch-agent-stack.md:130-139`).
- **Bewertung:** Gelöst. ADR-006 definiert Clearnet, Onion und Offline Zone sowie DNS-/Tor-Regeln und Human Approval (`docs/adr/006-evidence-first-pipeline.md:82-103`). Die Pipeline ist disabled by default (`onion_discovery/engine.py:87-103`) und nutzt `socks5h://127.0.0.1:9050` für Remote-DNS über Tor (`onion_discovery/engine.py:49-58`, `onion_discovery/engine.py:68-85`). ADR-007 konkretisiert diese Grenzen (`docs/adr/007-onion-discovery-engine.md:72-80`).
- **Entscheidung:** Onion-Zugriffe bleiben in der Onion Zone, standardmäßig deaktiviert, ausschließlich über Tor/SOCKS mit Remote-DNS; dauerhafte Speicherung erfolgt erst nach Human Approval.
- **Status:** ✅ Erledigt

### Gap 6 — AC-6: Inference-Abstraktion

- **Gap:** Ollama und llama-server waren nicht über eine Konfigurationsvariable vereinheitlicht; `.env.example` enthielt nur Ollama-Variablen (`.env.example:11-22`).
- **Bewertung:** Gelöst durch `INFERENCE_BACKEND=ollama` in `.env.example` und ADR-006-Backend-Strategie (`docs/adr/006-evidence-first-pipeline.md:66-70`).
- **Entscheidung:** `INFERENCE_BACKEND=ollama|llama-server` ist die Architekturgrenze für austauschbares lokales LLM-Serving.
- **Status:** ✅ Erledigt

### Gap 7 — AC-7: Deterministisches Profil

- **Gap:** Der Blueprint fordert deterministische Reports (`deepresearch-agent-stack.md:155-164`), spezifizierte aber keine technische Reproduzierbarkeit. Der Review hatte `temperature 0.7` als Widerspruch zum Ziel markiert (`deepresearch-agent-stack.md:181-183`).
- **Bewertung:** Architektonisch gelöst, Implementierung folgt. ADR-006 definiert `research-deterministic` mit `temperature=0`, fixer Modellversion, fixer Prompt-Version, fixen Evidence-Snapshots und fixer Quellen-Sortierung (`docs/adr/006-evidence-first-pipeline.md:104-113`).
- **Entscheidung:** Final Reports und reproduzierbare Synthese müssen im deterministischen Profil laufen; explorative Schritte dürfen separat bleiben.
- **Status:** ⏳ Geplant

### Gap 8 — AC-8: MCP-Tools ergänzt

- **Gap:** Der Blueprint listete MCP-Tools, aber es fehlten `web-fetch`, `evidence-store`, `claim-validator`, `audit-log` und `human-review-request` (`deepresearch-agent-stack.md:142-152`).
- **Bewertung:** Architektonisch gelöst, Implementierung folgt. ADR-006 ergänzt die Tool-Taxonomie mit Retrieval-, Evidence- und Governance-Tools inklusive `web-fetch`, `evidence-store`, `claim-validator`, `audit-log` und `human-review-request` (`docs/adr/006-evidence-first-pipeline.md:115-125`). Die Projektregel verlangt außerdem klare MCP-Trennung zwischen Resources, Prompts und Tools (`researcher_research_first_rule.md:249-284`).
- **Entscheidung:** MCP-Tools werden sicherheitsbegrenzt ergänzt; gefährliche generische Tools wie `crawl_anything` bleiben verboten.
- **Status:** ⏳ Geplant

### Gap 9 — AC-9: Pipeline-Reihenfolge korrigiert

- **Gap:** Im Blueprint kam LLM synthesis vor Contradiction analysis (`deepresearch-agent-stack.md:101-115`), wodurch Widersprüche zu spät geprüft würden.
- **Bewertung:** Gelöst. ADR-006 ordnet Contradiction + Gap Analysis vor LLM Synthesis ein (`docs/adr/006-evidence-first-pipeline.md:47-60`); der Blueprint wurde entsprechend angepasst.
- **Entscheidung:** Evidence Extraction, Scoring und Contradiction Analysis müssen vor der LLM-Synthese abgeschlossen sein.
- **Status:** ✅ Erledigt

### Gap 10 — AC-10: Human-in-the-loop Gates

- **Gap:** Human Gates für Onion, Binary-Downloads und Low-Confidence waren im Blueprint nicht explizit. Der ursprüngliche Review nannte fehlende Human-in-the-loop Gates (`deepresearch-agent-stack.md:181-184`).
- **Bewertung:** Teilweise implementiert und architektonisch gelöst. `ReviewQueue` verwaltet Approval/Reject für Onion-Quellen (`onion_discovery/human_review.py:44-158`), und `DiscoveryPipeline` sendet reviewpflichtige Klassifikationen in die Queue (`onion_discovery/engine.py:181-200`). ADR-006 definiert Gates für Onion/Darknet, potenziell illegale Inhalte, personenbezogene Daten, niedrige Confidence, widersprüchliche Quellen und Binary-Downloads (`docs/adr/006-evidence-first-pipeline.md:126-135`). Binary- und Low-Confidence-Gates sind architektonisch definiert, aber noch nicht vollständig als eigenständige Pipeline-Gates nachgewiesen.
- **Entscheidung:** Human Approval ist Pflicht für Onion, Binary-Downloads und Low-Confidence; die bestehende ReviewQueue bleibt der MVP-Mechanismus und wird für weitere Gate-Typen erweitert.
- **Status:** ⏳ Geplant

---

## Consequences

### Wird einfacher

- Architekturstatus von Issue #14 ist prüfbar und quellenbasiert.
- ADR-006, ADR-007 und ADR-008 bleiben konsistent: Evidence-first Pipeline, sichere Onion Discovery und MVP-tauglicher Search Index.
- Storage-, Inference-, Security- und Human-Gate-Grenzen sind explizit.

### Wird schwieriger

- Determinismus, Evidence Store, MCP-Tools und zusätzliche Human Gates brauchen Folgeimplementierung und Tests.
- Mehr Artefakte müssen synchron gehalten werden: Blueprint, ADRs, Specs und `.env.example`.

### Risiken

- Dokumentierte Gates ohne technische Durchsetzung können Scheinsicherheit erzeugen; daher sind geplante Gaps bewusst nicht als implementiert markiert.
- Human Review kann Skalierung und Automatisierung begrenzen.

---

## Architecture Review Checklist

- [x] Neue Dependency gerechtfertigt? Keine neue Dependency für diesen Review; Qdrant/Meilisearch bleiben Upgrade-Pfade.
- [x] Module Coupling akzeptabel? Ja im MVP; ADR-008 empfiehlt Index-Adapter gegen direkte `DiscoveryPipeline`→`WhooshIndex`-Kopplung.
- [x] Data Flow dokumentiert und sicher? Ja: Retrieval → Snapshot/Extraction → Scoring → Contradiction → Synthesis → Verification → Report.
- [x] Error Handling konsistent? Teilweise; ChromaDB/Whoosh degradieren/loggen, Evidence-/MCP-Fehlerstrategie bleibt Folgearbeit.
- [x] Scaling Bottlenecks identifiziert? Ja: GTX 1070, Whoosh-Schwellen, Human Review, Snapshot-Storage.
- [x] Security Boundaries klar? Ja: Clearnet/Onion/Offline, `socks5h`, no-live-Tor-retrieval, Human Approval.
- [x] Testing Strategy ausreichend? Für ADR ja; Umsetzung braucht Reproducibility-, Gate-, Evidence-Store- und MCP-Tool-Tests.

---

## References

- Issue #14: <https://github.com/xxammaxx/Researcher/issues/14>
- ADR-001: `design.md:42-45`
- ADR-002: `design.md:47-50`
- ADR-003: `design.md:52-56`
- ADR-004: `design.md:58-61`
- ADR-005: `design.md:63-67`
- ADR-006: `docs/adr/006-evidence-first-pipeline.md`
- ADR-007: `docs/adr/007-onion-discovery-engine.md`
- ADR-008: `docs/adr/008-onion-search-index.md`
- Blueprint Review: `deepresearch-agent-stack.md`
- C4-Kontext und Komponenten: `docs/architecture.md:8-83`
- Delta-Spezifikationen: `specs/delta-specs.md`
- Konfiguration: `.env.example`
- ChromaDB-Vektorspeicher: `vectordb/store.py:21-39`, `vectordb/store.py:79-180`
- Whoosh-Volltextindex: `darknet_search/index.py:27-36`, `darknet_search/index.py:117-166`
- Onion Discovery Engine: `onion_discovery/engine.py:42-103`, `onion_discovery/engine.py:181-218`
- Human Review Queue: `onion_discovery/human_review.py:44-158`
- Policy Gateway: `onion_discovery/policy_gateway.py:64-113`
- Projekt-Sicherheitsregeln: `researcher_research_first_rule.md:201-284`
