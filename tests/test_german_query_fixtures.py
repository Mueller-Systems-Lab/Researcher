# =============================================================================
# Tests: Deutsche Query-Fixtures + Regression (Issue #76)
# =============================================================================
# Prüft deutsche Umlaut-Queries auf:
#   - NFC-Normalisierung
#   - Search-Key-Stabilität (casefold)
#   - ASCII-Folding (ä→ae etc.)
#   - Slug-Sicherheit
#   - Safety-Guard-Validierung
#   - Original-Umlauterhalt
# =============================================================================
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixture Loading ───────────────────────────────────────────────────────────


def test_load_all_fixtures():
    """Alle Fixtures aus german_queries.json laden."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    assert len(fixtures) >= 4, f"Erwartet ≥4 Fixtures, gefunden: {len(fixtures)}"
    ids = {f["id"] for f in fixtures}
    assert "de-footpath-sharp-s" in ids
    assert "de-oversize-umlaut" in ids
    assert "de-muellerstrasse-example" in ids


def test_fixtures_have_required_fields():
    """Jede Fixture hat mindestens id, query, expected_terms."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        assert f.get("id"), f"Fixture ohne id: {f}"
        assert f.get("query"), f"Fixture {f.get('id')} ohne query"
        assert f.get("expected_terms"), f"Fixture {f.get('id')} ohne expected_terms"


def test_fixtures_requires_umlaut_flag():
    """Fixtures mit Umlauten haben requires_umlaut=true."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    umlaut_ids = {
        "de-footpath-sharp-s",
        "de-oversize-umlaut",
        "de-muellerstrasse-example",
    }
    for f in fixtures:
        if f["id"] in umlaut_ids:
            assert f.get("requires_umlaut") is True, (
                f"{f['id']} muss requires_umlaut=true haben"
            )
        elif f.get("requires_umlaut") is True:
            # Optional: Fixtures ohne Umlaute sollten kein requires_umlaut setzen
            pass


# ── NFC Normalization ─────────────────────────────────────────────────────────


def test_all_queries_are_nfc_normalized():
    """Alle Queries sind in NFC-Normalform."""
    import unicodedata

    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        query = f["query"]
        nfc = unicodedata.normalize("NFC", query)
        assert query == nfc, f"{f['id']}: Query nicht in NFC: {query!r} != {nfc!r}"


def test_nfc_preserves_umlauts():
    """NFC-Normalisierung verändert Umlaute nicht sichtbar."""
    from text_utils.german import normalize_nfc

    texts = [
        "Übergröße",
        "Fußgängerzone",
        "Müllerstraße",
        "Ärger",
        "Öl",
    ]
    for text in texts:
        result = normalize_nfc(text)
        assert result == text, f"NFC hat '{text}' zu '{result}' verändert"


def test_nfd_to_nfc_conversion():
    """NFD-kodierte Umlaute werden zu NFC kombiniert."""
    from text_utils.german import normalize_nfc

    # NFD: a + combining diaeresis = 'ä' in NFD
    assert normalize_nfc("Mu\u0308ller") == "M\u00fcller"
    assert normalize_nfc("gro\u0308\u00dfe") == "gr\u00f6\u00dfe"


# ── Search-Key Stability ──────────────────────────────────────────────────────


def test_search_key_stable_for_umlaut_queries():
    """normalize_search_key() ist stabil für deutsche Queries."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.german import normalize_search_key

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        key1 = normalize_search_key(f["query"])
        key2 = normalize_search_key(f["query"])
        assert key1 == key2, f"{f['id']}: Search-Key nicht stabil: {key1!r} != {key2!r}"
        # Der Key sollte NICHT leer sein
        assert len(key1) > 0, f"{f['id']}: Search-Key ist leer"


def test_search_key_casefold_umlauts_in_queries():
    """casefold() erkennt Groß-/Kleinschreibung von Umlauten."""
    from text_utils.german import normalize_search_key

    # Übergröße → übergrösse (casefold) — ist korrekt für Suche
    assert normalize_search_key("Übergröße") == "übergrösse"
    # Groß- und Kleinschreibung vergleichbar
    assert normalize_search_key("FUSSGÄNGERZONE") == normalize_search_key(
        "fußgängerzone"
    )


def test_search_key_sharp_s_in_queries():
    """ß → ss im Search-Key (casefold-Eigenschaft)."""
    from text_utils.german import normalize_search_key

    assert normalize_search_key("Straße") == "strasse"
    assert normalize_search_key("Fußgängerzone") == "fussgängerzone"


def test_search_key_whitespace_in_queries():
    """Mehrfache Whitespaces werden im Search-Key normalisiert."""
    from text_utils.german import normalize_search_key

    assert normalize_search_key("  Über  Größe  ") == "über grösse"


# ── ASCII-Folding ─────────────────────────────────────────────────────────────


