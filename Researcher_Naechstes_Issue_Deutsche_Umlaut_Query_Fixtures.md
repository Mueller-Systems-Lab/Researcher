# Researcher — Nächstes Issue: Deutsche Umlaut-Query-Fixtures und Search-Key-Regression einführen

## Rolle

Du bist ein Senior Search Quality Engineer, Unicode Regression Test Engineer und Local-First Research Evaluation Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis von Issue #75:

- `config/ollama_models.py` eingeführt
- `text_utils/german.py` eingeführt
- 54 neue Tests für Modellrollen und deutsche Textnormalisierung
- `make quality` grün
- Coverage: 79.17%
- keine Cloud-Fallbacks
- keine neuen Research-Features

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, die neue deutsche Unicode-/Umlautstrategie mit realistischen, harmlosen Query-Fixtures und Regressionstests in die Research-Evaluation einzubinden, ohne bestehende Indizes oder Daten zu migrieren.

---

# Ausgangslage

Nach #75 existieren getestete Helper:

```python
normalize_nfc()
normalize_search_key()
ascii_fold_german()
slugify_german()
normalize_markdown_text()
```

Bekannte Entscheidungen:

- Reports behalten Umlaute sichtbar.
- Interne Textnormalisierung nutzt NFC.
- Suche kann `casefold()` und optional ASCII-Folding verwenden.
- Technische Slugs/Dateinamen sollen ASCII-sicher sein.
- Originaltext darf nicht irreversibel ersetzt werden.
- `slugify_german()` ist aktuell vorbereitet, aber noch kaum produktiv genutzt.

Offene Chance:

> Deutsche Umlautfälle sind technisch getestet, aber noch nicht als Research-/Search-/Evaluation-Fixtures abgesichert.

---

# Oberstes Ziel

Erstelle harmlose deutsche Query-Fixtures und Regressionstests, die prüfen, dass deutsche Umlaute in Queries, Reports und Evaluation korrekt verarbeitet werden.

Das Issue soll beweisen:

1. deutsche Query-Texte bleiben in Reports sichtbar erhalten
2. `ä`, `ö`, `ü`, `ß`, `ẞ` werden normalisiert vergleichbar
3. ASCII-Fallbacks wie `mueller` können mit `müller` verglichen werden
4. technische Slugs sind ASCII-sicher
5. Report-Evaluation bleibt mit deutschen Queries stabil
6. keine bestehende Datenmigration nötig ist
7. keine Cloud-Provider aktiviert werden

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- bestehende Indizes migrieren
- Darknet-/Security-/CVE-Queries verwenden
- personenbezogene Queries verwenden
- Cloud-Provider aktivieren
- SearXNG-/Ollama-Architektur ändern
- Vendor-Code im `gpt_researcher/`-Submodul anfassen
- Quality-Gates lockern
- Coverage-Schwelle senken
- Tests löschen

---

# Sichere deutsche Testqueries

Verwende nur harmlose, generische Queries.

Erlaubte Beispiele:

```text
Was ist eine Suchmaschine?
Was ist freie Software?
Was bedeutet lokale KI?
Was ist eine Fußgängerzone?
Was ist die Müllerstraße als Wortbeispiel?
Was bedeutet Übergröße?
```

Nicht verwenden:

```text
Personennamen realer Personen
Adressen realer Ziele
CVE
Exploit
Vulnerability
Credentials
Darknet Forum
site:
target domain
```

Wichtig:

`Müllerstraße` darf als reines Wort-/Unicode-Beispiel verwendet werden, nicht als echte Orts-/Personenrecherche.

---

# Arbeitsreihenfolge

## 1. Bestehenden Zustand prüfen

Lies:

```text
text_utils/german.py
tests/test_german_text_normalization.py
scripts/research_happy_path.py
scripts/evaluate_research_report.py
scripts/research_multi_query_eval.py
docs/text/unicode-german-strategy.md
docs/text/umlaut-search-and-slug-policy.md
docs/evaluation/
```

Führe aus:

```bash
make quality
make coverage
python3 -m pytest tests/test_german_text_normalization.py -q
```

Dokumentiere:

- welche Unicode-Helfer vorhanden sind
- welche schon produktiv genutzt werden
- welche nur vorbereitet sind
- wo Query-Fixtures sinnvoll angeschlossen werden können

---

## 2. Deutsche Query-Fixtures erstellen

Erstelle z. B.:

```text
tests/fixtures/german_queries.json
```

Empfohlenes JSON-Format:

```json
[
  {
    "id": "de-search-engine",
    "query": "Was ist eine Suchmaschine?",
    "expected_terms": ["Suchmaschine"],
    "forbidden_terms": ["CVE", "Exploit", "Credentials"],
    "requires_umlaut": false
  },
  {
    "id": "de-footpath-sharp-s",
    "query": "Was ist eine Fußgängerzone?",
    "expected_terms": ["Fußgängerzone"],
    "ascii_folded": "was ist eine fussgaengerzone",
    "requires_umlaut": true
  },
  {
    "id": "de-oversize-umlaut",
    "query": "Was bedeutet Übergröße?",
    "expected_terms": ["Übergröße"],
    "ascii_folded": "was bedeutet uebergroesse",
    "requires_umlaut": true
  }
]
```

Regeln:

- keine echten Personen
- keine echten Ziel-Domains
- keine Security-/Exploit-Queries
- nur generische Sprach-/Konzeptfragen

---

## 3. Fixture-Loader implementieren

Erstelle minimal:

```text
tests/helpers/german_query_fixtures.py
```

Funktionen:

