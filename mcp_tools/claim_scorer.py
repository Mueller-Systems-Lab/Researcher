# =============================================================================
# Claim Scorer — Scoring-Logik und Confidence-Berechnung
# =============================================================================
# Getrennt vom Retrieval und Index-Schreiben. Nur für Scoring zuständig.
# =============================================================================

import logging
import re

logger = logging.getLogger(__name__)


def calculate_confidence(
    results: list[dict],
    claim: str,
    max_sources: int = 5,
) -> float:
    """Berechnet den Confidence-Score für einen Claim.

    Args:
        results: Liste von Ergebnis-Dicts (aus retriever).
        claim: Der zu validierende Claim.
        max_sources: Maximale Quellenanzahl (für Normalisierung).

    Returns:
        Confidence-Score zwischen 0.0 und 1.0.
    """
    if not results:
        return 0.0

    # Anzahl-Basierter Score (50% Gewicht)
    source_score = min(1.0, len(results) / max_sources) * 0.5

    # Relevanz-Basierter Score (30% Gewicht)
    relevance = (
        sum(float(r.get("score", 0) or 0) for r in results) / len(results) * 0.3
        if results
        else 0
    )

    # Keyword-Matching in Snippets (20% Gewicht)
    keywords = re.findall(r"\w+", claim.lower())
    keyword_hits = sum(
        1
        for r in results
        for kw in keywords
        if len(kw) > 3 and kw in r.get("snippet", "").lower()
    )
    keyword_score = min(1.0, keyword_hits / max(1, len(keywords))) * 0.2

    confidence = source_score + relevance + keyword_score
    return max(0.0, min(1.0, confidence))


def assess(confidence: float) -> str:
    """Bewertet den Confidence-Score in menschenlesbarer Form.

    Args:
        confidence: Score zwischen 0.0 und 1.0.

    Returns:
        Bewertungs-String.
    """
    if confidence >= 0.7:
        return "gut belegt"
    elif confidence >= 0.4:
        return "teilweise belegt"
    elif confidence >= 0.1:
        return "schwach belegt"
    return "nicht belegt"
