# Umlaut Search and Slug Policy

## Stand
2026-05-20

## Ziel
Konkrete Implementierungsregeln für deutsche Umlaute in Suche, Slugs und Dateinamen.

## Aktuelle Implementierung

- Die konkrete Implementierung liegt in `text_utils/german.py`.
- Dort sind `normalize_nfc`, `normalize_search_key`, `ascii_fold_german`, `slugify_german` und `normalize_markdown_text` verfügbar.
- Verifikation und Regressionstests liegen in `tests/test_german_text_normalization.py`.

## Search Keys
### Primärer Suchschlüssel
```python
def search_key(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()
```

### Warum NFC + casefold?
NFC normalisiert z. B. `a+U+0308` zu `ä`; `casefold()` ermöglicht fallunabhängiges Matching inklusive `ß→ss`. Quellen: https://www.unicode.org/reports/tr15/ , https://docs.python.org/3/library/stdtypes.html#str.casefold

## ASCII Folding
```python
GERMAN_ASCII_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
    "ß": "ss", "ẞ": "SS",
}

def ascii_fold_de(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    for umlaut, ascii_rep in GERMAN_ASCII_MAP.items():
        text = text.replace(umlaut, ascii_rep)
    return text
```

UNSICHER: Die konkrete `ae/oe/ue/ss`-Zuordnung ist eine deutsche Konvention; sie ist **nicht** Teil der Unicode-Norm. Als reine Unicode-Normalisierung reicht NFKD dafür nicht aus. Quelle: https://www.unicode.org/reports/tr15/

## Slugs
```python
def slugify_de(text: str) -> str:
    text = ascii_fold_de(text)
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
```

Beispiele:
- `Müller Straße` → `mueller-strasse`
- `Ärger` → `aerger`
- `Öl` → `oel`
- `Übergröße` → `uebergroesse`
- `Fußgänger` → `fussgaenger`

## Dateinamen
- Für technische Dateinamen: `slugify_de()` verwenden.
- Für menschenlesbare Titel: Unicode NFC ist erlaubt, aber plattformübergreifend vorsichtig verwenden. Quelle für NFC: https://www.unicode.org/reports/tr15/

## URLs
- Nicht selbst transliterieren.
- `urllib.parse.quote()` für Percent-Encoding verwenden. UNSICHER: konkrete URL-Policy projektabhängig.
- Keine manuelle `ä→ae`-Ersetzung in URLs. UNSICHER: Projektregel.

## JSON / Markdown
- UTF-8-Encoding.
- `json.dump(..., ensure_ascii=False)` für lokale Dateien, wenn der Konsument UTF-8 versteht. UNSICHER: Tool-/Consumer-Kompatibilität.
- Markdown-Dateien als UTF-8 speichern. UNSICHER: Repository-Konvention.

## Do / Don't
### Do
- ✅ NFC für alle internen Strings. Quelle: https://www.unicode.org/reports/tr15/
- ✅ `casefold()` für Suche. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold
- ✅ Originaltext speichern. UNSICHER: Projektregel.
- ✅ ASCII-Fallback nur für technische Identifier. UNSICHER: Projektregel.
- ✅ Tests für alle Umlaut-Fälle. UNSICHER: Qualitätsregel.

### Don't
- ❌ `lower()` für caseless Matching. Quelle: https://docs.python.org/3/library/stdtypes.html#str.casefold
- ❌ NFKC/NFKD auf Inhaltstext. Quelle: https://www.unicode.org/reports/tr15/
- ❌ Umlaute in Reports automatisch transliterieren. UNSICHER: Projektregel.
- ❌ Nur ASCII-Text speichern. UNSICHER: Datenverlust.
- ❌ URLs manuell transliterieren. UNSICHER: Projektregel.

## Testfälle
```python
# Normalisierung
assert normalize_text("Müller") == "Müller"
assert normalize_text("Mu\u0308ller") == "Müller"  # NFD → NFC

# Suche
assert search_key("MÜLLER") == search_key("müller")
assert search_key("Straße") == "strasse"

# ASCII-Folding
assert ascii_fold_de("Müller") == "Mueller"
assert ascii_fold_de("Straße") == "Strasse"
assert ascii_fold_de("ẞ") == "SS"

# Slugs
assert slugify_de("Müller Straße") == "mueller-strasse"
assert slugify_de("Ärger") == "aerger"
assert slugify_de("  Öl  ") == "oel"
assert slugify_de("Übergröße") == "uebergroesse"
assert slugify_de("Fußgänger") == "fussgaenger"
assert slugify_de("ẞ") == "ss"
```

## Quellen
- Unicode UAX #15: https://www.unicode.org/reports/tr15/
- Python `unicodedata`: https://docs.python.org/3/library/unicodedata.html
- Python `str.casefold`: https://docs.python.org/3/library/stdtypes.html#str.casefold
- UnicodeData.txt: https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt
- Unicode CaseFolding.txt: https://www.unicode.org/Public/UNIDATA/CaseFolding.txt
- SQLite FTS5: https://sqlite.org/fts5.html
- Whoosh analyzers: https://whoosh.readthedocs.io/en/latest/analysis.html

## Query-Fixture-Validierung

- `tests/fixtures/german_queries.json` enthält deutsche Query-Fixtures für die Regression.
- Vor der Nutzung werden die Fixtures mit dem Safety-Guard validiert.
- Die Original-Umlaute bleiben in Queries und Reports erhalten; nur technische Ableitungen wie Suchschlüssel oder Slugs dürfen ASCII-Fallback verwenden.
- Die Sicherheitsregeln für diese Fixtures erlauben nur harmlose, generische Sprach- und Konzeptfragen ohne echte Personen, Adressen, Domains oder Security-Inhalte.
- Ausführen der Fixture-Tests:

```bash
python3 -m pytest tests/test_german_query_fixtures.py -q
```

- Für eine Live-Evaluation mit deutschen Queries siehe `make research-evaluate-german`.
