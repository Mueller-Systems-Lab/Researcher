# =============================================================================
# Tests: German Search Keys (Issue #77)
# =============================================================================
# Prüft die Search-Key-Helper aus text_utils/search_keys.py:
#   - build_german_search_keys() — Originalerhalt, NFC, ASCII-Fallback
#   - german_search_keys_match() — Müller/Mueller, Straße/Strasse
#   - german_query_matches_text() — Substring-Matching mit Fallback
# =============================================================================

from text_utils.search_keys import (
    build_german_search_keys,
    german_query_matches_text,
    german_search_keys_match,
)

# ── build_german_search_keys ──────────────────────────────────────────────


def test_build_german_search_keys_preserves_original():
    """Originaltext bleibt als Source-of-Truth erhalten."""
    keys = build_german_search_keys("Müller Straße")

    assert keys.original == "Müller Straße"
    assert keys.normalized == "müller strasse"
    assert keys.ascii_folded == "Mueller Strasse"


def test_mueller_matches_müller():
    """ASCII-Fallback 'mueller' matched original 'Müller'."""
    assert german_search_keys_match("Müller", "mueller")


def test_strasse_matches_straße():
    """ASCII-Fallback 'strasse' matched original 'Straße'."""
    assert german_search_keys_match("Straße", "strasse")


def test_uebergroesse_matches_übergröße():
    """ASCII-Fallback 'uebergroesse' matched original 'Übergröße'."""
    assert german_search_keys_match("Übergröße", "uebergroesse")


# ── german_query_matches_text ─────────────────────────────────────────────


def test_query_matches_text_with_ascii_fallback():
    """ASCII-Query 'fussgaengerzone' findet 'Fußgängerzone' im Text."""
    assert german_query_matches_text(
        "fussgaengerzone",
        "Die Fußgängerzone ist autofrei.",
    )


def test_original_text_is_not_replaced():
    """Originaltext in GermanSearchKeys bleibt unverändert."""
    keys = build_german_search_keys("Übergröße")

    assert keys.original == "Übergröße"
    assert keys.original != keys.ascii_folded


def test_combining_umlaut_matches_precomposed_umlaut():
    """Kombinierendes Diaeresis (Mu\u0308ller) matched vorkomponiertes 'Müller'."""
    assert german_search_keys_match("Mu\u0308ller", "Müller")


# ── Umlaut ASCII Variants ─────────────────────────────────────────────────


def test_umlaut_ascii_variants():
    """Alle deutschen Umlaut-ASCII-Fallback-Paare matchen."""
    assert german_search_keys_match("Ärger", "aerger")
    assert german_search_keys_match("Öl", "oel")
    assert german_search_keys_match("Fußgänger", "fussgaenger")


def test_capital_umlaut_ascii_match():
    """Groß-Umlaute matchen ASCII-Fallback (casefold)."""
    assert german_search_keys_match("ÄRGER", "aerger")
    assert german_search_keys_match("ÜBER", "ueber")


def test_sharp_s_ascii_match():
    """ß→ss Matching funktioniert in beide Richtungen."""
    assert german_search_keys_match("Straße", "strasse")
    assert german_search_keys_match("Fuß", "fuss")


# ── Substring Matching ────────────────────────────────────────────────────


def test_query_substring_normalized():
    """Normalisierte Query als Substring im normalisierten Text."""
    assert german_query_matches_text(
        "müller",
        "Müller wohnt in der Müllerstraße.",
    )


def test_query_substring_ascii():
    """ASCII-Query als Substring im ASCII-gefalteten Text."""
    assert german_query_matches_text(
        "mueller",
        "Müller wohnt in der Müllerstraße.",
    )


def test_full_sentence_matching():
    """Vollständiger Satz matched sich selbst."""
    text = "Was ist eine Fußgängerzone?"
    assert german_query_matches_text(text, text)


# ── Edge Cases ────────────────────────────────────────────────────────────


def test_empty_strings():
    """Leere Strings werden korrekt behandelt."""
    keys = build_german_search_keys("")
    assert keys.original == ""
    assert keys.normalized == ""
    assert keys.ascii_folded == ""

    # Leerer Query matched nichts in nicht-leerem Text
    assert not german_query_matches_text("", "Irgendein Text")
    # Leerer Text matched keine Query
    assert not german_query_matches_text("suche", "")


def test_whitespace_handling():
    """Mehrfache Whitespaces beeinflussen Matching nicht."""
    assert german_search_keys_match("  Müller  ", "Müller")
    assert german_search_keys_match("Müller  Straße", "Müller Straße")


def test_no_false_positives():
    """Ähnliche aber verschiedene Wörter matchen nicht fälschlich."""
    # 'Haus' ≠ 'Maus' (keine Umlaut-Variante)
    assert not german_search_keys_match("Haus", "Maus")
    # 'Müller' ≠ 'Maler' (völlig verschieden)
    assert not german_search_keys_match("Müller", "Maler")


def test_dataclass_is_frozen():
    """GermanSearchKeys ist immutable (frozen dataclass)."""
    keys = build_german_search_keys("test")
    try:
        keys.original = "modified"  # type: ignore[misc]
        assert False, "Frozen dataclass sollte mutation verhindern"
    except Exception:
        pass  # Erwartet: FrozenInstanceError oder ähnlich


def test_idempotent_build():
    """build_german_search_keys ist idempotent."""
    keys1 = build_german_search_keys("Müller Straße")
    keys2 = build_german_search_keys("Müller Straße")

    assert keys1 == keys2
    assert keys1.original == keys2.original
    assert keys1.normalized == keys2.normalized
    assert keys1.ascii_folded == keys2.ascii_folded
