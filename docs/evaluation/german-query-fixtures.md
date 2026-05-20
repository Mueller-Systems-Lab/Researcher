# German Query Fixtures

## Ziel

Deutsche Query-Fixtures stellen sicher, dass Umlaute (ä, ö, ü, ß, ẞ) in Research-Queries,
Reports und der Evaluation korrekt verarbeitet werden — ohne irreversible Datenmigration oder Cloud-Provider.

## Warum deutsche Fixtures?

- Deutsche Texte enthalten Umlaute und ß, die von Suchmaschinen und LLMs unterschiedlich behandelt werden
- NFC-Normalisierung, casefold() und ASCII-Folding müssen für Deutsch getestet werden
- Reports müssen Umlaute sichtbar erhalten, während technische Slugs ASCII-sicher sein müssen
- Der Safety-Guard muss auch bei deutschen Queries greifen

## Enthaltene Query-Typen

| ID | Query | Zweck |
|---|---|---|
| de-search-engine | Was ist eine Suchmaschine? | Basis-Query ohne Umlaute |
| de-free-software | Was ist freie Software? | Basis-Query ohne Umlaute |
| de-local-ai | Was bedeutet lokale KI? | Basis-Query ohne Umlaute |
| de-footpath-sharp-s | Was ist eine Fußgängerzone? | ß (Sharp S) |
| de-oversize-umlaut | Was bedeutet Übergröße? | Ü + ß |
| de-muellerstrasse-example | Was ist die Müllerstraße als Wortbeispiel? | ü |

## Safety Rules

- Keine echten Personen, Adressen oder Domains
- Keine Security-/Exploit-/CVE-Queries
- Nur generische Sprach-/Konzeptfragen
- Jede Query wird vor Verwendung durch den Safety-Guard validiert
- `Müllerstraße` ist ein reines Unicode-Wortbeispiel, keine Personenrecherche

## Normalization Rules

1. **NFC-Normalisierung**: Alle Queries werden in Unicode NFC gehalten
2. **Search-Key**: casefold() für fallunabhängige Suche (erkennt ß→ss)
3. **ASCII-Folding**: Nur für technische IDs/Slugs (ä→ae, ö→oe, ü→ue, ß→ss)
4. **Slug**: ASCII-sicher, keine Umlaute, keine Pfadseparatoren
5. **Reports**: Umlaute bleiben sichtbar erhalten

## Ausführen

```bash
# Fixture-Tests (Unit, keine Netzwerkdienste)
python3 -m pytest tests/test_german_query_fixtures.py -q

# Report-Evaluation-Tests (gemockt, keine Netzwerkdienste)
python3 -m pytest tests/test_german_report_evaluation.py -q

# Alle deutschen Tests
python3 -m pytest tests/ -q -k "german or umlaut or unicode"

# Live Multi-Query-Evaluation mit deutschen Queries (benötigt SearXNG + Ollama)
make research-evaluate-german
```

## Grenzen

- Fixtures sind rein strukturell/testgetrieben — keine produktive Featurelogik
- Live-Evaluation (`make research-evaluate-german`) benötigt laufende SearXNG- und Ollama-Dienste
- Keine Datenmigration — bestehende Indizes bleiben unverändert
- ASCII-Folding ist eine deutsche Konvention, kein Unicode-Standard
- `nomic-embed-text` hat keine offizielle Deutsch-Garantie (siehe ADR-016)

## Nächste Schritte

1. German Search Keys auf Indizes anwenden (ohne Datenmigration)
2. Deutsche Embedding-Qualität mit nomic-embed-text evaluieren
3. Mehrsprachige Query-Fixtures für weitere Sprachen
