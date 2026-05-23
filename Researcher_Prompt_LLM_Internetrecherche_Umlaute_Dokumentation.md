# Researcher — Prompt: LLM-Modelldokumentation und deutsche Umlaut-/Unicode-Strategie recherchieren

## Rolle

Du bist ein Senior Local-LLM Research Engineer, Documentation Architect und Unicode/Text-Normalization Specialist.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, alle aktuell im Projekt verwendeten lokalen LLM-/Embedding-Modelle im Internet aus offiziellen und belastbaren Quellen zu recherchieren, die Ergebnisse als KI-lesbare Projektdokumentation abzulegen und zusätzlich eine robuste Strategie für deutsche Umlaute, Unicode-Normalisierung und Such-/Indexierungsverhalten zu erarbeiten.

---

# Ausgangslage

Das Projekt `Researcher` ist ein lokales Research-System mit Local-First-Ansatz.

Aktuell relevante Modell-/Runtime-Komponenten aus dem Projektkontext:

- Ollama als lokale LLM-Runtime
- lokales Chat-/Summary-Modell über `OLLAMA_CHAT_MODEL`
- lokales Embedding-Modell über `OLLAMA_EMBEDDING_MODEL`
- dokumentiertes Embedding-Modell: `nomic-embed-text:latest`
- dokumentiertes Chat-/Summary-Modell: `qwen3.5-uncensored-no-thinking:latest`
- historischer/falscher Default: `qwen3.5-9b-uncensored-hauhaucs-aggressive`
- SearXNG als lokale Websuche
- Tor optional
- Cloud-Provider sollen im Standardmodus blockiert bleiben

Das Projekt nutzt inzwischen:

```bash
make runtime-smoke
make research-happy-path
make research-evaluate
make research-evaluate-multi
make quality
```

Die Modellinformationen sollen für künftige KI-Agenten und Entwickler im Repository dokumentiert werden.

---

# Oberstes Ziel

Erstelle eine aktuelle, quellenbasierte Dokumentation zu den im Projekt verwendeten lokalen Modellen und eine belastbare deutsche Umlaut-/Unicode-Strategie.

Die Dokumentation soll beantworten:

1. Welche LLM-/Embedding-Modelle verwendet das Projekt aktuell?
2. Welche offiziellen oder belastbaren Informationen gibt es zu diesen Modellen?
3. Welche Modellrollen gibt es im Projekt?
4. Welche Modelle sind für Chat/Summary geeignet?
5. Welche Modelle sind nur für Embeddings geeignet?
6. Welche Hardware-/VRAM-Anforderungen sind realistisch?
7. Welche Kontextlängen, Sprachen, Stärken und Grenzen sind bekannt?
8. Welche Lizenz-/Nutzungsbedingungen sind dokumentiert?
9. Wie sollen deutsche Umlaute behandelt werden?
10. Wie sollen Unicode-Normalisierung, Suche, Indexierung, Slugs, Dateinamen und Reports mit Deutsch umgehen?
11. Welche Tests sollten die Strategie absichern?

---

# Wichtig: Arbeitsweise

Du MUSST aktuelle Internetrecherche durchführen.

Verwende bevorzugt:

1. offizielle Modellkarten
2. Ollama Library Seiten
3. Hugging Face Model Cards
4. Hersteller-/Maintainer-Dokumentation
5. GitHub-Repositories der Modelle/Tokenizer
6. offizielle Unicode-Dokumentation
7. Python-Dokumentation zu `unicodedata`
8. Python-Dokumentation zu `str.casefold()`
9. SQLite/Whoosh/ChromaDB-Dokumentation, falls relevant
10. seriöse technische Blogposts nur ergänzend

Nicht ausreichend:

- bloße Vermutungen
- Reddit-Kommentare ohne Gegenprüfung
- veraltete Modelllisten
- nicht belegte Benchmark-Behauptungen

Wenn Quellen widersprechen:

- Widerspruch dokumentieren
- keine falsche Eindeutigkeit behaupten
- konservative Empfehlung ableiten

---

# Rechercheteil A — Modellinventar im Repository

## 1. Repository nach Modellnamen durchsuchen

Suche im Repo nach:

```bash
grep -RIn "OLLAMA_CHAT_MODEL\|OLLAMA_EMBEDDING_MODEL\|OLLAMA_BASE_URL\|nomic-embed-text\|qwen\|ollama\|llama.cpp\|embedding\|chat model\|summary model" .
```

Zusätzlich prüfen:

```text
.env.example
README.md
docs/runtime/
scripts/runtime_smoke.py
scripts/research_happy_path.py
config/
Makefile
```

