# Researcher — Prompt: LLM-/Unicode-Erkenntnisse sicher in den Code einbauen

## Rolle

Du bist ein Senior Python Implementation Engineer, Local-LLM Runtime Engineer und Unicode/Text-Normalization Specialist.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die zuvor recherchierten Erkenntnisse zu lokalen LLM-Modellen, Ollama-Modellrollen und deutscher Unicode-/Umlautstrategie sicher, minimal und testgetrieben in den Code einzubauen.

---

# Ausgangslage

Es existiert oder soll existieren:

```text
docs/llm/model-inventory.md
docs/llm/ollama-models.md
docs/llm/model-selection-policy.md
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
```

Diese Dokumente definieren:

- Chat-/Summary-Modell und Embedding-Modell sind getrennte Rollen.
- `OLLAMA_CHAT_MODEL` ist für Textgenerierung/Summary.
- `OLLAMA_EMBEDDING_MODEL` ist für Embeddings.
- Embedding-Modelle wie `nomic-embed-text` dürfen nicht als Chat-/Summary-Modell verwendet werden.
- Cloud-Fallbacks bleiben im Standard verboten.
- Deutsche Umlaute bleiben in Anzeige/Reports erhalten.
- Interne Textnormalisierung soll Unicode NFC verwenden.
- Suche soll zusätzlich casefold- und optional ASCII-Folding unterstützen.
- Slugs/technische Dateinamen sollen ASCII-sicher sein.
- Originaltext darf niemals durch irreversible Normalisierung ersetzt werden.

---

# Oberstes Ziel

Implementiere die Erkenntnisse aus der Dokumentation in kleinen, sicheren Code-Schritten:

1. Modellrollen im Code zentralisieren.
2. Ollama-Modellauflösung robuster machen.
3. Embedding- und Chatmodell technisch trennen.
4. Unicode-/Umlaut-Helfer für Deutsch einführen.
5. Suche/Slug/Dateinamen/Reports konsistent behandeln.
6. Tests für Modellrollen und Umlaute ergänzen.
7. Keine bestehende Funktionalität brechen.
8. `make quality` bleibt grün.

---

# Harte Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- Cloud-Provider aktivieren
- externe API-Fallbacks einführen
- automatisch Ollama-Modelle herunterladen
- große Architektur-Refactorings durchführen
- Vendor-Code im `gpt_researcher/`-Submodul ändern
- Tests löschen
- Coverage-Schwelle senken
- Quality-Gates lockern
- Report-Evaluation künstlich beschönigen
- Umlaute im sichtbaren Reporttext pauschal in ASCII umwandeln

---

# Grundprinzipien

## 1. Dokumentation ist Quelle der Wahrheit

Vor jeder Änderung lies:

```text
docs/llm/model-inventory.md
docs/llm/ollama-models.md
docs/llm/model-selection-policy.md
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
.env.example
scripts/runtime_smoke.py
scripts/research_happy_path.py
config/
search/
darknet_search/
onion_discovery/
vectordb/
mcp_tools/
```

Wenn Dokumente fehlen:

- nicht blind implementieren
- fehlende Doku benennen
- minimalen Implementation-Plan erstellen
- erst dann Code ändern

## 2. Minimaler Einbau

Keine breite Neuarchitektur.

Bevorzugt:

- kleine Utility-Module
- gezielte Tests
- bestehende Skripte verwenden Utility-Funktionen
- klare Fehlermeldungen

## 3. Originaltext bleibt erhalten

Originale deutsche Texte bleiben unverändert gespeichert und angezeigt.

Normalisierte Formen sind nur Zusatzfelder oder Suchschlüssel.

## 4. Modellrollen nie vermischen

Embedding-Modell und Chat-/Summary-Modell dürfen nicht vertauscht werden.

---

# Arbeitsreihenfolge

## 1. Ist-Zustand analysieren

Führe aus:

```bash
grep -RIn "OLLAMA_CHAT_MODEL\|OLLAMA_EMBEDDING_MODEL\|OLLAMA_EMBED_MODEL\|nomic-embed-text\|qwen\|ollama" config scripts vectordb search mcp_tools .env.example README.md docs || true

grep -RIn "slug\|normalize\|casefold\|lower()\|unicodedata\|ä\|ö\|ü\|ß" config scripts search darknet_search onion_discovery vectordb mcp_tools tests docs || true
```

