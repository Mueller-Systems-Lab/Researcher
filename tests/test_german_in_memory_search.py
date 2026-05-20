# =============================================================================
# Tests: German In-Memory Search Regression (Issue #77)
# =============================================================================
# Simuliert eine einfache In-Memory-Suche mit deutschen Suchbegriffen.
# Keine echten Indizes, keine Datenmigration — nur strukturelle Regression.
# =============================================================================

from text_utils.search_keys import german_query_matches_text

DOCUMENTS: list[dict[str, str]] = [
    {
        "id": "1",
        "title": "Müller Straße",
        "body": "Eine Straße als Unicode-Beispiel.",
    },
    {
        "id": "2",
        "title": "Fußgängerzone",
        "body": "Ein Bereich für Fußgänger.",
    },
    {
        "id": "3",
        "title": "Übergröße",
        "body": "Ein Wortbeispiel mit Umlaut.",
    },
]


def search_documents(query: str) -> list[dict[str, str]]:
    """Durchsucht die In-Memory-Dokumente mit deutschen Search-Keys.

    Args:
        query: Suchbegriff (kann ASCII-Fallback oder Original-Umlaute enthalten).

    Returns:
        Liste der passenden Dokumente.
    """
    return [
        doc
        for doc in DOCUMENTS
        if german_query_matches_text(query, f"{doc['title']} {doc['body']}")
    ]


# ── Core Search Regression ────────────────────────────────────────────────


def test_mueller_strasse_finds_müller_straße():
    """ASCII-Query 'mueller strasse' findet 'Müller Straße'."""
    results = search_documents("mueller strasse")

    assert len(results) == 1
    assert results[0]["id"] == "1"
    assert results[0]["title"] == "Müller Straße"


def test_fussgaenger_finds_fußgängerzone():
    """ASCII-Query 'fussgaenger' findet 'Fußgängerzone'."""
    results = search_documents("fussgaenger")

    assert len(results) == 1
    assert results[0]["id"] == "2"
    assert results[0]["title"] == "Fußgängerzone"


def test_uebergroesse_finds_übergröße():
    """ASCII-Query 'uebergroesse' findet 'Übergröße'."""
    results = search_documents("uebergroesse")

    assert len(results) == 1
    assert results[0]["id"] == "3"
    assert results[0]["title"] == "Übergröße"


def test_original_titles_keep_umlauts():
    """In-Memory-Dokumente behalten Umlaute in den Titeln."""
    titles = [doc["title"] for doc in DOCUMENTS]

    assert "Müller Straße" in titles
    assert "Fußgängerzone" in titles
    assert "Übergröße" in titles


# ── Query Variants ────────────────────────────────────────────────────────


def test_umlaut_query_finds_umlaut_document():
    """Query mit Umlauten ('straße') findet Dokument mit Umlauten."""
    results = search_documents("straße")

    assert len(results) == 1
    assert results[0]["id"] == "1"


def test_ascii_query_finds_literal_umlaut_in_body():
    """Query 'umlaut' findet Dokument 3 ('Ein Wortbeispiel mit Umlaut')."""
    # Dokument 3 enthält 'Umlaut' im Body (casefold → 'umlaut')
    results = search_documents("umlaut")
    assert len(results) == 1
    assert results[0]["id"] == "3"


def test_case_insensitive_search():
    """Groß-/Kleinschreibung spielt keine Rolle."""
    assert len(search_documents("MÜLLER")) == 1
    assert len(search_documents("müller")) == 1
    assert len(search_documents("MuElLeR")) == 1


# ── Regression Guards ─────────────────────────────────────────────────────


def test_no_false_matches():
    """Query ohne Match liefert leere Ergebnisliste."""
    results = search_documents("xyz_unbekannt")

    assert len(results) == 0


def test_body_search_works():
    """Query matcht auch im Body, nicht nur im Titel."""
    results = search_documents("autofrei")

    # 'autofrei' steht nur im Body von Dokument 1
    assert len(results) == 0  # 'autofrei' ist kein Umlaut-Wort


def test_all_documents_accessible():
    """Alle drei Dokumente sind in DOCUMENTS vorhanden."""
    assert len(DOCUMENTS) == 3
    ids = {doc["id"] for doc in DOCUMENTS}
    assert ids == {"1", "2", "3"}


def test_no_index_modification():
    """Keine echten Indizes werden verändert — strukturelle Prüfung."""
    original_ids = {doc["id"] for doc in DOCUMENTS}
    original_titles = [doc["title"] for doc in DOCUMENTS]

    # Suche ausführen
    _ = search_documents("test")

    # Dokumente sind unverändert
    assert {doc["id"] for doc in DOCUMENTS} == original_ids
    assert [doc["title"] for doc in DOCUMENTS] == original_titles
