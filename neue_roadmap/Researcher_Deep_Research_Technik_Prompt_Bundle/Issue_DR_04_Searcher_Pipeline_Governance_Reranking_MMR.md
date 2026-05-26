# Issue DR-04 — Searcher Pipeline: Cache, Robots, Reranking, MMR

## Ziel

Implementiere eine lokale Searcher Pipeline, die Suchergebnisse aus SearXNG fair, gecacht, dedupliziert, segmentiert und evidenzfähig verarbeitet.

---

# Kontext

Deep-Research-Systeme sammeln nicht einfach beliebig Webseiten. Sie brauchen Query-Ausführung, Reranking, strukturierte Segmentierung, MMR-Diversifizierung, Gap Evaluation und Web-Governance.

---

# Betroffene Module

Neu/Erweitert:

```text
searcher_pipeline/
  __init__.py
  searxng_client.py
  url_canonicalizer.py
  robots_policy.py
  fetch_cache.py
  rate_limiter.py
  content_extractor.py
  segmenter.py
  reranker.py
  mmr.py
  prompt_injection_filter.py
tests/test_searcher_pipeline.py
docs/deep-research/searcher-pipeline.md
```

---

# Sicherheitsregeln

Die Pipeline MUSS:

- robots.txt respektieren
- Cache-first arbeiten
- Domain Rate Limits erzwingen
- Timeouts setzen
- Redirects begrenzen
- Prompt-Injection-Inhalte isolieren
- keine Captchas umgehen
- keine Login-/Paywall-Automation ausführen
- keine aggressive Crawl-Parallelität starten

---

# Technischer Flow

```text
SearchQuery
  -> SearXNG JSON
  -> URL Canonicalization
  -> Robots Policy
  -> Fetch Cache
  -> Rate Limit
  -> HTTP Fetch
  -> Content Extraction
  -> Structural Segmentation
  -> Reranking
  -> MMR
  -> Evidence Candidates
```

---

# Robots Policy

- `/robots.txt` pro Domain prüfen
- Ergebnis cachen
- 5xx/unreachable = fail closed
- 4xx/unavailable = gemäß Policy dokumentiert entscheiden
- max-age beachten
- robots-Datei als untrusted content behandeln

---

# HTTP Cache

- Cache key: method + normalized URL
- nur GET by default
- Cache-Control respektieren
- no-store nicht speichern
- Authorization niemals in shared cache speichern
- Content Hash speichern

---

# Reranking

Zunächst simpel:

- lexical score
- title/query overlap
- domain diversity
- source freshness

Cross-Encoder optional als Folge-Issue.

---

# MMR

Ziel:

- redundante Segmente entfernen
- Quellendiversität erhöhen
- nicht 10 fast identische Snippets in Evidence Store übernehmen

---

# Tests

- URL canonicalization stabil
- robots allow/disallow funktioniert
- robots 5xx fail-closed
- cache hit vermeidet Fetch
- rate limit blockiert zu schnelle Wiederholung
- no-store wird nicht gecacht
- content extractor erzeugt Text
- segmenter erhält Metadaten
- MMR reduziert Duplikate
- prompt injection wird markiert, nicht ausgeführt

---

# Akzeptanzkriterien

Given eine Suchquery  
When SearXNG Ergebnisse liefert  
Then entstehen Evidence Candidates mit Quelle, Zeitstempel und Segmenttext.

Given robots disallow  
When Fetch geplant wird  
Then wird die URL nicht abgerufen.

Given gleiche URL mehrfach  
When Pipeline läuft  
Then wird Cache genutzt.

Given redundante Segmente  
When MMR läuft  
Then werden diversere Segmente bevorzugt.

---

# Validierung

```bash
python3 -m pytest tests/test_searcher_pipeline.py -q
make quality
make coverage
```

---

# Nicht-Ziele

- kein CAPTCHA-Bypass
- keine Paywall-Umgehung
- keine Darknet-Default-Crawls
- kein Cross-Encoder-Zwang
- keine Cloud
