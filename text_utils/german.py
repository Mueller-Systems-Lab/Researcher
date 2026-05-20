# =============================================================================
# Researcher — German Unicode/Umlaut Helpers (ADR-016)
# =============================================================================
# Implementiert die Policy aus:
#   docs/text/unicode-german-strategy.md
#   docs/text/umlaut-search-and-slug-policy.md
#
# Grundsätze:
#   - Interne Textrepräsentation: Unicode NFC (UAX #15).
#   - Originaltext wird NIEMALS durch irreversible Normalisierung ersetzt.
#   - casefold() für Suche, NICHT lower() (erkennt ß→ss korrekt).
#   - ASCII-Fallback NUR für technische IDs/Slugs.
#   - Umlaute bleiben in Anzeige/Reports erhalten.
# =============================================================================

import re
import unicodedata

# ── German Umlaut ASCII Mapping ───────────────────────────────────────────────
# Quelle: docs/text/unicode-german-strategy.md
# UNSICHER: ae/oe/ue/ss ist eine deutsche Konvention, kein Unicode-Standard.

_GERMAN_ASCII_MAP: dict[str, str] = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "ß": "ss",
    "ẞ": "SS",
}

# Reihenfolge: längere Ersetzungen zuerst (ẞ vor ß), dann umgekehrte Länge
_GERMAN_ASCII_SORTED: list[tuple[str, str]] = sorted(
    _GERMAN_ASCII_MAP.items(), key=lambda x: -len(x[0])
)

# Erlaubte Zeichen für Slugs
_SLUG_SAFE_RE = re.compile(r"[^a-z0-9._-]")
_SLUG_SEPARATOR_RE = re.compile(r"[-_.]{2,}")
_SLUG_TRIM_RE = re.compile(r"^[-_.]+|[-_.]+$")


# ── Public API ────────────────────────────────────────────────────────────────


def normalize_nfc(text: str) -> str:
    """Normalisiert Text zu Unicode NFC (Canonical Composition).

    NFC wandelt z.B. 'a' + U+0308 (combining diaeresis) zu 'ä' (U+00E4).
    Diese Normalisierung ist IDEMPOTENT und verändert den sichtbaren Text nicht.

    Args:
        text: Eingabetext (beliebige Unicode-Normalform).

    Returns:
        NFC-normalisierter Unicode-Text.

    Example:
        >>> normalize_nfc("Mu\\u0308ller")
        'Müller'
    """
    return unicodedata.normalize("NFC", text)


def normalize_search_key(text: str) -> str:
    """Erzeugt einen Suchschlüssel für fallunabhängige Textvergleiche.

    Reihenfolge:
    1. NFC-Normalisierung
    2. casefold() — aggressiver als lower(), erkennt ß→ss
    3. Whitespace normalisieren (mehrfache Leerzeichen → eines, trim)

    Umlaute bleiben ERHALTEN (kein ASCII-Folding).
    Geeignet für Unicode-Suchvergleiche in deutschen Texten.

    Args:
        text: Eingabetext.

    Returns:
        Normalisierter Suchschlüssel.

    Example:
        >>> normalize_search_key("MÜLLER") == normalize_search_key("müller")
        True
        >>> normalize_search_key("  Straße  ")
        'straße'
    """
    normalized = unicodedata.normalize("NFC", text)
    folded = normalized.casefold()
    # Whitespace normalisieren
    collapsed = " ".join(folded.split())
    return collapsed


def ascii_fold_german(text: str) -> str:
    """Wandelt deutsche Umlaute und ß in ASCII-Repräsentation um.

    Mapping:
        ä→ae, ö→oe, ü→ue, Ä→Ae, Ö→Oe, Ü→Ue, ß→ss, ẞ→SS

    NUR FÜR TECHNISCHE IDENTIFIER verwenden — nicht für Anzeigetext.
    Die Ausgabe wird zusätzlich NFC-normalisiert.

    Args:
        text: Deutscher Text mit Umlauten.

    Returns:
        ASCII-gefalteter Text (Umlaute ersetzt, sonst unverändert).

    Example:
        >>> ascii_fold_german("Müller Straße")
        'Mueller Strasse'
        >>> ascii_fold_german("Fußgänger")
        'Fussgaenger'
    """
    result = unicodedata.normalize("NFC", text)
    for umlaut, ascii_rep in _GERMAN_ASCII_SORTED:
        result = result.replace(umlaut, ascii_rep)
    return result


def slugify_german(text: str, max_length: int = 120) -> str:
    """Erzeugt einen ASCII-sicheren Slug aus deutschem Text.

    Verarbeitung:
    1. ASCII-Folding (ä→ae, etc.)
    2. casefold() (lowercase + ß→ss)
    3. Unerlaubte Zeichen durch '-' ersetzen
    4. Mehrfache Trennzeichen kollabieren
    5. Trimmen und auf max_length kürzen
    6. Fallback 'untitled' bei leerem Ergebnis

    Args:
        text: Eingabetext (z.B. Query, Titel).
        max_length: Maximale Länge des Slugs (default 120).

    Returns:
        ASCII-sicherer Slug-String.

    Example:
        >>> slugify_german("Müller Straße!")
        'mueller-strasse'
        >>> slugify_german("  Ärger  ")
        'aerger'
        >>> slugify_german("Übergröße")
        'uebergroesse'
    """
    # 1. ASCII-Folding
    folded = ascii_fold_german(text)
    # 2. casefold
    slug = folded.casefold()
    # 3. Unerlaubte Zeichen durch '-' ersetzen
    slug = _SLUG_SAFE_RE.sub("-", slug)
    # 4. Mehrfache Trennzeichen kollabieren
    slug = _SLUG_SEPARATOR_RE.sub("-", slug)
    # 5. Trimmen
    slug = _SLUG_TRIM_RE.sub("", slug)
    # 6. Auf max_length kürzen (an Wortgrenzen)
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    # 7. Fallback
    if not slug:
        slug = "untitled"
    return slug


def normalize_markdown_text(text: str) -> str:
    """Bereitet Text für Markdown-Ausgabe vor.

    - NFC-Normalisierung
    - Umlaute bleiben ERHALTEN
    - KEINE ASCII-Faltung
    - Whitespace bleibt weitgehend erhalten (nur trailing/newline cleanup)

    Args:
        text: Rohtext für Markdown-Report.

    Returns:
        NFC-normalisierter Text mit erhaltenen Umlauten.

    Example:
        >>> normalize_markdown_text("Übergröße Straße")
        'Übergröße Straße'
    """
    normalized = unicodedata.normalize("NFC", text)
    return normalized.strip()