```python
def load_german_query_fixtures() -> list[GermanQueryFixture]:
    ...

def validate_german_fixture_safety(query: str) -> None:
    ...
```

Wenn ein allgemeiner Query-Safety-Guard existiert:

- wiederverwenden
- nicht duplizieren

---

## 4. Regressionstests für Query-Normalisierung

Erstelle:

```text
tests/test_german_query_fixtures.py
```

Testfälle:

- alle Fixtures laden
- alle Queries sind NFC-normalisiert
- alle Queries bestehen den Safety-Guard
- `normalize_search_key()` ist stabil
- `ascii_fold_german()` liefert erwartete Fallbacks
- `slugify_german()` erzeugt sichere IDs
- keine Query enthält verbotene Begriffe
- Originalquery bleibt mit Umlauten erhalten

---

## 5. Optional: Multi-Query-Evaluation mit deutschen Queries vorbereiten

Wenn `scripts/research_multi_query_eval.py` bereits `--queries-file` unterstützt:

- nutze die Fixtures als optionale deutsche Query-Suite

Beispiel:

```bash
python3 scripts/research_multi_query_eval.py   --queries-file tests/fixtures/german_queries.json   --limit 3
```

Wenn `--queries-file` noch nicht existiert:

- minimal ergänzen
- keine neue Feature-Architektur bauen
- weiterhin Safety-Guard erzwingen

Makefile optional:

```makefile
research-evaluate-german:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --queries-file tests/fixtures/german_queries.json --limit 3
```

Wichtig:

- nicht in `make quality` aufnehmen, wenn Live-Runtime nötig ist
- nur optionaler Evaluation-Target

---

## 6. Report-/Evaluation-Regression für deutsche Umlaute

Erstelle Tests, die gemockte deutsche Reports evaluieren:

```text
tests/test_german_report_evaluation.py
```

Testfälle:

- Report mit `Übergröße`, `Fußgängerzone`, `Müllerstraße` bleibt lesbar
- Evaluation akzeptiert deutsche Unicode-Zeichen
- Source Coverage bleibt korrekt
- Traceability erkennt Quellen-IDs
- Hallucination-Heuristik erkennt deutsche Risiko-Wörter, falls in Evaluation definiert
- Local-First bleibt 100

Keine echten Netzwerkdienste in Unit-Tests.

---

## 7. Dokumentation aktualisieren

Aktualisiere:

```text
docs/text/umlaut-search-and-slug-policy.md
docs/text/unicode-german-strategy.md
docs/evaluation/multi-query-evaluation.md
```

Optional neu:

```text
docs/evaluation/german-query-fixtures.md
```

Pflichtinhalt:

```markdown
# German Query Fixtures

## Ziel

## Warum deutsche Fixtures?

## Enthaltene Query-Typen

| ID | Query | Zweck |
|---|---|---|

## Safety Rules

## Normalization Rules

## ASCII-Fallback

## Ausführen

```bash
python3 -m pytest tests/test_german_query_fixtures.py -q
make research-evaluate-german
```

## Grenzen

## Nächste Schritte
```

---

# Validierung

Nach Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local

python3 -m pytest tests/test_german_text_normalization.py -q
python3 -m pytest tests/ -q -k "german or umlaut or unicode"
```

Optional, wenn Runtime verfügbar:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-evaluate-german
```

Erwartung:

- `make quality` grün
- Coverage >=78%
- deutsche Fixture-Tests grün
- keine Cloud-Fallbacks
- keine riskanten Queries

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- deutsche Query-Fixtures existieren
- Fixtures sind harmlos und Safety-Guard-validiert
- NFC-Normalisierung wird auf Fixtures getestet
- ASCII-Folding für deutsche Queries wird getestet
- Slug-Sicherheit wird getestet
- Original-Umlaute bleiben in Query/Report erhalten
- gemockte deutsche Report-Evaluation existiert oder bestehende Evaluation deckt deutsche Reports ab
- optionaler deutscher Multi-Query-Evaluation-Target existiert oder bewusst vertagt ist
- Doku wurde aktualisiert
- `make quality` bleibt grün
- `make coverage` bleibt grün
- keine produktive Featurelogik wurde erweitert
- keine Cloud-Provider wurden eingeführt
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- Fixture-Datei
- Fixture-Tests
- Report-Evaluation-Test mit Umlauten
- Doku
- Quality Gates grün

Gut:

- optionaler `research-evaluate-german` Target
- `--queries-file` unterstützt deutsche Query-Suite
- Safety-Guard wird wiederverwendet

Sehr gut:

- deutsche Queries können lokal live evaluiert werden, ohne dass Umlaute beschädigt oder ASCII-only erzwungen werden

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Deutsche Query-Fixtures Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Deutsche Query-Fixtures erstellt | |
| Safety-Guard validiert Fixtures | |
| NFC-Normalisierung getestet | |
| ASCII-Folding getestet | |
| Slug-Sicherheit getestet | |
| Original-Umlaute bleiben erhalten | |
| Deutsche Report-Evaluation getestet | |
| Optionaler German-Eval-Target | |
| Doku aktualisiert | |
| `make quality` grün | |
| `make coverage` grün | |
| Keine Cloud-Fallbacks | |
| Keine neuen Research-Features | |
| GitHub-Kommentar geschrieben | |

## Neue Fixtures

| ID | Query | Zweck |
|---|---|---|

## Tests

| Testdatei | Anzahl | Ergebnis |
|---|---:|---|

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
2. `Model compatibility check command for local Ollama models`
3. `Docs-aware prompt context for local AI agents`
4. `Release tag after CI/Playwright cleanup`