Erstelle eine Tabelle:

```markdown
| Modell / Variable | Rolle | Fundstelle | Aktueller Default | Bemerkung |
|---|---|---|---|---|
| OLLAMA_CHAT_MODEL | Chat/Summary | | | |
| OLLAMA_EMBEDDING_MODEL | Embeddings | | | |
| nomic-embed-text:latest | Embedding | | | |
| qwen3.5-uncensored-no-thinking:latest | Chat/Summary | | | |
```

---

# Rechercheteil B — Internetrecherche zu verwendeten Modellen

## 2. Recherchiere `nomic-embed-text`

Recherchiere:

- offizielle Ollama-Seite
- Nomic/Hugging Face Model Card
- Modellzweck
- Embedding-Dimensionen
- Kontext-/Token-Limit
- unterstützte Sprachen, insbesondere Deutsch
- Lizenz
- typische Nutzung mit Ollama
- Grenzen
- ob das Modell für Textgenerierung ungeeignet ist

Zu dokumentieren:

```markdown
## nomic-embed-text

### Rolle im Projekt

### Offizielle Quellen

### Technische Eckdaten

| Feld | Wert | Quelle |
|---|---|---|
| Modelltyp | Embedding | |
| Dimensionen | | |
| Kontextlänge | | |
| Spracheignung Deutsch | | |
| Lizenz | | |
| Ollama Name | | |

### Empfehlung für Researcher

### Nicht verwenden für
```

---

## 3. Recherchiere `qwen3.5-uncensored-no-thinking` / Qwen-Varianten

Wichtig:

Der exakte Name `qwen3.5-uncensored-no-thinking:latest` kann ein Community-, Fork- oder lokaler Modelfile-Name sein. Deshalb:

1. Prüfe, ob dieser exakte Name öffentlich auffindbar ist.
2. Wenn nicht, identifiziere die wahrscheinlich zugrunde liegende Qwen-Version.
3. Dokumentiere klar:
   - exakt belegte Informationen
   - abgeleitete Vermutungen
   - lokale Naming-Konvention
   - Risiken bei unklarer Herkunft

Recherchiere:

- Qwen offizielle Dokumentation
- Qwen Model Cards
- Ollama Library Qwen-Varianten
- Kontextlänge
- Sprachunterstützung Deutsch
- Reasoning-/No-Thinking-Modi, falls dokumentiert
- Lizenz
- Hardware-/Quantisierungshinweise
- Nutzung in Ollama
- Eignung für kurze Summaries
- Risiken unzensierter Modelle
- Prompting-Empfehlungen für faktengebundene Reports

Zu dokumentieren:

```markdown
## Qwen Chat/Summary Model

### Exakter lokaler Modellname

### Öffentlich belegbarer Ursprung

### Unsicherheiten

### Technische Eckdaten

| Feld | Wert | Quelle |
|---|---|---|
| Modellfamilie | Qwen | |
| Modellgröße | | |
| Kontextlänge | | |
| Spracheignung Deutsch | | |
| Lizenz | | |
| Ollama-Verfügbarkeit | | |

### Empfehlung für Researcher

### Risiken

### Prompting-Regeln
```

---

## 4. Recherchiere Ollama Runtime

Recherchiere:

- Ollama API `/api/tags`
- Ollama Generate/Chat API
- Modellnamen und Tags
- lokale Modellverwaltung
- `ollama list`
- `ollama pull`
- typische Fehler bei 404 Modell nicht gefunden
- GPU/CPU-Verhalten allgemein

Zu dokumentieren:

```markdown
## Ollama Runtime

### Relevante API-Endpunkte

### Modellauflösung

### Typische Fehler

### Empfohlene Diagnosebefehle

```bash
ollama list
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```
```

---

# Rechercheteil C — Deutsche Umlaute, Unicode und Suche

## 5. Recherchiere Unicode-Normalisierung

Recherchiere offizielle Quellen zu:

- Unicode Normalization Forms NFC, NFD, NFKC, NFKD
- Python `unicodedata.normalize`
- Unicode Case Folding
- Python `str.casefold()`
- Unterschiede zwischen `.lower()` und `.casefold()`
- Behandlung von `ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`, `ß`, `ẞ`
- Probleme mit zusammengesetzten Zeichen: `ä` vs `a` + combining diaeresis
- Dateinamen und Betriebssysteme
- Suchindexierung und Normalisierung

Zu dokumentieren:

