# =============================================================================
# Tests: text_utils/german.py — Deutsche Unicode-/Umlaut-Helper (ADR-016)
# =============================================================================
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── normalize_nfc ────────────────────────────────────────────────────────────


def test_normalize_nfc_combining_umlaut():
    """NFD 'a' + combining diaeresis → NFC 'ä'."""
    from text_utils.german import normalize_nfc

    assert normalize_nfc("Mu\u0308ller") == "M\u00fcller"


def test_normalize_nfc_idempotent():
    """NFC ist idempotent: NFC(NFC(x)) == NFC(x)."""
    from text_utils.german import normalize_nfc

    text = "Müller Straße Ärger Öl Übergröße"
    nfc_once = normalize_nfc(text)
    nfc_twice = normalize_nfc(nfc_once)
    assert nfc_once == nfc_twice


def test_normalize_nfc_ascii():
    """ASCII-Text bleibt unverändert."""
    from text_utils.german import normalize_nfc

    assert normalize_nfc("Hello World") == "Hello World"


def test_normalize_nfc_empty():
    """Leerer String bleibt leer."""
    from text_utils.german import normalize_nfc

    assert normalize_nfc("") == ""


# ── normalize_search_key ──────────────────────────────────────────────────────


def test_search_key_casefold_umlauts():
    """casefold erkennt Umlaut-Groß-/Kleinschreibung."""
    from text_utils.german import normalize_search_key

    assert normalize_search_key("MÜLLER") == normalize_search_key("müller")


def test_search_key_sharp_s():
    """casefold wandelt ß → ss für Vergleich."""
    from text_utils.german import normalize_search_key

    assert normalize_search_key("Straße") == "strasse"
    assert normalize_search_key("STRASSE") == normalize_search_key("Straße")


def test_search_key_whitespace():
    """Mehrfache Whitespaces werden normalisiert."""
    from text_utils.german import normalize_search_key

    # casefold konvertiert ß→ss, daher 'strasse' nicht 'straße'
    assert normalize_search_key("  Müller   Straße  ") == "müller strasse"


def test_search_key_preserves_umlauts():
    """Search-Key erhält Umlaute (kein ASCII-Folding)."""
    from text_utils.german import normalize_search_key

    result = normalize_search_key("Ärger Öl Übergröße")
    # Umlaute sollen erhalten bleiben, nur casefold
    assert "ä" in result
    assert "ö" in result
    assert "ü" in result


# ── ascii_fold_german ─────────────────────────────────────────────────────────


def test_ascii_fold_german_umlauts():
    """ä→ae, ö→oe, ü→ue Ersetzung."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Müller Straße") == "Mueller Strasse"


def test_ascii_fold_german_capital_umlauts():
    """Großbuchstaben-Umlaute: Ä→Ae, Ö→Oe, Ü→Ue."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Ärger") == "Aerger"
    assert ascii_fold_german("Öl") == "Oel"
    assert ascii_fold_german("Übergröße") == "Uebergroesse"


def test_ascii_fold_sharp_s():
    """ß→ss Ersetzung."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Fußgänger") == "Fussgaenger"


def test_ascii_fold_capital_sharp_s():
    """ẞ→SS Ersetzung (Unicode U+1E9E)."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("ẞ") == "SS"


def test_ascii_fold_mixed():
    """Mixed Case mit Umlauten."""
    from text_utils.german import ascii_fold_german

    # Ü→Ue (capital U + lowercase e) ohne casefold
    assert ascii_fold_german("MÜLLER") == "MUeLLER"


