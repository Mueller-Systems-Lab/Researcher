# =============================================================================
# Researcher — German Query Fixture Helpers (Issue #76)
# =============================================================================
# Lädt und validiert deutsche Query-Fixtures für die Research-Evaluation.
# Wiederverwendet den Query-Safety-Guard aus scripts/research_multi_query_eval.py.
# =============================================================================

import json
import os
from typing import TypedDict

# ── TypedDict für Typ-Hints (optional, Python 3.12 kompatibel) ────────────────


class GermanQueryFixture(TypedDict, total=False):
    """Typ für eine deutsche Query-Fixture."""

    id: str
    query: str
    expected_terms: list[str]
    forbidden_terms: list[str]
    ascii_folded: str
    requires_umlaut: bool


# ── Public API ────────────────────────────────────────────────────────────────


def load_german_query_fixtures() -> list[GermanQueryFixture]:
    """Lädt die deutschen Query-Fixtures aus tests/fixtures/german_queries.json.

    Returns:
        Liste von Query-Fixture-Dictionaries.

    Raises:
        FileNotFoundError: Wenn die Fixture-Datei nicht existiert.
        json.JSONDecodeError: Wenn die JSON-Datei ungültig ist.
    """
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "fixtures",
        "german_queries.json",
    )
    with open(fixture_path) as f:
        data: list[GermanQueryFixture] = json.load(f)
    return data


# ── Safety Validation (wiederverwendet) ────────────────────────────────────────


# Blockierte Begriffe — synchron gehalten mit scripts/research_multi_query_eval.py
_BLOCKED_TERMS: set[str] = {
    "exploit",
    "cve",
    "vulnerability",
    "target.com",
    "credential",
    "password dump",
    "darknet",
    "onion forum",
    "person:",
    "site:",
    "malware",
    "ransomware",
}


def validate_german_fixture_safety(query: str) -> str | None:
    """Prüft, ob eine Query sicher/harmlos ist.

    Gibt bei Problemen eine Fehlermeldung zurück, sonst None.

    Der Safety-Guard ist synchron mit dem Guard in:
      - scripts/research_happy_path.py (is_safe_query)
      - scripts/research_multi_query_eval.py (is_safe_query)

    Args:
        query: Der zu prüfende Query-String.

    Returns:
        None wenn die Query sicher ist, sonst einen Fehler-String.
    """
    query_lower = query.casefold()
    for term in _BLOCKED_TERMS:
        if term in query_lower:
            return f"Query enthält blockierten Begriff: '{term}'"
    return None


def get_fixture_count() -> int:
    """Gibt die Anzahl der geladenen Fixtures zurück.

    Returns:
        Anzahl der Fixtures in german_queries.json.
    """
    return len(load_german_query_fixtures())
