# ADR-016: German Unicode Normalization Strategy

**Status:** Proposed  
**Date:** 2026-05-20  
**Deciders:** Architecture Review Agent  
**Context:** Deutsche Textnormalisierung für Reports, Suche, Slugs, Dateinamen, JSON und URLs

---

## Context

Das Researcher-Projekt verarbeitet deutschsprachige Research-Reports, Suchanfragen, Quellenmetadaten und lokale Dateipfade. Deutsche Texte enthalten Umlaute (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`), scharfes s (`ß`) und großes scharfes s (`ẞ`). Diese Zeichen können in Unicode unterschiedlich repräsentiert werden, zum Beispiel als vorkomponierte NFC-Zeichen oder als decomposed Sequenzen in NFD (`a` + U+0308 → `ä`).

Zusätzlich nutzt das Projekt lokale Suchindizes. Aktuell ist Whoosh im Bestand; gemäß ADR-014 ist SQLite FTS5 als Ziel vorgesehen. Beide Suchsysteme haben eigene Tokenizer-/Analyzer-Regeln. Für Slugs, Dateinamen, JSON und URLs braucht das Projekt außerdem eine konsistente Regel, wann Originaltext erhalten bleibt und wann ASCII-Fallbacks erlaubt sind.

Die Normalisierung muss folgende Ziele erfüllen:

- Deutsche Originaltexte in Reports dürfen nicht beschädigt oder transliteriert werden.
- Such- und Vergleichsoperationen müssen `Müller`, `Mu\u0308ller`, `MÜLLER`, `Straße` und `STRASSE` konsistent behandeln.
- Slugs und technische Dateinamen müssen portabel und sicher sein.
- URLs müssen korrekt percent-encoded werden, ohne manuelle Umlaut-Ersetzung.
- Kompatibilitätsnormalisierung darf keine semantischen Unterschiede in Inhaltstexten entfernen.

## Decision

### 1. Interne Textnormalisierung

Alle intern gespeicherten und verglichenen Strings werden in Unicode **NFC (Normalization Form C)** normalisiert.

NFC ist die primäre Projektform, weil sie kanonisch äquivalente Darstellungen zusammenführt und decomposed Sequenzen wie `a + U+0308` zu `ä` komponiert.

### 2. Caseless Matching

Für fallunabhängige Vergleiche wird Python `str.casefold()` verwendet, nicht `str.lower()`.

`casefold()` ist für caseless Matching vorgesehen und behandelt deutsche Sonderfälle korrekt:

- `ß` → `ss`
- `ẞ` → `ss`
- `Straße` → `strasse`

### 3. Anzeige und Reports

Report- und Display-Text bleibt im Original mit Umlauten erhalten. Es gibt keine automatische Umwandlung `ä→ae`, `ö→oe`, `ü→ue` oder `ß→ss` in lesbarem Inhaltstext. Ausgabe erfolgt in UTF-8.

### 4. Search Keys

Primärer Suchschlüssel ist:

```python
unicodedata.normalize("NFC", text).casefold()
```

Optional darf ein sekundäres ASCII-Fallback-Feld verwendet werden:

- `ä` → `ae`
- `ö` → `oe`
- `ü` → `ue`
- `Ä` → `Ae`
- `Ö` → `Oe`
- `Ü` → `Ue`
- `ß` → `ss`
- `ẞ` → `SS`

Dieses ASCII-Feld ist nur ein zusätzlicher Suchfallback. Der Originaltext bleibt immer gespeichert.

### 5. Slugs und Dateinamen

Technische Slugs und portable Dateinamen verwenden zuerst deutsche ASCII-Transliteration, dann `casefold()`, dann einen Safe-Character-Filter:

```text
[a-z0-9._-]
```

Beispiele:

- `Müller Straße` → `mueller-strasse`
- `Übergröße` → `uebergroesse`
- `Fußgänger` → `fussgaenger`

### 6. URLs

URLs werden mit Standardbibliothek-Funktionen wie `urllib.parse.quote()` percent-encoded. Es gibt keine manuelle Umlaut-Substitution in URLs.

### 7. JSON und lokale Dateien

Lokale JSON-Dateien werden als UTF-8 geschrieben. Für JSON-Serialisierung gilt `ensure_ascii=False`, sofern der Konsument UTF-8 unterstützt.

### 8. Niemals-Regeln

- NFKC/NFKD werden nicht blind auf Inhaltstext angewendet, weil Kompatibilitätsnormalisierung semantische Unterschiede entfernen kann.
- Das Projekt speichert niemals nur ASCII-gefalteten Text, weil dadurch Originalinformationen verloren gehen.
- `lower()` wird nicht als Basis für Suchschlüssel verwendet.

## Alternatives Considered

### Alternative A: NFC + casefold + optionaler deutscher ASCII-Fallback

- **Pros:** Bewahrt Originaltext; unterstützt kanonische Unicode-Äquivalenz; behandelt `ß`/`ẞ` korrekt; trennt Anzeige, Suche und Slugs sauber; kompatibel mit Python-Standardbibliothek.
- **Cons:** Benötigt Helper-Funktionen und Tests; Suchindizes wie Whoosh/SQLite FTS5 haben eigene Normalisierungsregeln, die zusätzlich beachtet werden müssen.
- **Decision:** Gewählt. Diese Alternative bietet die beste Balance aus Korrektheit, Datenbewahrung und Implementierbarkeit.

### Alternative B: Alles in ASCII transliterieren

- **Pros:** Einfache Slugs und Dateinamen; viele technische Systeme kommen mit ASCII gut zurecht.
- **Cons:** Datenverlust; Reports wirken unnatürlich; Namen und Fachbegriffe können verfälscht werden; `Müller` und `Mueller` sind nicht immer semantisch identisch.
- **Decision:** Abgelehnt für Inhaltstext. ASCII-Folding ist nur als technischer Fallback für Slugs und sekundäre Suchfelder erlaubt.

### Alternative C: `lower()` statt `casefold()`

- **Pros:** Weit verbreitet und einfach; viele bestehende Analyzer nutzen Lowercase-Filter.
- **Cons:** Behandelt deutsches `ß` nicht wie `casefold()`; führt zu Matching-Lücken zwischen `Straße`, `STRASSE` und `ẞ`; schlechtere Unicode-Konformität für caseless Matching.
- **Decision:** Abgelehnt. `casefold()` ist die Projektregel für fallunabhängige Vergleiche.

### Alternative D: NFKC/NFKD für alle Texte

- **Pros:** Vereinheitlicht zusätzlich Kompatibilitätszeichen; kann für technische Identifier nützlich sein.
- **Cons:** Entfernt potentiell semantische und typografische Unterschiede; Unicode UAX #15 warnt vor blindem Einsatz auf beliebigem Text; Risiko für Inhaltstreue in Reports.
- **Decision:** Abgelehnt für Inhaltstext. Nur gezielte technische Sonderfälle dürfen separat entschieden werden.

## Consequences

### Positive

- Deutsche Zeichen bleiben in Reports und Display-Ausgaben korrekt erhalten.
- NFC verhindert Unterschiede zwischen precomposed und decomposed Unicode-Formen.
- `casefold()` verbessert deutsche caseless Suche gegenüber `lower()`.
- Slugs und technische Dateinamen werden portabel und reproduzierbar.
- Originaltext und Such-/Slug-Ableitungen sind klar getrennt.

### Negative

- SQLite FTS5 `unicode61` entfernt Diakritika standardmäßig; die Konfiguration muss bewusst gewählt und getestet werden.
- Whoosh `LowercaseFilter` verwendet `.lower()` und nicht `.casefold()`; dadurch können Matching-Unterschiede für `ß` entstehen.
- Helper-Funktionen wie `nfc()`, `search_key()`, `ascii_fold_de()` und `slugify_de()` müssen implementiert und zentral genutzt werden.
- Bestehende Indizes müssen nach Einführung der neuen Normalisierung ggf. neu aufgebaut werden.

### Risiken

| Risiko | Impact | Mitigation |
|---|---|---|
| FTS5 entfernt Diakritika unerwartet | Suchergebnisse unterscheiden sich von Projekt-Search-Key | `unicode61 remove_diacritics` bewusst konfigurieren und dokumentieren; Parity-Tests |
| Whoosh nutzt `lower()` | `Straße`/`STRASSE`-Mismatch | Eigene Normalisierungsfelder oder Analyzer-Anpassung; Migration zu SQLite FTS5 berücksichtigen |
| ASCII-Folding überschreibt Originaltext | Datenverlust | Originaltext immer speichern; ASCII nur als abgeleitetes Feld |
| Manuelle URL-Umlautersetzung | Fehlerhafte URLs | `urllib.parse.quote()` verwenden; Tests für URLs mit Umlauten |
| NFKC/NFKD auf Reports | Verlust semantischer Unterschiede | Niemals-Regel und Tests für Inhaltstext |

## Migration Path

1. **Helper-Funktionen einführen**
   - `nfc(text: str) -> str`
   - `search_key(text: str) -> str`
   - `ascii_fold_de(text: str) -> str`
   - `slugify_de(text: str) -> str`

2. **Storage- und Suchfelder trennen**
   - `original_text`: unveränderter bzw. NFC-normalisierter Inhalt für Anzeige.
   - `normalized_text`: NFC + `casefold()` für Matching.
   - `ascii_folded_text`: optionaler deutscher ASCII-Fallback.

3. **Suchindex-Konfiguration prüfen**
   - SQLite FTS5 `unicode61` und `remove_diacritics` explizit konfigurieren.
   - Whoosh-Verhalten mit `LowercaseFilter` dokumentieren und durch Tests absichern.

4. **Tests ergänzen**
   - NFC/NFD-Äquivalenz: `Müller` vs. `Mu\u0308ller`.
   - Casefold: `Straße`, `STRASSE`, `ẞ`.
   - Slugs: `Müller Straße`, `Übergröße`, `Fußgänger`.
   - JSON: UTF-8 und `ensure_ascii=False`.
   - URL-Encoding mit `urllib.parse.quote()`.

5. **Indizes rebuilden**
   - Bestehende lokale Suchindizes nach Einführung der Normalisierungsfelder neu erstellen.

## Architecture Review Checklist

- [x] New dependency justified? **Keine neue Dependency; Python-stdlib `unicodedata`, `re`, `json`, `urllib.parse` reichen aus.**
- [x] Module coupling acceptable? **Zentrale Helper reduzieren verstreute Normalisierungslogik.**
- [x] Data flow documented and secure? **Originaltext bleibt erhalten; abgeleitete Such-/Slug-Felder werden lokal erzeugt.**
- [x] Error handling strategy consistent? **Helper sollen `None` nicht stillschweigend als Text interpretieren; Aufrufer validieren Eingaben.**
- [x] Scaling bottlenecks identified? **Normalisierung ist CPU-leicht; Index-Rebuild ist der relevante Migrationsaufwand.**
- [x] Security boundaries clearly defined? **Dateinamen/Slugs filtern unsichere Zeichen; URLs werden standardkonform percent-encoded.**
- [x] Testing strategy adequate? **Umlaut-, `ß`/`ẞ`-, NFC/NFD-, JSON-, URL- und FTS-Tests erforderlich.**

## References

- `docs/text/unicode-german-strategy.md` — Deutsche Unicode-Strategie.
- `docs/text/umlaut-search-and-slug-policy.md` — Umlaut-Suche und Slug-Regeln.
- `docs/adr/ADR-014-whoosh-migration.md` — SQLite FTS5 als Ziel für Suchindex-Migration.
- Unicode UAX #15: <https://www.unicode.org/reports/tr15/>
- Python `unicodedata`: <https://docs.python.org/3/library/unicodedata.html>
- Python `str.casefold`: <https://docs.python.org/3/library/stdtypes.html#str.casefold>
- UnicodeData.txt: <https://unicode.org/Public/UCD/latest/ucd/UnicodeData.txt>
- Unicode CaseFolding.txt: <https://www.unicode.org/Public/UNIDATA/CaseFolding.txt>
- SQLite FTS5: <https://sqlite.org/fts5.html>
- Whoosh Analysis: <https://whoosh.readthedocs.io/en/latest/analysis.html>