def test_ascii_fold_matches_expected():
    """ASCII-Folding liefert die erwarteten Fallback-Werte aus den Fixtures."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.german import ascii_fold_german

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        if "ascii_folded" in f:
            result = ascii_fold_german(f["query"])
            assert result == f["ascii_folded"], (
                f"{f['id']}: ASCII-Fold '{result}' != erwartet '{f['ascii_folded']}'"
            )


def test_ascii_fold_ae_oe_ue():
    """Umlaute werden korrekt zu ae/oe/ue gefaltet."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Müller") == "Mueller"
    assert ascii_fold_german("Öl") == "Oel"
    assert ascii_fold_german("Über") == "Ueber"
    assert ascii_fold_german("Fußgänger") == "Fussgaenger"


def test_ascii_fold_capital_umlauts():
    """Großbuchstaben-Umlaute: Ä→Ae, Ö→Oe, Ü→Ue (ohne casefold)."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Ärger") == "Aerger"
    assert ascii_fold_german("MÜLLER") == "MUeLLER"


def test_ascii_fold_sharp_s_and_capital_sharp_s():
    """ß→ss und ẞ→SS."""
    from text_utils.german import ascii_fold_german

    assert ascii_fold_german("Straße") == "Strasse"
    assert ascii_fold_german("\u1e9e") == "SS"  # Capital Sharp S


# ── Slug Generation ───────────────────────────────────────────────────────────


def test_slugify_german_for_all_queries():
    """slugify_german() erzeugt sichere, ASCII-only Slugs für alle Queries."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.german import slugify_german

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        slug = slugify_german(f["query"])
        # Slug muss ASCII-sicher sein
        assert slug.isascii(), f"{f['id']}: Slug enthält Nicht-ASCII: {slug!r}"
        # Keine Pfadseparatoren
        assert "/" not in slug
        assert "\\" not in slug
        # Keine Umlaute
        for umlaut in "äöüÄÖÜßẞ":
            assert umlaut not in slug, (
                f"{f['id']}: Slug enthält Umlaut '{umlaut}': {slug!r}"
            )
        # Keine Leerzeichen
        assert " " not in slug
        # Nicht leer
        assert len(slug) > 0


def test_slugify_known_outputs():
    """Bekannte Slug-Ergebnisse prüfen."""
    from text_utils.german import slugify_german

    assert slugify_german("Müllerstraße") == "muellerstrasse"
    assert slugify_german("Fußgängerzone") == "fussgaengerzone"
    assert slugify_german("Übergröße") == "uebergroesse"


def test_slugify_max_length():
    """Slug wird auf max_length gekürzt."""
    from text_utils.german import slugify_german

    long_query = "Was ist die Müllerstraße " * 10
    slug = slugify_german(long_query, max_length=50)
    assert len(slug) <= 50
    assert slug.isascii()


def test_slugify_special_chars():
    """Sonderzeichen werden durch '-' ersetzt."""
    from text_utils.german import slugify_german

    slug = slugify_german("Test!@#$%^&*()query")
    for char in "!@#$%^&*()":
        assert char not in slug


# ── Safety-Guard ──────────────────────────────────────────────────────────────


def test_all_queries_pass_safety_guard():
    """Alle deutschen Fixture-Queries bestehen den Safety-Guard."""
    from tests.helpers.german_query_fixtures import (
        load_german_query_fixtures,
        validate_german_fixture_safety,
    )

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        error = validate_german_fixture_safety(f["query"])
        assert error is None, f"{f['id']}: Safety-Guard fehlgeschlagen: {error}"


def test_safety_guard_blocks_forbidden_terms():
    """Safety-Guard blockiert Queries mit verbotenen Begriffen."""
    from tests.helpers.german_query_fixtures import validate_german_fixture_safety

    assert validate_german_fixture_safety("CVE-2024 exploit") is not None
    assert validate_german_fixture_safety("darknet forum onion") is not None
    assert validate_german_fixture_safety("site:target.com") is not None
    assert validate_german_fixture_safety("password dump credentials") is not None


def test_safety_guard_case_insensitive():
    """Safety-Guard prüft case-insensitive."""
    from tests.helpers.german_query_fixtures import validate_german_fixture_safety

    assert validate_german_fixture_safety("EXPLOIT") is not None
    assert validate_german_fixture_safety("Darknet") is not None


def test_no_fixture_contains_forbidden_terms():
    """Keine Fixtures enthalten verbotene Begriffe (strukturelle Prüfung)."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    for f in fixtures:
        if "forbidden_terms" in f:
            query_lower = f["query"].casefold()
            for forbidden in f["forbidden_terms"]:
                assert forbidden.casefold() not in query_lower, (
                    f"{f['id']}: Verboten '{forbidden}': {f['query']}"
                )


# ── Original Umlaut Preservation ──────────────────────────────────────────────


def test_original_umlauts_preserved_in_queries():
    """Die Original-Queries in den Fixtures behalten Umlaute."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures

    fixtures = load_german_query_fixtures()
    umlaut_fixtures = {
        "de-footpath-sharp-s": "ß",
        "de-oversize-umlaut": "Ü",
        "de-muellerstrasse-example": "ü",
    }
    for f in fixtures:
        if f["id"] in umlaut_fixtures:
            expected_char = umlaut_fixtures[f["id"]]
            assert expected_char in f["query"], (
                f"{f['id']}: Umlaut '{expected_char}' nicht in Query: {f['query']}"
            )


