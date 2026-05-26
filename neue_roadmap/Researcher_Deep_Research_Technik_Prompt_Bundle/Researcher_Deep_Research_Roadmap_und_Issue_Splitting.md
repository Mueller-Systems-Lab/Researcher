# Researcher — Deep-Research-Technik lokal-first in das Projekt integrieren

## Rolle

Du bist ein Senior Research Systems Architect, Local-First AI Engineer, Agent-Orchestration Engineer und GitHub Source-of-Truth Agent.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, eine Cloud-Deep-Research-API nachzubauen.

Dein Ziel ist, die im Dokument „Deep Research Funktion: Funktionsweise und Details“ beschriebenen Architekturprinzipien kontrolliert, lokal-first und issue-basiert in unser bestehendes Researcher-Projekt zu überführen.

---

# Validierter Kontext

Das gelesene Dokument beschreibt Deep-Research-Systeme als mehrstufige, autonome Forschungsagenten, die komplexe Fragen in Forschungspläne zerlegen, iterative Such-/Analysezyklen ausführen und zitierte Berichte erzeugen.

Die Kerntechnik besteht aus:

- Collaborative Planning / Planfreigabe
- Planner Agent
- Master/Orchestrator Agent
- Researcher Agent
- Searcher Agent
- Report Writer Agent
- DAG-basierter Aufgabenplan
- iterativer Feedback-Loop
- Cross-Encoder-Reranking
- MMR-Diversifizierung
- strukturkonforme Segmentierung
- Quellenmetadaten
- Inline-Zitate
- Web-Governance
- Caching
- Robots-Policy
- Prompt-Injection-Schutz
- Evaluation und Qualitätsmetriken

Unser bestehendes Projekt hat bereits:

- GPT-Researcher-Fork/Submodul
- lokale Websuche via SearXNG
- lokale LLM-Runtime via llama-server / Ollama
- unzensiertes Qwen3.5-kompatibles Modellziel
- Report-Evaluation
- Source Coverage / Traceability Scores
- Local-First-Blocker
- German Search Keys
- Crawl-Scale-Policy
- GPU-Dashboard
- GPT-Researcher UI
- GitHub-Issue-basierte Entwicklung

---

# Architekturentscheidung

Wir bauen kein neues monolithisches „Deep Research“-Feature.

Wir bauen eine lokale Deep-Research-Orchestrierungsschicht über dem bestehenden Projekt:

```text
User Query
  -> Collaborative Planner
  -> Research Plan DAG
  -> Human Approval
  -> Master Orchestrator
  -> Researcher Workers
  -> Searcher Pipeline
  -> Evidence Store
  -> Report Writer
  -> Report Evaluation
  -> UI / Markdown Report
```

---

# Nicht-Ziele

Diese Initiative darf NICHT:

- Cloud-APIs erforderlich machen
- OpenAI/Tavily/Anthropic aktivieren
- externe Deep-Research-APIs verwenden
- robots.txt umgehen
- Captchas umgehen
- Login-/Paywall-Automation bauen
- aggressive Crawls ausführen
- Darknet-/Security-Recherche als Default aktivieren
- unzensiertes Modell für gefährliche Testprompts missbrauchen
- bestehende Quality Gates lockern
- Release-Tag erstellen
- GitHub Release veröffentlichen

---

# Vorgeschlagene Issue-Kette

## Issue DR-01 — Collaborative Planner + Research Plan DAG

Ziel:
Aus einer Nutzerfrage einen editierbaren Forschungsplan als DAG erzeugen.

Scope:

- `research_planner/`
- `ResearchPlan`
- `ResearchNode`
- Abhängigkeiten
- Status: draft / approved / running / completed / failed
- JSON/Markdown-Export
- Human-in-the-loop approval
- keine Websuche in diesem Issue

Entscheidung:
Ohne bestätigten Plan wird keine tiefe Recherche gestartet.

---

## Issue DR-02 — Master Orchestrator + Persistent State

Ziel:
Einen genehmigten DAG topologisch traversieren und Worker-Aufgaben koordinieren.

Scope:

- `research_orchestrator/`
- State Store
- Task lifecycle
- resume/retry
- event log
- dependency resolution
- sequential first, optional parallel later

