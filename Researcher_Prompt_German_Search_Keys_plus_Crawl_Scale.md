# Researcher — Prompt: German Search Keys + Crawl-/Index-Skalierung ohne Datenmigration

## Rolle

Du bist ein Senior Search Infrastructure Engineer, Unicode Regression Engineer, Crawl-Scale Architect und Local-First Data Safety Agent.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die deutsche Unicode-/Umlautstrategie kontrolliert in Such-/Index-nahe Pfade einzubauen und dabei gleichzeitig die früheren Erkenntnisse aus „Crawling und Skalierung in KI“ zu berücksichtigen:

- keine DDoS-artigen Live-Crawls
- deduplizierte Crawl-/Cache-Schicht
- robots.txt respektieren
- per-domain Rate Limits
- Retry/Backoff
- Crawl Frontier / Queueing
- Canonicalization
- Content Deduplication
- Cache-first statt ungehemmtes Live-Fetching
- klare Trennung zwischen Query, Crawl, Index, Report und Evaluation
- keine Datenmigration ohne explizite Freigabe
- keine Cloud-Fallbacks

---

# Validierte externe Grundlagen

Diese Implementierung soll sich an folgenden offiziellen/hochwertigen Quellen orientieren:

- Robots Exclusion Protocol: RFC 9309
- HTTP Caching: RFC 9111
- Unicode Normalization: Unicode Standard Annex #15
- Python Unicode Handling: `unicodedata.normalize()` und `str.casefold()`

Diese Quellen sollen in der Doku erwähnt werden, falls neue Dokumentation entsteht.

---

# Ausgangslage

Nach den bisherigen Issues existieren:

## Unicode / Deutsch

```python
normalize_nfc()
normalize_search_key()
ascii_fold_german()
slugify_german()
normalize_markdown_text()
```

## Deutsche Query-Fixtures

- harmlose deutsche Query-Fixtures
- Fixture-Loader
- deutsche Report-Evaluation-Tests
- optionales `make research-evaluate-german`
- `scripts/research_multi_query_eval.py --queries-file`

## Local-First Runtime

- Ollama lokal
- SearXNG lokal
- Tor optional
- Cloud-Provider blockiert
- Report-Evaluation lokal
- keine Cloud-Judges

## Crawling-/Skalierungsprinzipien aus früherem Chat

Das System darf nicht für jede Nutzerfrage unkontrolliert dieselben Webseiten erneut abrufen.

Stattdessen soll die Architektur langfristig so gedacht werden:

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

Dieses Issue implementiert NICHT die komplette Crawl-Architektur. Es bereitet nur die search-key- und index-nahe Grundlage so vor, dass spätere Crawl-/Index-Skalierung sauber darauf aufbauen kann.

---

# Oberstes Ziel

Führe deutsche Search Keys als ergänzende Normalisierungsschicht ein und dokumentiere, wie diese später in eine skalierbare Crawl-/Index-Architektur integriert werden.

Das Issue soll sicherstellen:

1. Such-/Matching-Pfade können Unicode-NFC + casefold verwenden.
2. ASCII-Fallbacks können ergänzend verglichen werden.
3. Originaltexte bleiben unverändert.
4. bestehende Indizes werden nicht migriert.
5. neue Helper werden nur dort eingebaut, wo risikoarm.
6. Tests belegen `müller` ↔ `mueller`, `straße` ↔ `strasse`, `übergröße` ↔ `uebergroesse`.
7. Crawl-/Index-Doku erklärt, warum Cache, Queueing, Robots, Rate-Limits und Dedup nötig sind.
8. Es entstehen keine unkontrollierten Live-Crawls.
9. `make quality` bleibt grün.

---

# Harte Nicht-Ziele

Dieses Issue darf NICHT:

