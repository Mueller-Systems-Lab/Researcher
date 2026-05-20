# =============================================================================
# Researcher — German Search Keys (Issue #77)
# =============================================================================
# Ergänzende Normalisierungsschicht für deutsche Suchanfragen.
# Baut auf text_utils/german.py auf (ADR-016).
#
# Grundsätze:
#   - Originaltext bleibt UNVERÄNDERT erhalten (Source of Truth).
#   - normalized_text = Unicode NFC + casefold()
#   - ascii_folded_text = deutscher ASCII-Fallback (ä→ae etc.)
#   - Keine irreversible Normalisierung, keine Datenmigration.
#   - Keine Fuzzy Search, kein Ranking — diese Schicht macht nur exaktes Matching.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass

from text_utils.german import ascii_fold_german, normalize_search_key


@dataclass(frozen=True)
class GermanSearchKeys:
    """German Search Key Tuple für eine Text-Eingabe.

    Felder:
        original:       Roher Eingabetext (unverändert).
        normalized:     Unicode NFC + casefold() + Whitespace-Normalisierung.
        ascii_folded:   ASCII-Fallback (ä→ae, ö→oe, ü→ue, ß→ss, ẞ→SS).
    """

    original: str
    normalized: str
    ascii_folded: str


def build_german_search_keys(text: str) -> GermanSearchKeys:
    """Baut alle Search-Key-Varianten für einen deutschen Text.

    Args:
        text: Eingabetext (beliebige Unicode-Normalform).

    Returns:
        GermanSearchKeys mit original, normalized und ascii_folded.
    """
    return GermanSearchKeys(
        original=text,
        normalized=normalize_search_key(text),
        ascii_folded=ascii_fold_german(text),
    )


def german_search_keys_match(left: str, right: str) -> bool:
    """Prüft, ob zwei deutsche Textstrings als Suchbegriffe matchen.

    Matching-Regeln (OR-verknüpft):
        - left.normalized == right.normalized (Unicode-Vergleich)
        - left.ascii_folded.casefold() == right.ascii_folded.casefold() (ASCII-Fallback)

    Args:
        left:  Erster Textstring.
        right: Zweiter Textstring.

    Returns:
        True wenn mindestens eine Matching-Regel zutrifft.
    """
    left_keys = build_german_search_keys(left)
    right_keys = build_german_search_keys(right)

    return (
        left_keys.normalized == right_keys.normalized
        or left_keys.ascii_folded.casefold() == right_keys.ascii_folded.casefold()
    )


def german_query_matches_text(query: str, text: str) -> bool:
    """Prüft, ob eine Query im Suchtext enthalten ist.

    Matching-Regeln (OR-verknüpft):
        - normalized query in normalized text (Unicode-Substring)
        - ascii_folded query in ascii_folded text (ASCII-Fallback-Substring)

    Verwendet casefold() auf dem ASCII-Fallback für caseless Matching.

    Leere Queries matchen NIE ("" in "text" ist immer True in Python).

    Args:
        query: Suchanfrage (z.B. "mueller").
        text:  Zu durchsuchender Text (z.B. "Müller Straße ist...").

    Returns:
        True wenn die Query im Text gefunden wurde.
    """
    # Guard: empty query never matches (Python's "" in "text" is always True)
    if not query or not text:
        return False

    query_keys = build_german_search_keys(query)
    text_keys = build_german_search_keys(text)

    return (
        query_keys.normalized in text_keys.normalized
        or query_keys.ascii_folded.casefold() in text_keys.ascii_folded.casefold()
    )