Dokumentiere:

- Wo Modellnamen hart codiert sind.
- Wo Chat-/Embedding-Rollen schon getrennt sind.
- Wo Unicode-Normalisierung fehlt.
- Wo Slugs/Dateinamen aus User-Input entstehen.
- Wo Suche/Indexierung deutsche Texte verarbeitet.
- Wo Reports deutsche Texte ausgeben.

---

# Teil A — Modellrollen sicher einbauen

## 2. Zentrales Modell-Konfigurationsmodul prüfen oder erstellen

Prüfe, ob es bereits geeignete Konfigurationslogik gibt:

```text
config/
scripts/runtime_smoke.py
scripts/research_happy_path.py
vectordb/embedding.py
```

Wenn sinnvoll, erstelle ein kleines Modul:

```text
config/ollama_models.py
```

oder integriere in bestehende Config-Struktur.

Vorgeschlagene Datentypen:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OllamaModelConfig:
    base_url: str
    chat_model: str
    embedding_model: str
    allow_model_fallback: bool = False
```

Funktionen:

```python
def load_ollama_model_config() -> OllamaModelConfig:
    ...

def is_embedding_model_name(model_name: str) -> bool:
    ...

def validate_model_roles(config: OllamaModelConfig) -> list[str]:
    ...
```

Regeln:

- `OLLAMA_CHAT_MODEL` darf nicht leer sein.
- `OLLAMA_EMBEDDING_MODEL` darf nicht leer sein.
- `OLLAMA_CHAT_MODEL` darf nicht offensichtlich ein Embedding-Modell sein.
- `nomic-embed-text` ist Embedding-Rolle.
- Default-Werte müssen mit `.env.example` und Doku übereinstimmen.

---

## 3. Modellauflösung zentralisieren

Wenn bereits in `scripts/research_happy_path.py` eine Funktion wie `resolve_chat_model()` existiert:

- nicht duplizieren
- in gemeinsames Modul auslagern oder sauber wiederverwenden
- Tests anpassen

Ziel:

```python
def resolve_chat_model(
    requested_model: str,
    available_models: list[str],
    allow_fallback: bool = False,
) -> ModelResolution:
    ...
```

`ModelResolution` sollte mindestens enthalten:

```python
@dataclass(frozen=True)
class ModelResolution:
    status: str
    requested_model: str
    used_model: str | None
    fallback_used: bool
    message: str
```

Statuswerte:

```text
OK
MODEL_MISSING
NO_MODELS_AVAILABLE
FALLBACK_SELECTED
CONFIG_ERROR
```

Wichtig:

- Fallback darf niemals ein Embedding-Modell auswählen.
- Fallback ist nur erlaubt, wenn `ALLOW_OLLAMA_MODEL_FALLBACK=true`.
- Strict Mode muss bei fehlendem Chatmodell fehlschlagen.
- Standardmodus darf graceful degradieren, aber muss Report/Warnung erzeugen.

---

## 4. Runtime-Smoke und Happy-Path anschließen

Passe an:

```text
scripts/runtime_smoke.py
scripts/research_happy_path.py
```

Ziele:

- Beide verwenden dieselbe Modellkonfiguration.
- Beide prüfen Chat- und Embedding-Modell getrennt.
- Fehlermeldungen sind identisch oder konsistent.
- Reports dokumentieren:
  - requested chat model
  - used chat model
  - embedding model
  - fallback used
  - degraded mode

Keine Cloud-Fallbacks.

---

# Teil B — Deutsche Unicode-/Umlautstrategie einbauen

## 5. Textnormalisierungsmodul erstellen

Erstelle:

```text
text_utils/
```

oder, falls Projektstruktur besser passt:

```text
utils/text_normalization.py
```

Empfohlen:

```text
text_utils/__init__.py
text_utils/german.py
```

Minimaler Funktionsumfang:

```python
def normalize_nfc(text: str) -> str:
    ...

def normalize_search_key(text: str) -> str:
    ...

def ascii_fold_german(text: str) -> str:
    ...

def slugify_german(text: str, max_length: int = 120) -> str:
    ...