```markdown
## Unicode-Strategie für Deutsch

### Grundsatz

Interne Textrepräsentation: Unicode NFC.

### Warum NFC?

### Wann NFKC?

### Casefolding

### Umlaute

| Zeichen | Primäre Form | ASCII-Fallback | Bemerkung |
|---|---|---|---|
| ä | ä | ae | |
| ö | ö | oe | |
| ü | ü | ue | |
| Ä | Ä | Ae/ae | |
| Ö | Ö | Oe/oe | |
| Ü | Ü | Ue/ue | |
| ß | ß | ss | |
| ẞ | ẞ | SS/ss | |

### Niemals blind transliterieren

### Suche vs Anzeige
```

---

## 6. Entwickle eine Projektstrategie für deutsche Umlaute

Die Strategie muss unterscheiden:

## Anzeige / Reports

- Umlaute bleiben erhalten.
- Keine automatische Umwandlung `ä -> ae` im Reporttext.
- Ausgabe in UTF-8.
- Markdown-Dateien als UTF-8.

## Suche / Matching

- Primär Unicode NFC + casefold.
- Zusätzlich optional ASCII-Fallback-Feld für Suchindizes:
  - `müller` matcht auch `mueller`
  - `straße` matcht auch `strasse`
- Originaltext immer speichern.
- Normalisierte Suchfelder nur ergänzend.

## Slugs / Dateinamen

- Für menschenlesbare Titel: Unicode erlaubt, aber vorsichtig.
- Für technische Dateinamen/IDs:
  - ASCII-Fallback
  - lowercase
  - whitespace zu `-`
  - sichere Zeichenmenge `[a-z0-9._-]`
- Keine Pfade aus untrusted Input ohne Sanitizing.

## URLs

- URLs nicht selbst transliterieren.
- URLs mit Standardbibliothek korrekt percent-encoden.
- Keine manuelle Umlaut-Ersetzung in URLs.

## JSON / APIs

- UTF-8 beibehalten.
- `ensure_ascii=False` für lesbare lokale JSON-Dateien, wenn kompatibel.
- Für externe APIs Standard-Encoding beachten.

## Datenbanken / Indizes

- Originalfeld speichern.
- `normalized_text` für NFC + casefold.
- optional `ascii_folded_text` für `ä->ae`, `ö->oe`, `ü->ue`, `ß->ss`.
- Keine irreversible Normalisierung als einzige Datenbasis.

---

# Rechercheteil D — Tests und Implementierungsvorschlag

## 7. Entwickle Tests für Umlautstrategie

Schlage Tests vor, aber implementiere sie nur, wenn explizit erlaubt.

Tests sollen prüfen:

```python
normalize_text("Müller") == "Müller"  # NFD zu NFC
search_key("MÜLLER") == search_key("müller")
ascii_fold("Müller") == "mueller"
ascii_fold("Straße") == "strasse"
slugify_de("Müller Straße") == "mueller-strasse"
```

Weitere Testfälle:

- `Ärger`
- `Öl`
- `Übergröße`
- `Fußgänger`
- `ẞ`
- kombinierte Unicode-Zeichen
- JSON-Export mit Umlauten
- Markdown-Report mit Umlauten

---

## 8. Erstelle Dokumente im Repository

Erstelle folgende Dokumente:

```text
docs/llm/model-inventory.md
docs/llm/ollama-models.md
docs/llm/model-selection-policy.md
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
```

Optional:

```text
docs/adr/ADR-015-local-llm-model-policy.md
docs/adr/ADR-016-german-unicode-normalization.md
```

Dokumente müssen enthalten:

- Datum
- Quellen
- klare Empfehlungen
- offene Unsicherheiten
- konkrete Projektregeln
- nächste Issues

---

# Pflichtstruktur der Dokumente

## `docs/llm/model-inventory.md`

```markdown
# Local LLM Model Inventory

## Stand

## Im Repository gefundene Modellvariablen

## Aktuelle Modellrollen

| Rolle | Variable | Default | Zweck |
|---|---|---|---|

## Gefundene Modellnamen

## Unsicherheiten

## Quellen
```

## `docs/llm/ollama-models.md`

```markdown
# Ollama Models used by Researcher

## Ollama Runtime

## Chat/Summary Model

## Embedding Model

## Diagnostics

## Common Errors

## Quellen
```

## `docs/llm/model-selection-policy.md`

```markdown
# Model Selection Policy

## Ziel

## Chat/Summary-Modell

## Embedding-Modell

## Kein Cloud-Fallback

## Fallback-Regeln

## Hardware-/VRAM-Hinweise

## Prompting-Regeln

## Quellen
```