def test_umlaut_queries_remain_readable_after_nfc():
    """Nach NFC-Normalisierung sind Umlaute weiterhin lesbar."""
    from text_utils.german import normalize_nfc

    queries = [
        "Was ist eine Fußgängerzone?",
        "Was bedeutet Übergröße?",
        "Was ist die Müllerstraße als Wortbeispiel?",
    ]
    for q in queries:
        result = normalize_nfc(q)
        assert result == q, f"'{q}' wurde durch NFC verändert: '{result}'"
        for umlaut in "äöüÄÖÜß":
            if umlaut in q:
                assert umlaut in result, f"'{umlaut}' fehlt nach NFC in: {result}"


# ── Cross-Comparison (ASCII-Fallback vs Search-Key) ───────────────────────────


def test_ascii_fallback_matches_search_key_for_mueller():
    """ASCII-Fallback 'mueller' kann mit search_key('müller') verglichen werden."""
    from text_utils.german import ascii_fold_german, normalize_search_key

    # casefold von 'Müller' → 'müller' (Umlaut erhalten)
    _search_muller = normalize_search_key("Müller")
    assert "müller" in _search_muller
    # ASCII-Fold von 'Müller' → 'mueller'
    ascii_mueller = ascii_fold_german("Müller").casefold()

    # Search-Key von 'mueller' soll zum ASCII-Fold passen
    assert normalize_search_key(ascii_mueller) == normalize_search_key("mueller")

    # ASCII-Fold von 'Müller' vergleichbar mit Eingabe 'mueller'
    assert ascii_mueller == "mueller"


def test_ascii_fallback_matches_for_strasse():
    """ASCII-Fallback 'strasse' passt zu search_key('straße')."""
    from text_utils.german import normalize_search_key

    # casefold von 'Straße' → 'strasse'
    assert normalize_search_key("Straße") == "strasse"
    # Direkte Eingabe 'strasse' → 'strasse'
    assert normalize_search_key("Strasse") == "strasse"
    # Beide sind gleich
    assert normalize_search_key("Straße") == normalize_search_key("Strasse")


# ── Edge Cases ────────────────────────────────────────────────────────────────


def test_empty_query_handling():
    """Leere Query-Strings werden von Helfern korrekt behandelt."""
    from text_utils.german import normalize_nfc, normalize_search_key, slugify_german

    assert normalize_nfc("") == ""
    assert normalize_search_key("") == ""
    assert slugify_german("") == "untitled"


def test_fixture_count():
    """Fixture-Count-Funktion funktioniert."""
    from tests.helpers.german_query_fixtures import get_fixture_count

    count = get_fixture_count()
    assert count >= 4, f"Erwartet ≥4 Fixtures, gefunden: {count}"


# ── Search-Key Integration (Issue #77) ────────────────────────────────────────


def test_german_fixtures_have_search_keys():
    """Jede Fixture kann in GermanSearchKeys umgewandelt werden."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.search_keys import build_german_search_keys

    for fixture in load_german_query_fixtures():
        keys = build_german_search_keys(fixture["query"])

        assert keys.original == fixture["query"], (
            f"{fixture['id']}: Original nicht erhalten"
        )
        assert keys.normalized, f"{fixture['id']}: normalized ist leer"
        assert keys.ascii_folded, f"{fixture['id']}: ascii_folded ist leer"


def test_german_fixture_ascii_folded_matches_policy():
    """ascii_folded in Fixtures entspricht ascii_fold_german()."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.german import ascii_fold_german

    for fixture in load_german_query_fixtures():
        if "ascii_folded" in fixture:
            assert ascii_fold_german(fixture["query"]) == fixture["ascii_folded"], (
                f"{fixture['id']}: ascii_fold_german != fixture.ascii_folded"
            )


def test_german_fixture_ids_are_slug_safe():
    """Fixture-IDs sind slug-safe (keine Pfadseparatoren)."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.german import slugify_german

    for fixture in load_german_query_fixtures():
        slug = slugify_german(fixture["id"])

        assert slug == fixture["id"], f"{fixture['id']}: Slug '{slug}' != ID"
        assert "/" not in slug
        assert "\\" not in slug


def test_expected_terms_match_example_text():
    """expected_terms matchen via german_query_matches_text()."""
    from tests.helpers.german_query_fixtures import load_german_query_fixtures
    from text_utils.search_keys import german_query_matches_text

    for fixture in load_german_query_fixtures():
        example_text = " ".join(fixture["expected_terms"])

        for term in fixture["expected_terms"]:
            assert german_query_matches_text(term, example_text), (
                f"{fixture['id']}: term '{term}' nicht in '{example_text}'"
            )