def normalize_markdown_text(text: str) -> str:
    ...
```

Regeln:

## `normalize_nfc`

- verwendet `unicodedata.normalize("NFC", text)`
- gibt Unicode-Text zurück
- keine Transliteration

## `normalize_search_key`

- NFC
- `casefold()`
- whitespace normalisieren
- Umlaute bleiben erhalten
- geeignet für Unicode-Suchvergleich

## `ascii_fold_german`

- NFC + casefold
- `ä -> ae`
- `ö -> oe`
- `ü -> ue`
- `ß -> ss`
- `Ä/Ö/Ü` über casefold ebenfalls
- nicht für Anzeige verwenden

## `slugify_german`

- nutzt ASCII-Folding
- lowercase
- whitespace und Trennzeichen zu `-`
- entfernt unsichere Zeichen
- erlaubt nur `[a-z0-9._-]`
- keine Pfadseparatoren
- kürzt kontrolliert auf `max_length`
- niemals leeren String zurückgeben, sondern z. B. `untitled`

## `normalize_markdown_text`

- NFC
- Umlaute bleiben erhalten
- keine ASCII-Faltung

---

## 6. Keine irreversible Migration

Dieses Issue soll keine bestehenden Daten migrieren.

Wenn bestehende Indizes oder Dateien normalisierte Daten brauchen:

- nur neue Helper einführen
- bestehende Codepfade minimal anschließen, wenn risikoarm
- sonst Folge-Issue vorschlagen

Nicht erlaubt:

- bestehende Datenbestände überschreiben
- Index neu bauen, außer rein testweise
- Reports rückwirkend ändern

---

## 7. Sinnvolle Anschlussstellen prüfen

Prüfe, ob die Helper ohne Risiko verwendet werden können in:

```text
scripts/research_happy_path.py
scripts/evaluate_research_report.py
scripts/research_multi_query_eval.py
search/
darknet_search/
onion_discovery/
mcp_tools/evidence_store.py
```

Empfohlene sichere Anschlüsse:

### Reports

- Reporttext vor Schreiben mit `normalize_markdown_text()`
- Umlaute bleiben sichtbar

### Report-Dateinamen

- Query-basierte Dateinamen nur mit `slugify_german()`, falls solche Dateinamen existieren
- Wenn aktuell timestamp-basierte Dateinamen genutzt werden, nichts ändern

### Suche/Evaluation

- Query-Vergleich mit `normalize_search_key()`
- optionale ASCII-Fallback-Vergleiche nur ergänzend

### Evidence Store / IDs

- Keine Änderung an bestehenden IDs, wenn Kompatibilitätsrisiko besteht
- Falls neue Slugs entstehen, `slugify_german()` verwenden

---

# Teil C — Tests

## 8. Modellrollen-Tests ergänzen

Erstelle oder erweitere:

```text
tests/test_ollama_model_config.py
tests/test_runtime_smoke.py
tests/test_research_happy_path.py
```

Testfälle:

- `OLLAMA_CHAT_MODEL` und `OLLAMA_EMBEDDING_MODEL` werden getrennt geladen.
- `nomic-embed-text` wird als Embedding-Modell erkannt.
- Embedding-Modell wird nicht als Chat-Fallback gewählt.
- fehlendes Chat-Modell führt in Strict Mode zu Fehler.
- Fallback wählt nur nicht-Embedding-Modelle.
- Report enthält requested/used Chat Model und Embedding Model.
- `.env.example` enthält beide Variablen.

---

## 9. Unicode-/Umlaut-Tests ergänzen

Erstelle:

```text
tests/test_german_text_normalization.py
```

Pflichttests:

```python
def test_normalize_nfc_combining_umlaut():
    assert normalize_nfc("Mu\u0308ller") == "Müller"

def test_search_key_casefold_umlauts():
    assert normalize_search_key("MÜLLER") == normalize_search_key("müller")

def test_ascii_fold_german_umlauts():
    assert ascii_fold_german("Müller Straße") == "mueller strasse"

def test_slugify_german():
    assert slugify_german("Müller Straße!") == "mueller-strasse"

def test_sharp_s():
    assert ascii_fold_german("Fußgänger") == "fussgaenger"

