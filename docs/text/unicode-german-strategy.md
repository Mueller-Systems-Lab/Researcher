# German Unicode and Umlaut Strategy

## Stand
2026-05-20

## Ziel
Festlegung, wie deutsche Texte intern normalisiert, gespeichert und durchsucht werden.

## Grundsatz
Interne Textrepräsentation: Unicode NFC. Quelle: https://www.unicode.org/reports/tr15/

## Implementierung im Projekt

- `text_utils/__init__.py` macht das Package explizit importierbar.
- `text_utils/german.py` stellt die fünf Helper bereit: `normalize_nfc`, `normalize_search_key`, `ascii_fold_german`, `slugify_german`, `normalize_markdown_text`.
- `normalize_markdown_text()` normalisiert auf NFC, lässt Umlaute im Inhalt aber erhalten.
- Die zugehörigen Tests liegen in `tests/test_german_text_normalization.py`.

## Unicode Normalization
- Unicode-Normalisierung macht kanonisch bzw. kompatibel äquivalente Zeichenfolgen vergleichbar. Quelle: https://www.unicode.org/reports/tr15/
- Die vier Formen sind NFC, NFD, NFKC und NFKD. Quelle: https://www.unicode.org/reports/tr15/
- Für gespeicherten Web-/Inhaltstext empfiehlt die W3C-nahe Dokumentation NFC. Quelle: https://www.unicode.org/reports/tr15/
- NFKC und NFKD dürfen **nicht** blind auf Inhaltstext angewendet werden, da sie semantische Unterschiede entfernen können. Quelle: https://www.unicode.org/reports/tr15/

## Casefolding
- `str.casefold()` ist für fallunabhängige Vergleiche gedacht und aggressiver als `str.lower()`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold
- Für Suche/Matching ist `casefold()` die bessere Basis als `lower()`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold
- Beispiele: `Straße` → `strasse`, `Müller` → `müller`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold

## Deutsche Umlaute
### Tabelle
| Zeichen | Primäre Form (NFC) | ASCII-Fallback | Bemerkung |
|---|---|---|---|
| ä | ä (U+00E4) | ae | Auch als a+U+0308 möglich. Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| ö | ö (U+00F6) | oe | Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| ü | ü (U+00FC) | ue | Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| Ä | Ä (U+00C4) | Ae | Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| Ö | Ö (U+00D6) | Oe | Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| Ü | Ü (U+00DC) | Ue | Quelle: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt |
| ß | ß (U+00DF) | ss | `casefold()` → `ss`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold |
| ẞ | ẞ (U+1E9E) | SS | `casefold()` → `ss`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold |

### Niemals blind transliterieren
- Report-Text: Umlaute bleiben original. UNSICHER: Das ist eine Projektregel, keine Unicode-Norm.
- Keine automatische Umwandlung `ä→ae` im Output. UNSICHER: Das ist eine Projektregel, keine Unicode-Norm.
- ASCII-Fallback ist eine deutsche Konvention, nicht der Unicode-Standard. Quelle für die Unicode-Trennung von kanonischer und Kompatibilitätsnormalisierung: https://www.unicode.org/reports/tr15/

## Anzeige vs Suche vs Slugs
### Anzeige / Reports
- Umlaute erhalten, UTF-8-Ausgabe. UNSICHER: Ausgabeformat ist eine Projektentscheidung.
- Keine ASCII-Konvertierung im Lesetext. UNSICHER: Projektregel.

### Suche / Matching
- NFC + `casefold()` als primärer Suchschlüssel. Quelle: https://www.unicode.org/reports/tr15/ , https://docs.python.org/3/library/stdtypes.html#str.casefold
- Optional: ASCII-Fallback-Feld (`ä→ae`, etc.). UNSICHER: Projektkonvention.
- Originaltext immer speichern. UNSICHER: Projektregel.

### Slugs / Dateinamen
- Für technische IDs: ASCII-Fallback + lowercase + `[-a-z0-9]`. UNSICHER: Projektkonvention.
- Für menschenlesbare Titel: Unicode erlaubt. UNSICHER: Projektkonvention.
- Keine Pfade aus unsicherem Input. UNSICHER: Sicherheitsregel.

### URLs
- Standardbibliothek für Percent-Encoding verwenden. UNSICHER: konkrete Implementierung abhängig vom Python-Stack.
- Keine manuelle Umlaut-Ersetzung in URLs. UNSICHER: Projektregel.

### JSON / APIs
- UTF-8 beibehalten. UNSICHER: Transport- und Storage-Konvention.
- `ensure_ascii=False` für lokale Dateien, wenn kompatibel. UNSICHER: projekt- und toolabhängig.

### Datenbanken / Indizes
- Originalfeld speichern.
- `normalized_text` für NFC + `casefold`.
- Optional `ascii_folded_text`.
- Hinweis: SQLite FTS5 `unicode61` entfernt Diakritika standardmäßig und ist case-insensitive gemäß Unicode 6.1. Quelle: https://sqlite.org/fts5.html
- Hinweis: Whoosh `LowercaseFilter` verwendet `.lower()` und nicht `.casefold()`. Quelle: https://whoosh.readthedocs.io/en/latest/analysis.html

## Projektregeln
1. Alle internen Strings in NFC normalisieren. Quelle: https://www.unicode.org/reports/tr15/
2. `casefold()` für Suche, **nicht** `lower()`. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold
3. Originaltext immer erhalten. UNSICHER: Projektregel.
4. ASCII-Fallback nur für technische IDs. UNSICHER: Projektregel.
5. Keine NFKC/NFKD auf Inhaltstext. Quelle: https://www.unicode.org/reports/tr15/

## Tests (vorgeschlagen)
```python
normalize_text("Müller") == "Müller"       # NFD zu NFC
search_key("MÜLLER") == search_key("müller")
ascii_fold("Müller") == "mueller"
ascii_fold("Straße") == "strasse"
slugify_de("Müller Straße") == "mueller-strasse"
```

## Quellen
- Unicode UAX #15: https://www.unicode.org/reports/tr15/
- Python `unicodedata`: https://docs.python.org/3/library/unicodedata.html
- Python `str.casefold`: https://docs.python.org/3/library/stdtypes.html#str.casefold
- UnicodeData.txt: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt
- Unicode CaseFolding.txt: https://www.unicode.org/Public/UNIDATA/CaseFolding.txt
- SQLite FTS5: https://sqlite.org/fts5.html
- Whoosh analyzers: https://whoosh.readthedocs.io/en/latest/analysis.html

## Implementierungsstatus (Issue #76)

- Deutsche Query-Fixtures existieren in `tests/fixtures/german_queries.json`.
- Die Strategie ist abgesichert durch 28 Fixture-Regressionstests für NFC, Search-Key, ASCII-Fold, Slug und Safety.
- Zusätzlich gibt es 16 Report-Evaluationstests mit deutschen Umlauten.
- Eine optionale Live-Evaluation ist über `make research-evaluate-german` verfügbar.