- bestehende Indizes neu bauen oder migrieren
- vorhandene Daten überschreiben
- Originaltext durch normalisierten Text ersetzen
- einen vollwertigen Crawler bauen
- Live-Crawling ausweiten
- neue Search-Features bauen
- Suchprovider hinzufügen
- Cloud-Provider aktivieren
- SearXNG-/Ollama-/Tor-Architektur ändern
- Zugangskontrollen umgehen
- Logins/Formulare/CAPTCHAs automatisieren
- Portscans/Exploits/Bruteforce durchführen
- Darknet-Foren automatisch crawlen
- Vendor-Code im `gpt_researcher/`-Submodul ändern
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken

---

# Sicherheits- und Skalierungsprinzipien

## 1. Original bleibt Source of Truth

Für jedes Dokument, jede Query und jeden Report:

```text
original_text = unverändert
search_key = NFC + casefold
ascii_search_key = deutscher ASCII-Fallback
```

Nur Zusatzfelder, keine Ersetzung.

## 2. Kein Index-Rebuild in diesem Issue

Wenn ein Index aktuell keine Normalisierungsfelder hat:

- Helper und neue Codepfade vorbereiten
- Tests mit temporären In-Memory-Daten schreiben
- Folge-Issue für optionale Index-Migration vorschlagen

## 3. Cache-first statt Live-Fetch-first

Spätere Architekturregel:

```text
Vor jedem Fetch:
1. Cache prüfen
2. Canonical URL prüfen
3. robots.txt Policy prüfen
4. Domain-Budget prüfen
5. Rate-Limit prüfen
6. erst dann Fetch erlauben
```

Dieses Issue baut noch keinen produktiven Fetcher um, soll aber Doku und Interfaces nicht gegen diese Architektur stellen.

## 4. Per-Domain Fairness

Spätere Crawl-Schicht muss pro Domain limitieren:

- `max_requests_per_minute`
- `concurrent_requests_per_domain`
- `crawl_delay`
- `backoff_until`
- `error_budget`
- `daily_domain_budget`

## 5. Deduplizierte gemeinsame Crawl-/Cache-Schicht

Wenn mehrere Nutzer oder Agenten dieselbe Quelle brauchen:

- nicht mehrfach live crawlen
- canonical URL nutzen
- content hash nutzen
- cached extraction wiederverwenden
- TTL und Revalidation beachten

## 6. Robots Policy

Spätere Fetcher müssen `robots.txt` berücksichtigen.

Wichtig:

- `robots.txt` ist kein Zugriffsschutz.
- Trotzdem ist es eine verpflichtende Fairness-/Compliance-Schicht für Crawler.
- Policy-Entscheidungen sollen auditierbar sein.

## 7. Deterministische Tests vor Live-Runtime

Für dieses Issue:

- keine echten SearXNG-/Tor-/Ollama-Dienste in Unit-Tests
- keine echten externen Webseiten
- keine Live-Crawls
- nur Fixtures, In-Memory-Daten, Mocks

---

# Arbeitsreihenfolge

## 1. Bestehenden Zustand analysieren

Lies:

```text
text_utils/german.py
tests/fixtures/german_queries.json
tests/helpers/german_query_fixtures.py
search/
darknet_search/
onion_discovery/
mcp_tools/evidence_store.py
scripts/evaluate_research_report.py
scripts/research_multi_query_eval.py
vectordb/
crawlers/
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
docs/evaluation/german-query-fixtures.md
docs/security/
```

Führe aus:

```bash
grep -RIn "query\|search\|index\|match\|title\|slug\|filename\|document\|content" search darknet_search onion_discovery mcp_tools vectordb scripts tests crawlers | head -250

grep -RIn "lower()\|casefold\|normalize_search_key\|ascii_fold_german\|slugify_german" search darknet_search onion_discovery mcp_tools vectordb scripts tests crawlers || true

grep -RIn "requests\.get\|requests\.post\|robots\|cache\|rate\|backoff\|retry\|canonical\|dedup" search crawlers scripts mcp_tools darknet_search onion_discovery || true
```

Dokumentiere:

- wo Query-Vergleiche stattfinden
- wo Indextexte erzeugt werden
- wo Titel/Dateinamen/IDs entstehen
- wo Crawling/Fetched Content verarbeitet wird
- wo bestehende Datenpersistenz betroffen wäre
- welche Stellen risikoarm angepasst werden können
- wo Crawl-/Skalierungsregeln später greifen müssten

