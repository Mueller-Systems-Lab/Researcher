# German Search Keys

## Ziel

Ergänzende Normalisierungsschicht für deutsche Suchanfragen im Researcher-Projekt.

## Grundsätze

- **Originaltext bleibt Source of Truth** — keine irreversible Normalisierung
- **`normalized_text`** = Unicode NFC + casefold() + Whitespace-Normalisierung
- **`ascii_folded_text`** = deutscher ASCII-Fallback (ä→ae, ö→oe, ü→ue, ß→ss, ẞ→SS)
- **Keine Datenmigration** — bestehende Indexe bleiben unverändert
- **Keine Fuzzy Search, kein Ranking** — diese Schicht macht nur exaktes Matching

## Datenstruktur

```python
@dataclass(frozen=True)
class GermanSearchKeys:
    original: str       # Roher Eingabetext (unverändert)
    normalized: str     # Unicode NFC + casefold() + Whitespace-Normalisierung
    ascii_folded: str   # ASCII-Fallback (ä→ae, etc.)
```

## Funktionen

### `build_german_search_keys(text: str) -> GermanSearchKeys`

Baut alle Search-Key-Varianten für einen deutschen Text.

### `german_search_keys_match(left: str, right: str) -> bool`

Prüft, ob zwei deutsche Textstrings als Suchbegriffe matchen.

Matching-Regeln (OR-verknüpft):
- `left.normalized == right.normalized` (Unicode-Vergleich)
- `left.ascii_folded.casefold() == right.ascii_folded.casefold()` (ASCII-Fallback)

### `german_query_matches_text(query: str, text: str) -> bool`

Prüft, ob eine Query im Suchtext enthalten ist.

Matching-Regeln (OR-verknüpft):
- `query.normalized in text.normalized` (Unicode-Substring)
- `query.ascii_folded.casefold() in text.ascii_folded.casefold()` (ASCII-Fallback-Substring)

## Mapping-Tabelle

| Umlaut | ASCII-Fallback |
| ------ | -------------- |
| ä      | ae             |
| ö      | oe             |
| ü      | ue             |
| Ä      | Ae             |
| Ö      | Oe             |
| Ü      | Ue             |
| ß      | ss             |
| ẞ      | SS             |

## Matching-Beispiele

| Query (Eingabe)   | Text (Index)         | Match? | Grund                  |
| ----------------- | -------------------- | ------ | ---------------------- |
| Müller            | mueller              | ✅     | ASCII-Fallback         |
| Straße            | strasse              | ✅     | casefold ß→ss          |
| Übergröße         | uebergroesse         | ✅     | ASCII-Fallback         |
| Mu\u0308ller      | Müller               | ✅     | NFC-Normalisierung     |
| fussgaenger       | Fußgängerzone        | ✅     | Substring + Fallback   |

## Abgrenzung zu text_utils/german.py

| Funktion                    | Modul        | Zweck                        |
| --------------------------- | ------------ | ---------------------------- |
| `normalize_nfc()`           | `german.py`  | Reine NFC-Normalisierung     |
| `normalize_search_key()`    | `german.py`  | NFC + casefold + Whitespace  |
| `ascii_fold_german()`       | `german.py`  | ASCII-Fallback (ohne casefold)|
| `build_german_search_keys()`| `search_keys.py` | Alle drei Varianten bündeln |
| `german_search_keys_match()`| `search_keys.py` | Exaktes Matching zweier Strings |
| `german_query_matches_text()`| `search_keys.py`| Substring-Matching          |

## Sicherheitshinweise

- Keine Fuzzy-Search — keine Tippfehler-Toleranz
- Kein Stemming — keine Wortstamm-Reduktion
- Keine Index-Migration — bestehende Daten bleiben unangetastet
- ASCII-Fallback ist eine deutsche Konvention, kein Unicode-Standard — als UNSICHER markiert