Entscheidung:
Durable Execution ist wichtiger als Geschwindigkeit.

---

## Issue DR-03 — Researcher Worker + Query Decomposition

Ziel:
Jeden DAG-Knoten in konkrete Suchqueries zerlegen.

Scope:

- Fragezerlegung
- Keyword-Vertiefung
- Gap-driven follow-up queries
- deutsch/englisch Query-Varianten
- keine Inhaltsfilterung (unzensiertes Research)
- keine direkten Crawls

Entscheidung:
Worker erzeugen Suchaufträge, keine Berichte.

---

## Issue DR-04 — Searcher Pipeline: SearXNG, Fetch Cache, Robots, Reranking, MMR

Ziel:
Suchergebnisse fair, dedupliziert, gecacht und evidenzfähig sammeln.

Scope:

- SearXNG
- URL canonicalization
- robots.txt policy
- HTTP cache
- domain rate limiting
- fetch queue/frontier
- content extraction
- segment metadata
- local reranking
- MMR
- prompt-injection isolation

Entscheidung:
Robots/Cache/Rate-Limits sind Pflicht, kein optionales Nice-to-have.

---

## Issue DR-05 — Evidence Store + Citation Model

Ziel:
Alle Segmente mit Quelle, Zeitstempel, Hash und Zitier-ID persistieren.

Scope:

- `evidence_store`
- source metadata
- content hash
- quote-safe snippets
- source IDs `[S1]`, `[S2]`
- segment provenance
- duplicate detection

Entscheidung:
Kein Bericht ohne belegbare Evidence.

---

## Issue DR-06 — Report Writer + Evaluation Loop

Ziel:
Aus DAG-Ergebnissen und Evidence einen zitierbaren Bericht erzeugen.

Scope:

- Report sections per DAG node
- inline citations
- limitations
- uncertainty markers
- source coverage score
- traceability score
- hallucination risk heuristic
- local-first score
- revision loop when quality too low

Entscheidung:
Bericht gilt nur als fertig, wenn Evaluation-Schwellen erfüllt sind.

---

## Issue DR-07 — UI-Integration: Plan → Approve → Run → Report

Ziel:
GPT-Researcher UI oder lokales Dashboard so verdrahten, dass der Nutzer den Deep-Research-Flow bedienen kann.

Scope:

- Plan anzeigen
- Plan editieren/freigeben
- Research starten
- Fortschritt anzeigen
- Reports anzeigen
- Evaluation anzeigen
- Logs/Events anzeigen

Entscheidung:
CLI zuerst erlaubt, aber UI muss die Hauptzustände sichtbar machen.

---

## Issue DR-08 — Local Model Runtime Guard

Ziel:
Sicherstellen, dass das unzensierte Qwen3.5-kompatible Modell stabil im Deep-Research-Loop läuft.

Scope:

- llama-server runtime
- GTX 1070 offload profile
- cold/warm timings
- timeout budgets
- no 7B fallback
- no cloud fallback
- model garbling detector
- report metadata includes model/runtime

Entscheidung:
Deep Research darf nicht starten, wenn das Modell nur „existiert“, aber nicht generiert.

---

# Reihenfolge

1. DR-01 Planner DAG
2. DR-02 Orchestrator State
3. DR-03 Researcher Worker
4. DR-05 Evidence Store
5. DR-04 Searcher Pipeline
6. DR-06 Report Writer/Eval
7. DR-08 Runtime Guard
8. DR-07 UI Integration

Begründung:
Plan und State müssen vor Crawling stehen. Evidence muss vor Report stehen. Runtime Guard muss vor echter UI-Nutzung stabil sein.

---

# Globales Definition of Done

Die Deep-Research-Technik gilt erst als integriert, wenn:

- Nutzerfrage in Plan-DAG überführt wird
- Plan vor Ausführung freigegeben werden kann
- DAG-Knoten einzeln nachvollziehbar laufen
- Suchquellen gecacht und fair abgerufen werden
- Evidence Store alle Quellen belegt
- Report Inline-Zitate enthält
- Evaluation Scores erzeugt werden
- Local-First garantiert ist
- keine Cloud aktiv ist
- keine robots/captcha/paywall Umgehung existiert
- UI oder CLI den vollständigen Flow bedienen kann
- alle Tests grün sind