---

## 2. Search-Key-Utility-Schicht ergänzen

Wenn `text_utils/german.py` reicht, dort ergänzen.

Falls besser getrennt:

```text
text_utils/search_keys.py
```

Vorgeschlagene Datentypen:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class GermanSearchKeys:
    original: str
    normalized: str
    ascii_folded: str
```

Funktionen:

```python
def build_german_search_keys(text: str) -> GermanSearchKeys:
    ...

def german_search_keys_match(left: str, right: str) -> bool:
    ...

def german_query_matches_text(query: str, text: str) -> bool:
    ...
```

Regeln:

- `original` bleibt exakt erhalten
- `normalized = normalize_search_key(text)`
- `ascii_folded = ascii_fold_german(text)`
- Match ist True, wenn:
  - normalized gleich ist
  - ascii_folded gleich ist
  - normalized query in normalized text enthalten ist
  - ascii_folded query in ascii_folded text enthalten ist
- keine fuzzy search
- keine Ranking-Änderung
- keine persistente Migration

---

## 3. Crawling-/Index-Metadaten vorbereiten, aber nicht produktiv erzwingen

Erstelle nur Dokumentation oder Typentwurf, kein produktiver Crawler-Umbau.

Optionaler Dokumentationsentwurf:

```text
docs/crawling/crawl-scale-policy.md
docs/crawling/cache-frontier-architecture.md
```

Pflichtinhalt:

```markdown
# Crawl Scale Policy

## Ziel

## Warum nicht jede Query live crawlen?

## Komponenten

| Komponente | Zweck |
|---|---|
| Frontier Queue | deduplizierte Fetch-Planung |
| Robots Policy Cache | robots.txt nur kontrolliert prüfen |
| Per-Domain Rate Limiter | DDoS vermeiden |
| Fetch Cache | wiederholte Abrufe vermeiden |
| Canonicalizer | URL-Duplikate reduzieren |
| Content Hash | Inhaltsduplikate erkennen |
| Extractor | lesbaren Text erzeugen |
| Indexer | Such-/Vektorindex aktualisieren |
| Audit Log | Entscheidungen nachvollziehbar machen |

## Domain-Budgets

## Retry / Backoff

## Cache TTL / Revalidation

## Deutsche Search Keys im Index

| Feld | Zweck |
|---|---|
| original_text | Anzeige / Wahrheit |
| normalized_text | Unicode-Suche |
| ascii_folded_text | Umlaut-Fallback |

## Nicht-Ziele

- kein Brute Force
- keine Login-Automation
- keine Captcha-Umgehung
- keine Exploits
- keine Darknet-Massencrawls
```

---

## 4. Risikoarme Anschlussstellen wählen

Erlaubte sichere Anschlüsse:

### Evaluation / Fixtures

- deutsche Query-Fixtures mit Search Keys prüfen
- Evaluation kann bei Query-/Termvergleich `normalize_search_key()` nutzen

### Report Evaluation

- erwartete deutsche Begriffe in gemockten Reports normalisiert vergleichen
- Umlaute im Report sichtbar erhalten

### In-Memory Tests

- kleine temporäre Dokumentlisten
- keine echten Indizes
- keine Migration

### Crawl-Doku

- beschreiben, wie später URLs canonicalisiert, gecacht und dedupliziert werden
- noch keine Live-Fetch-Logik ändern

Vorsichtig oder vertagen:

### Whoosh / SQLite / ChromaDB

- keine bestehende Datenstruktur ändern
- keine Persistenzmigration
- nur dokumentieren, wie Search Keys später als Zusatzfelder aufgenommen werden können

---

## 5. Tests für Search-Key-Verhalten

Erstelle:

```text
tests/test_german_search_keys.py
```

Testfälle:

```python
def test_build_german_search_keys_preserves_original():
    keys = build_german_search_keys("Müller Straße")
    assert keys.original == "Müller Straße"
    assert keys.ascii_folded == "mueller strasse"

