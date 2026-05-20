# Cache Frontier Architecture

## Ziel

Spätere Crawl-Arbeiten dürfen nicht direkt aus User Queries live crawlen, sondern müssen über Cache, Queue, Robots Policy und Rate Limiter laufen.

## Komponenten

| Komponente           | Zweck                                          |
| -------------------- | ---------------------------------------------- |
| Frontier Queue       | Deduplizierte Fetch-Planung                    |
| Robots Policy Cache  | robots.txt-Entscheidungen cachen               |
| Fetch Cache          | Unnötige Re-fetches vermeiden                  |
| Canonicalizer        | URL-Duplikate reduzieren                       |
| Content Hash         | Inhaltsduplikate erkennen                      |
| Domain Budget        | Fairness und Lastschutz                        |
| Audit Log            | Entscheidungen nachvollziehbar machen           |

## Datenfluss

```text
                     ┌──────────────────┐
                     │   User Query     │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │ Query Normalizer │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │  Index Lookup    │
                     │  (Cache-first)   │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │    Cache Hit?    │
                     └───┬──────────┬───┘
                     Ja  │          │ Nein
                         │          │
                 ┌───────▼──┐  ┌────▼──────────┐
                 │  Return  │  │ Frontier Queue │
                 │  Cached  │  └────┬───────────┘
                 └──────────┘       │
                            ┌───────▼──────────┐
                            │ Canonicalizer    │
                            └───────┬──────────┘
                                    │
                            ┌───────▼──────────┐
                            │ Dedup Check      │
                            │ (URL + Hash)     │
                            └───────┬──────────┘
                                    │
                            ┌───────▼──────────┐
                            │ Robots Policy    │
                            │ + Rate Limiter   │
                            └───────┬──────────┘
                                    │
                            ┌───────▼──────────┐
                            │ Fetcher          │
                            │ (Timeout+Backoff)│
                            └───────┬──────────┘
                                    │
                            ┌───────▼──────────┐
                            │ Content Hash     │
                            │ + Indexer        │
                            └──────────────────┘
```

## Frontier Queue

- Persistente Warteschlange (lokale SQLite oder Datei-basiert)
- Dedupliziert per Canonical URL vor Einfügung
- Priorisiert nach Domain-Budget und Crawl-Delay
- Maximale Queue-Größe konfigurierbar

## Robots Policy Cache

- Cached `robots.txt` pro Domain
- TTL: 24 Stunden (konfigurierbar)
- Bei 404/kein robots.txt: Allow-All-Policy cachen
- Redis/Pickle-basierter lokaler Cache

## Fetch Cache

- URL → Response-Cache mit TTL
- HTTP-Cache-Header respektieren (ETag, Last-Modified, Cache-Control)
- Conditional Requests (If-None-Match, If-Modified-Since) wenn verfügbar
- Separate Caches für: HTML-Rohdaten, extrahierte Texte, Metadaten

## Domain Budget Manager

- Pro Domain: tägliches Request-Budget
- Pro Domain: konkurrente Requests begrenzen
- Error-Budget: maximale Fehler pro Stunde
- Bei Budget-Erschöpfung: Queue pausiert für diese Domain

## Audit Log

- Jede Fetch-Entscheidung loggen (Timestamp, URL, Entscheidung, Begründung)
- Rate-Limit-Ereignisse loggen
- Domain-Sperren dokumentieren
- Log-Format: JSON Lines, rotationsbasiert