def test_markdown_keeps_umlauts():
    assert normalize_markdown_text("Übergröße Straße") == "Übergröße Straße"
```

Weitere Fälle:

- `Ärger`
- `Öl`
- `Übergröße`
- `ẞ`
- leere Strings
- Pfadseparatoren
- sehr lange Slugs
- Sonderzeichen
- kombinierte Unicode-Zeichen

---

# Teil D — Dokumentation aktualisieren

Aktualisiere:

```text
docs/llm/model-selection-policy.md
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
docs/runtime/research-happy-path.md
.env.example
README.md
```

Dokumentiere:

- welche Helper implementiert wurden
- welche Regeln jetzt technisch abgesichert sind
- welche Regeln nur Policy bleiben
- welche Folge-Issues offen bleiben

Optional ADRs aktualisieren:

```text
docs/adr/ADR-015-local-llm-model-policy.md
docs/adr/ADR-016-german-unicode-normalization.md
```

---

# Validierung

Nach Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local
```

Zusätzlich gezielt:

```bash
python3 -m pytest tests/test_german_text_normalization.py -q
python3 -m pytest tests/ -q -k "ollama_model or runtime_smoke or research_happy_path"
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

Erwartung:

- alle Gates grün
- Coverage >=78%
- Runtime-Smoke bleibt 4/4, falls Dienste verfügbar
- Report-Evaluation bleibt >=90 Overall
- keine Cloud-Fallbacks

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Modellkonfiguration zentral oder konsistent implementiert ist
- Chat-/Summary- und Embedding-Modell technisch getrennt sind
- Embedding-Modell nicht als Chatmodell verwendet wird
- Fallback-Regeln getestet sind
- `.env.example` konsistent ist
- Unicode-NFC-Helper existiert
- Search-Key-Helper existiert
- German ASCII-Folding existiert
- German Slugify existiert
- Markdown-Normalisierung erhält Umlaute
- Tests für deutsche Umlaute existieren
- Reports behalten Umlaute sichtbar bei
- Slugs/technische Namen sind ASCII-sicher, wenn genutzt
- Doku wurde aktualisiert
- `make quality` bleibt grün
- `make coverage` bleibt grün
- keine produktive Featurelogik wurde erweitert
- keine Cloud-Provider wurden eingeführt
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- Textnormalisierungsmodul + Tests
- Modellrollen-Tests
- Doku aktualisiert
- Quality Gates grün

Gut:

- Runtime-Smoke und Happy-Path nutzen gemeinsame Modellkonfiguration
- Report-Evaluation bleibt stabil
- `.env.example`, README und Doku sind konsistent

Sehr gut:

- KI-Agenten können anhand von Code + Doku zuverlässig wissen:
  - welches Modell wofür genutzt wird
  - wie deutsche Umlaute verarbeitet werden
  - wo Originaltext erhalten bleibt
  - wo ASCII-Folding erlaubt ist

---

# Abschlussbericht-Vorlage

```markdown
# Researcher LLM-/Unicode-Codeintegration Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Modellkonfiguration zentralisiert/konsistent | |
| Chat-/Embedding-Rollen getrennt | |
| Embedding-als-Chat verhindert | |
| Fallback-Regeln getestet | |
| Unicode-NFC-Helper implementiert | |
| Search-Key-Helper implementiert | |
| German ASCII-Folding implementiert | |
| German Slugify implementiert | |
| Markdown erhält Umlaute | |
| Umlaut-Tests vorhanden | |
| Modellrollen-Tests vorhanden | |
| Doku aktualisiert | |
| `make quality` grün | |
| `make coverage` grün | |
| Keine Cloud-Fallbacks | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Neue/Geänderte Dateien

## Testfälle

| Bereich | Anzahl | Ergebnis |
|---|---:|---|
| Modellrollen | | |
| Unicode/Umlaute | | |
| Runtime/Happy-Path | | |

## Validierte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Bewusst nicht umgesetzt

## Risiken

## Nächste empfohlene Issues
```

---

# Empfohlene Folge-Issues

1. `Apply German search keys to indexes without migrating original data`
2. `Add German umlaut query fixtures to research evaluation dataset`
3. `Model compatibility check command for local Ollama models`
4. `Docs-aware prompt context for local AI agents`