def test_mueller_matches_müller():
    assert german_search_keys_match("Müller", "mueller")

def test_strasse_matches_straße():
    assert german_search_keys_match("Straße", "strasse")

def test_uebergroesse_matches_übergröße():
    assert german_search_keys_match("Übergröße", "uebergroesse")

def test_query_matches_text_with_ascii_fallback():
    assert german_query_matches_text("fussgaengerzone", "Die Fußgängerzone ist autofrei.")
```

Zusätzliche Fälle:

- `Ärger` ↔ `aerger`
- `Öl` ↔ `oel`
- `Übergröße` ↔ `uebergroesse`
- `ẞ` ↔ `ss`
- kombinierte Unicode-Zeichen
- Mehrfach-Leerzeichen
- Satzzeichen

---

## 6. Tests mit deutschen Fixtures verbinden

Erweitere:

```text
tests/test_german_query_fixtures.py
```

Testfälle:

- Jede Fixture bekommt Search Keys.
- `ascii_folded`, falls im Fixture angegeben, entspricht `ascii_fold_german(query)`.
- Fixture-ID ist safe.
- `expected_terms` matchen Report-/Textbeispiele mit `german_query_matches_text()`.
- Kein Fixture triggert verbotene Crawl-/Security-Begriffe.

---

## 7. In-Memory Search-Regression

Erstelle:

```text
tests/test_german_in_memory_search.py
```

Beispiel:

```python
DOCUMENTS = [
    {"id": "1", "title": "Müller Straße", "body": "Eine Straße als Unicode-Beispiel."},
    {"id": "2", "title": "Fußgängerzone", "body": "Ein Bereich für Fußgänger."},
    {"id": "3", "title": "Übergröße", "body": "Ein Wortbeispiel mit Umlaut."},
]
```

Tests:

- Query `mueller strasse` findet `Müller Straße`
- Query `fussgaenger` findet `Fußgängerzone`
- Query `uebergroesse` findet `Übergröße`
- Query `straße` findet `strasse`-Fallback
- Originaltitel bleibt mit Umlauten erhalten
- keine echten Indizes werden verändert

---

## 8. Crawl-/Skalierungs-Regression als Dokumentations- und Policy-Test

Optional, aber empfohlen:

Erstelle:

```text
tests/test_crawl_scale_policy_docs.py
```

Testet nur Doku/Policy-Präsenz, nicht Live-Crawling:

- `docs/crawling/crawl-scale-policy.md` existiert
- enthält `robots.txt`
- enthält `per-domain rate limit`
- enthält `backoff`
- enthält `cache`
- enthält `canonical`
- enthält `dedup`
- enthält `original_text`, `normalized_text`, `ascii_folded_text`
- enthält Verbote für brute force, login automation, captcha bypass

Zweck:

- Die Skalierungsprinzipien aus dem Crawling-Chat bleiben im Repo für KI-Agenten sichtbar.
- Keine Runtime-Änderung.

---

## 9. Dokumentation aktualisieren

Aktualisiere:

```text
docs/text/umlaut-search-and-slug-policy.md
docs/text/unicode-german-strategy.md
docs/evaluation/german-query-fixtures.md
```

Neu empfohlen:

```text
docs/text/german-search-keys.md
docs/crawling/crawl-scale-policy.md
docs/crawling/cache-frontier-architecture.md
```

Pflichtinhalt für `docs/text/german-search-keys.md`:

```markdown
# German Search Keys

## Ziel

## Original vs Normalized vs ASCII-Folded

| Feld | Zweck | Beispiel |
|---|---|---|
| original | Anzeige / Source of Truth | Müller Straße |
| normalized | Unicode-Suche | müller strasse |
| ascii_folded | ASCII-Fallback | mueller strasse |

## Matching-Regeln

## Was dieses Issue nicht tut

- keine Indexmigration
- kein Rebuild
- kein Ranking
- keine Fuzzy Search

## Folge-Issue für echte Indizes
```

Pflichtinhalt für `docs/crawling/crawl-scale-policy.md`:

```markdown
# Crawl Scale Policy

