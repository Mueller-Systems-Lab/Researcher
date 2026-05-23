# Crawl Scale Policy

## Ziel

Dieses Dokument definiert die Sicherheits- und Skalierungsgrenzen für spätere Crawl-/Index-Arbeiten im Researcher-Projekt.

## Standards / Quellen

- RFC 9309 — Robots Exclusion Protocol
- RFC 9111 — HTTP Caching
- Unicode UAX #15 — Unicode Normalization
- Python `unicodedata.normalize()` und `str.casefold()`

## Architekturprinzip

```text
User Query
  -> Query Normalization
  -> Cache / Index Lookup
  -> Search Provider / SearXNG
  -> Crawl Frontier Queue
  -> Robots Policy Check
  -> Per-Domain Rate Limiter
  -> Fetcher with Timeout + Backoff
  -> Canonicalizer
  -> Content Extractor
  -> Deduplicator
  -> Indexer
  -> Report Generator
  -> Evaluation
```

## Cache-first Fetching

Vor jedem Fetch:

1. Cache prüfen
2. Canonical URL prüfen
3. robots.txt Policy prüfen
4. Domain-Budget prüfen
5. Rate-Limit prüfen
6. erst dann Fetch erlauben

## Robots Policy

Crawler müssen `robots.txt` respektieren.

`robots.txt` ist kein Zugriffsschutz, aber eine verbindliche Fairness- und Compliance-Schicht für freundliche Crawler.

Der Robots-Policy-Cache speichert bereits geprüfte `robots.txt`-Entscheidungen, um wiederholte Netzwerkabrufe zu vermeiden.

## Per-Domain Rate Limits

Jede Domain erhält eigene Limits:

| Limit-Feld                  | Beschreibung                                    |
| --------------------------- | ----------------------------------------------- |
| `max_requests_per_minute`   | Maximale HTTP-Requests pro Minute               |
| `concurrent_requests_per_domain` | Gleichzeitige Verbindungen zur Domain      |
| `crawl_delay`               | Mindestabstand zwischen zwei Requests (Sekunden) |
| `backoff_until`             | Zeitstempel bis zu dem keine Requests erlaubt sind |
| `error_budget`              | Maximale Fehlerrate bevor Domain gesperrt wird  |
| `daily_domain_budget`       | Maximale Requests pro Domain und Tag            |

## Retry / Backoff

Fehlerhafte oder limitierte Domains dürfen nicht aggressiv erneut abgefragt werden.

- Exponentielles Backoff mit Jitter
- Maximal 3 Retries pro URL
- Nach Erreichen des Error-Budgets: Domain-Sperre für 1 Stunde
- Keine Retries auf 4xx-Statuscodes (außer 429 Too Many Requests)

## Canonicalization

URLs müssen normalisiert werden, bevor sie in Cache, Frontier oder Dedup gelangen:

- Schema lowercase (`HTTP` → `http`)
- Host lowercase
- Port entfernen wenn Default (80, 443)
- Pfad normalisieren (`/./` und `/../` auflösen)
- Query-Parameter sortieren
- Fragment (`#`) entfernen
- Trailing Slash konsistent handhaben

## Deduplication

Inhalte werden über zwei Verfahren dedupliziert:

1. **Canonical URL**: Gleiche canonical URL → nur einmal fetchen
2. **Content Hash**: SHA-256 des extrahierten Textinhalts → Duplikate erkennen

## German Search Keys in Indexes

| Feld                | Zweck                                 |
| ------------------- | ------------------------------------- |
| `original_text`     | Anzeige / Source of Truth             |
| `normalized_text`   | Unicode-Suche (NFC + casefold)        |
| `ascii_folded_text` | Umlaut-Fallback (ä→ae, etc.)          |

## Safety Boundaries

Nicht erlaubt:

- Brute Force
- Login-Automation
- CAPTCHA-Umgehung
- Exploit-Ausführung
- Darknet-Massencrawls
- ungehemmte Live-Crawls ohne Frontier und Rate-Limiting

## Audit Logging

Jede Crawl-Entscheidung muss nachvollziehbar sein:

- Fetch-Entscheidungen (erlaubt/blockiert mit Begründung)
- Rate-Limit-Ereignisse
- robots.txt-Änderungen
- Domain-Sperren
- Error-Budget-Erschöpfung