## `docs/text/unicode-german-strategy.md`

```markdown
# German Unicode and Umlaut Strategy

## Ziel

## Unicode Normalization

## Casefolding

## Umlaute

## ß / ẞ

## Anzeige vs Suche vs Slugs

## Projektregeln

## Tests

## Quellen
```

## `docs/text/umlaut-search-and-slug-policy.md`

```markdown
# Umlaut Search and Slug Policy

## Ziel

## Search Keys

## ASCII Folding

## Slugs

## Dateinamen

## URLs

## JSON/Markdown

## Do / Don't

## Testfälle

## Quellen
```

---

# Quellenanforderungen

Jede wichtige Aussage muss eine Quelle haben.

Mindestens recherchieren:

## LLM / Ollama

- Ollama offizielle Dokumentation
- Ollama Library für `nomic-embed-text`
- Nomic Model Card / Hugging Face
- Qwen offizielle Model Card / Dokumentation
- Ollama Qwen Library, falls relevant

## Unicode / Deutsch

- Unicode Consortium Normalization
- Python `unicodedata` Dokumentation
- Python `str.casefold()` Dokumentation
- Unicode FAQ oder Technical Reports zu Normalization
- ggf. SQLite FTS5 / Whoosh Unicode-Handling, falls relevant

---

# Validierung

Nach Dokumentation ausführen:

```bash
make quality
make coverage
```

Zusätzlich prüfen:

```bash
grep -RIn "OLLAMA_CHAT_MODEL\|OLLAMA_EMBEDDING_MODEL\|nomic-embed-text\|qwen" docs/llm .env.example README.md
grep -RIn "NFC\|casefold\|Umlaut\|ä\|ö\|ü\|ß" docs/text docs/adr || true
```

Wenn Markdown-Lint existiert:

```bash
make docs-lint
```

Falls nicht vorhanden, nicht einführen.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Internetrecherche zu allen verwendeten lokalen Modellen durchgeführt wurde
- Modellinventar im Repo dokumentiert ist
- Ollama Runtime dokumentiert ist
- Chat-/Summary- und Embedding-Rollen klar getrennt sind
- Unsicherheiten zum exakten Qwen-Modell dokumentiert sind
- deutsche Unicode-/Umlautstrategie dokumentiert ist
- Such-/Slug-Policy dokumentiert ist
- Quellen in den Dokumenten enthalten sind
- empfohlene Tests für Umlaute dokumentiert sind
- keine produktive Logik geändert wurde
- keine neuen Features gebaut wurden
- `make quality` weiterhin grün ist
- GitHub-Kommentar mit Zusammenfassung geschrieben wurde

Minimal akzeptabel:

- `docs/llm/model-inventory.md`
- `docs/llm/ollama-models.md`
- `docs/text/unicode-german-strategy.md`
- Quellenangaben
- `make quality` grün

Gut:

- zusätzlich `model-selection-policy.md`
- zusätzlich `umlaut-search-and-slug-policy.md`
- ADR-Vorschläge
- konkrete Testfälle

Sehr gut:

- KI-Agenten können anhand der Dokumente Modellrollen, Fallbacks und deutsche Textnormalisierung korrekt anwenden

---

# Abschlussbericht-Vorlage

```markdown
# Researcher LLM-/Unicode-Dokumentation Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Modellinventar recherchiert | |
| Ollama Runtime dokumentiert | |
| Chat-/Summary-Modell dokumentiert | |
| Embedding-Modell dokumentiert | |
| Qwen-Unsicherheiten dokumentiert | |
| Modellrollen geklärt | |
| Unicode-/Umlautstrategie erstellt | |
| Search-/Slug-Policy erstellt | |
| Quellen dokumentiert | |
| Testfälle vorgeschlagen | |
| `make quality` grün | |
| Keine produktive Logik geändert | |
| GitHub-Kommentar geschrieben | |

## Recherchierte Modelle

| Modell | Rolle | Quelle | Empfehlung |
|---|---|---|---|

## Unicode-Entscheidungen

| Bereich | Entscheidung |
|---|---|
| Interne Normalisierung | |
| Suche | |
| Slugs | |
| Reports | |
| JSON | |

## Erstellte Dateien

## Wichtigste Quellen

## Offene Unsicherheiten

## Nächste empfohlene Issues
```

---

# Empfohlene Folge-Issues

1. `Implement German Unicode normalization helpers and tests`
2. `Add docs-aware prompt context for local AI agents`
3. `Model compatibility check for local Ollama models`
4. `Research Evaluation Dataset: German umlaut query fixtures`