## Ziel

## Standards / Quellen

- RFC 9309 Robots Exclusion Protocol
- RFC 9111 HTTP Caching
- Unicode UAX #15 Normalization
- Python unicodedata / casefold

## Architektur

## Cache-first Fetching

## Robots Policy

## Per-Domain Rate Limits

## Retry / Backoff

## Canonicalization

## Deduplication

## Audit Logging

## German Search Keys in Indexes

## Safety Boundaries
```

---

# Validierung

Nach Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local

python3 -m pytest tests/ -q -k "german or umlaut or unicode or search_key or crawl_scale"
```

Optional, wenn Runtime verfügbar:

```bash
make research-evaluate-german
```

Nicht ausführen:

- keine neuen Live-Crawls
- keine externen Zielseiten
- keine Darknet-Crawls

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- German Search Key Helper existieren oder bestehende Helper entsprechend erweitert sind
- Originaltext bleibt erhalten
- Unicode-normalisierte Search Keys werden erzeugt
- ASCII-Fallback Search Keys werden erzeugt
- `müller` / `mueller` Match ist getestet
- `straße` / `strasse` Match ist getestet
- `übergröße` / `uebergroesse` Match ist getestet
- deutsche Fixtures verwenden Search Keys
- In-Memory-Search-Regression existiert
- Crawl-/Skalierungs-Policy dokumentiert ist
- Policy enthält Cache, Queue, Robots, Rate-Limits, Backoff, Canonicalization, Dedup
- keine Datenmigration durchgeführt wurde
- keine bestehenden Indizes verändert wurden
- keine Live-Crawls eingeführt wurden
- Doku wurde aktualisiert
- `make quality` bleibt grün
- `make coverage` bleibt grün
- keine Cloud-Fallbacks
- keine neuen Research-Features
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- Search-Key-Helper
- Tests für deutsche Matching-Fälle
- Crawl-Scale-Policy-Doku
- keine Migration
- Quality Gates grün

Gut:

- deutsche Fixtures nutzen Search Keys
- In-Memory-Search-Regression vorhanden
- Policy-Test sichert Crawling-Skalierungsregeln

Sehr gut:

- Folge-Issue für echte Index-Anbindung kann präzise aus der Doku abgeleitet werden
- KI-Agenten finden klare Grenzen, bevor sie Crawler-Code ändern

---

# Abschlussbericht-Vorlage

```markdown
# Researcher German Search Keys + Crawl-Scale Policy Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Search-Key-Helper erstellt/erweitert | |
| Originaltext bleibt erhalten | |
| Unicode Search Key erzeugt | |
| ASCII-Fallback erzeugt | |
| Müller/Mueller getestet | |
| Straße/Strasse getestet | |
| Übergröße/Uebergroesse getestet | |
| Fixtures angebunden | |
| In-Memory-Search getestet | |
| Crawl-Scale-Policy erstellt | |
| Cache/Queue/Robots/Rate-Limits dokumentiert | |
| Keine Datenmigration | |
| Keine Indexänderung | |
| Keine Live-Crawls | |
| Doku aktualisiert | |
| `make quality` grün | |
| `make coverage` grün | |
| Keine Cloud-Fallbacks | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Neue/Geänderte Dateien

## Tests

| Testdatei | Anzahl | Ergebnis |
|---|---:|---|

## Validierte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Crawling-/Skalierungsentscheidungen

| Bereich | Entscheidung |
|---|---|
| robots.txt | |
| Cache | |
| Rate Limit | |
| Backoff | |
| Canonicalization | |
| Deduplication | |
| Queueing | |

## Bewusst nicht umgesetzt

## Risiken

## Nächste empfohlene Issues
```

---

# Empfohlene Folge-Issues

1. `Implement crawl frontier queue with robots/rate-limit/cache interfaces only`
2. `Apply German search keys to Whoosh/SQLite/Chroma indexes with opt-in rebuild`
3. `Model compatibility check command for local Ollama models`
4. `Docs-aware prompt context for local AI agents`
5. `Release tag after CI/Playwright cleanup`
