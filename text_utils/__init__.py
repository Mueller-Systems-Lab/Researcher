# =============================================================================
# Researcher — Text Utilities
# =============================================================================
# Deutsche Unicode-/Umlaut-Helper nach ADR-016 und
# docs/text/unicode-german-strategy.md.
#
# Grundsätze:
#   - Originaltext bleibt UNVERÄNDERT erhalten.
#   - Interne Normalisierung: Unicode NFC (normalize_nfc).
#   - Suche: NFC + casefold() (normalize_search_key).
#   - ASCII-Fallback: ä→ae etc. NUR für technische IDs (ascii_fold_german).
#   - Slugs: ASCII-sicher für Dateinamen (slugify_german).
#   - Markdown/Reports: NFC, Umlaute erhalten (normalize_markdown_text).
#   - NIEMALS NFKC/NFKD auf Inhaltstext.
#   - NIEMALS lower() für caseless Matching (casefold() verwenden).
# =============================================================================

from text_utils.german import (
    ascii_fold_german,
    normalize_markdown_text,
    normalize_nfc,
    normalize_search_key,
    slugify_german,
)
from text_utils.search_keys import (
    GermanSearchKeys,
    build_german_search_keys,
    german_query_matches_text,
    german_search_keys_match,
)

__all__ = [
    "normalize_nfc",
    "normalize_search_key",
    "ascii_fold_german",
    "slugify_german",
    "normalize_markdown_text",
    "GermanSearchKeys",
    "build_german_search_keys",
    "german_search_keys_match",
    "german_query_matches_text",
]
