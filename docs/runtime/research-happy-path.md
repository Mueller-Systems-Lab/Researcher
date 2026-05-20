# Minimal Local Research Happy Path

**Datum:** 2026-05-19  
**Scope:** Minimale lokale Research-Pipeline (Query → SearXNG → Ollama → Report)  

---

## Ziel

Beweist, dass die komplette lokale Research-Pipeline funktioniert:
1. SearXNG liefert Suchergebnisse
2. Ollama erzeugt eine Zusammenfassung
3. Ein Markdown-Report wird geschrieben
4. Keine Cloud-Provider werden verwendet

Seit Issue #75 nutzt der Happy-Path dafür die zentrale Modellkonfiguration aus `config/ollama_models.py`.

---

## Was dieser Test beweist

- ✅ SearXNG liefert relevante Suchergebnisse
- ✅ Ollama kann Quellen zusammenfassen
- ✅ Report-Datei wird korrekt erzeugt
- ✅ Cloud-Blocker funktioniert
- ✅ Query-Safety-Guard blockiert riskante Queries
- ✅ Modellrollen/Fallbacks werden zentral über `config/ollama_models.py` aufgelöst

## Was dieser Test nicht beweist

- ❌ Vollständige GPT-Researcher-Pipeline
- ❌ Multi-Source Deep Research
- ❌ Darknet/Onion-Crawling
- ❌ Produktive Research-Qualität

---

## Voraussetzungen

```bash
# Dienste müssen laufen (oder --strict für Pflicht)
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
```

---

## Ausführen

```bash
# Standard (Dienste optional, graceful degradation)
make research-happy-path

# Mit eigener Query
python3 scripts/research_happy_path.py --query "What is SearXNG?"

# Strict (alle Dienste Pflicht)
make research-happy-path-strict
```

---

## Erwartete Ausgabe

```
🔬 Researcher Happy-Path
   Query:  What is a search engine?
   Output: reports/research

✅ Cloud: Keine Cloud-Provider aktiv
✅ Query: harmlos

🔎 Searching...
   SearXNG: 5 results

🦙 Summarizing...
   Ollama: 234 chars summary

📄 Writing report...
   Report: reports/research/research_20260519_091300.md (1878 bytes)

──────────────────────────────────────────────────
✅ Research Happy-Path erfolgreich!
   Report: reports/research/research_20260519_091300.md
```

---

## Report-Pfad

```
reports/research/research_<YYYYMMDD_HHMMSS>.md
```

---

## Sicherheitsgrenzen

### Query-Safety-Guard

Blockierte Begriffe: `exploit`, `cve`, `vulnerability`, `credential`, `password dump`, `darknet`, `onion forum`, `malware`, `ransomware`, `target.com`, `person:`, `site:`

### Cloud-Blocker

Vor Ausführung: Prüfung auf `LLM_PROVIDER`, `RETRIEVER`, `ALLOW_CLOUD`. Bei Cloud-Aktivierung → Abbruch.

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| SearXNG Timeout | `SEARXNG_TIMEOUT_SECONDS=30` setzen |
| Ollama 404 | Modellname prüfen: `OLLAMA_LLM_MODEL` env |
| Report leer | SearXNG-Ergebnisse prüfen |
| Query geblockt | Harmlose generische Query verwenden |

---

## Nächste Schritte

1. Vollständige GPT-Researcher-Pipeline mit lokalen Diensten
2. Deep Research mit mehreren Quellen
3. Report-Quality-Evaluation