def test_ascii_fold_no_umlauts():
    """Text ohne Umlaute bleibt unverändert."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Hello World") == "Hello World"


# ── slugify_german ────────────────────────────────────────────────────────────


def test_slugify_german():
    """Slug aus deutschem Text mit Umlauten und Sonderzeichen."""
    from text_utils.german import slugify_german

    assert slugify_german("Müller Straße!") == "mueller-strasse"


def test_slugify_aerger():
    """Ärger → aerger."""
    from text_utils.german import slugify_german

    assert slugify_german("Ärger") == "aerger"


def test_slugify_oel():
    """Öl → oel."""
    from text_utils.german import slugify_german

    assert slugify_german("Öl") == "oel"


def test_slugify_uebergroesse():
    """Übergröße → uebergroesse."""
    from text_utils.german import slugify_german

    assert slugify_german("Übergröße") == "uebergroesse"


def test_slugify_fussgaenger():
    """Fußgänger → fussgaenger."""
    from text_utils.german import slugify_german

    assert slugify_german("Fußgänger") == "fussgaenger"


def test_slugify_trim_whitespace():
    """Whitespace wird getrimmt."""
    from text_utils.german import slugify_german

    assert slugify_german("  Öl  ") == "oel"


def test_slugify_special_chars():
    """Sonderzeichen werden durch '-' ersetzt."""
    from text_utils.german import slugify_german

    slug = slugify_german("test!@#$%^&*()query")
    # Sollte kein !@#$ enthalten
    for char in "!@#$%^&*()":
        assert char not in slug


def test_slugify_no_path_separators():
    """Keine Pfadseparatoren im Slug."""
    from text_utils.german import slugify_german

    slug = slugify_german("../../../etc/passwd")
    assert "/" not in slug
    assert ".." not in slug or slug.startswith("etc")


def test_slugify_max_length():
    """Slug wird auf max_length gekürzt."""
    from text_utils.german import slugify_german

    long_text = "ä" * 200
    slug = slugify_german(long_text, max_length=50)
    assert len(slug) <= 50


def test_slugify_empty_string():
    """Leerer String gibt 'untitled' zurück."""
    from text_utils.german import slugify_german

    assert slugify_german("") == "untitled"


def test_slugify_only_special_chars():
    """Nur Sonderzeichen → 'untitled'."""
    from text_utils.german import slugify_german

    assert slugify_german("!@#$%") == "untitled"


def test_slugify_allows_dots_and_underscores():
    """Punkte und Unterstriche sind in Slugs erlaubt."""
    from text_utils.german import slugify_german

    slug = slugify_german("file.name_v2")
    assert "." in slug or "_" in slug


def test_slugify_sharp_s():
    """ẞ → ss im Slug."""
    from text_utils.german import slugify_german

    assert slugify_german("ẞ") == "ss"


# ── normalize_markdown_text ────────────────────────────────────────────────────


def test_markdown_keeps_umlauts():
    """Markdown-Normalisierung erhält Umlaute."""
    from text_utils.german import normalize_markdown_text

    assert normalize_markdown_text("Übergröße Straße") == "Übergröße Straße"


def test_markdown_no_ascii_fold():
    """Kein ASCII-Folding in Markdown-Text."""
    from text_utils.german import normalize_markdown_text

    result = normalize_markdown_text("Müller Straße")
    assert "Müller" in result
    assert "Mueller" not in result


def test_markdown_nfc_normalization():
    """NFD wird zu NFC normalisiert."""
    from text_utils.german import normalize_markdown_text

    # NFD: a + combining diaeresis
    result = normalize_markdown_text("Mu\u0308ller")
    assert result == "M\u00fcller"


def test_markdown_trim_whitespace():
    """Führende/nachfolgende Whitespaces werden getrimmt."""
    from text_utils.german import normalize_markdown_text

    assert normalize_markdown_text("  Müller  ") == "Müller"


def test_markdown_empty_string():
    """Leerer String bleibt leer."""
    from text_utils.german import normalize_markdown_text

    assert normalize_markdown_text("") == ""


# ── Integration / Edge Cases ──────────────────────────────────────────────────


def test_integration_mueller_search():
    """Integration: Müller in verschiedenen Formen suchen."""
    from text_utils.german import normalize_search_key

    variants = [
        "Müller",
        "MÜLLER",
        "müller",
        "Mu\u0308ller",  # NFD: M u + combining diaeresis l l e r
    ]
    keys = [normalize_search_key(v) for v in variants]
    # Alle sollten den gleichen Suchschlüssel ergeben
    assert len(set(keys)) == 1


def test_integration_strasse_search():
    """Integration: Straße/Strasse/STRASSE Suche."""
    from text_utils.german import normalize_search_key

    assert normalize_search_key("Straße") == "strasse"
    assert normalize_search_key("STRASSE") == "strasse"
    assert normalize_search_key("Strasse") == "strasse"
