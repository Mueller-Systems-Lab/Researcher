"""Query Decomposer — converts a ResearchNode into structured search queries.

Produces four query categories:
- primary_queries: Direct rephrasing of the node's question
- entity_queries: Keyword-focused queries from extracted entities
- gap_queries: Queries addressing missing context from dependencies
- negative_queries: Exclusion-based queries for contrast/refinement

No content filtering — uncensored research (including security/darknet).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DecomposedQueries:
    """Structured query set produced from a single ResearchNode."""

    node_id: str
    primary_queries: list[str] = field(default_factory=list)
    entity_queries: list[str] = field(default_factory=list)
    gap_queries: list[str] = field(default_factory=list)
    negative_queries: list[str] = field(default_factory=list)
    language: str = "unknown"

    def all_queries(self) -> list[str]:
        """Return all queries as a flat list."""
        return (
            self.primary_queries
            + self.entity_queries
            + self.gap_queries
            + self.negative_queries
        )

    def __len__(self) -> int:
        return len(self.all_queries())


def decompose_node(
    node_id: str,
    question: str,
    *,
    rationale: str = "",
    expected_sources: list[str] | None = None,
    context_from_dependencies: dict[str, str] | None = None,
    language: str = "unknown",
) -> DecomposedQueries:
    """Decompose a single ResearchNode into structured search queries.

    Args:
        node_id: The plan node identifier.
        question: The research sub-question.
        rationale: Why this sub-question is needed.
        expected_sources: Types of sources expected.
        context_from_dependencies: Results from dependency nodes.
        language: Language hint ('de', 'en', or 'unknown').

    Returns:
        DecomposedQueries with categorized search queries.
    """
    result = DecomposedQueries(node_id=node_id, language=language)

    # 1. Primary queries — direct rephrasings of the question
    result.primary_queries = _generate_primary_queries(question, language)

    # 2. Entity queries — keyword-focused
    result.entity_queries = _generate_entity_queries(
        question, expected_sources or [], language
    )

    # 3. Gap queries — address missing context
    if context_from_dependencies:
        result.gap_queries = _generate_gap_queries(
            question, context_from_dependencies, language
        )

    # 4. Negative queries — exclusion/contrast
    result.negative_queries = _generate_negative_queries(question, language)

    return result


# ── Sub-generators ───────────────────────────────────────────────────────


def _generate_primary_queries(question: str, language: str) -> list[str]:
    """Generate primary queries by rephrasing the question."""
    queries = [question.strip()]

    # Add English variant for German questions
    if language == "de" or _looks_german(question):
        queries.append(_german_to_english_hint(question))

    # Add German variant for English questions
    if language == "en" or _looks_english(question):
        queries.append(_english_to_german_hint(question))

    # Remove duplicates preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        normalized = q.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(q)
    return unique


def _generate_entity_queries(
    question: str, expected_sources: list[str], language: str
) -> list[str]:
    """Generate entity-focused queries from extracted keywords."""
    entities = _extract_key_entities(question)
    queries: list[str] = []

    for entity in entities:
        queries.append(entity)
        # Combine with expected source type hints
        for src in expected_sources[:2]:  # limit to 2 source types
            queries.append(f"{entity} {src}")

    return list(dict.fromkeys(queries))  # deduplicate preserving order


def _generate_gap_queries(
    question: str, context: dict[str, str], language: str
) -> list[str]:
    """Generate queries to fill gaps identified from dependency context."""
    queries: list[str] = []

    # Look for explicit gap markers in context
    for dep_id, dep_result in context.items():
        if "missing:" in dep_result.lower() or "lücke:" in dep_result.lower():
            gap_info = dep_result.split(":", 1)[-1].strip()
            queries.append(f"{question} {gap_info}")

    # If no explicit gaps, combine question with dependency keys
    if not queries and context:
        keywords = list(context.keys())[:3]
        combined = " ".join(keywords)
        queries.append(f"{question} {combined}")

    return queries


def _generate_negative_queries(question: str, language: str) -> list[str]:
    """Generate negative/contrast queries for topic refinement."""
    queries: list[str] = []

    # Extract key terms for exclusion queries
    terms = _extract_key_entities(question)
    if len(terms) >= 2:
        main = terms[0]
        for term in terms[1:3]:
            queries.append(f"{main} -{term}")
            queries.append(f"{main} NOT {term}")

    return queries


# ── Utility helpers ──────────────────────────────────────────────────────


def _extract_key_entities(text: str) -> list[str]:
    """Extract likely key entities/terms from a question."""
    # Remove question words
    cleaned = re.sub(
        r"\b(?:was|wie|wo|wann|warum|wer|welche|what|how|where|when|why|who|which)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[?.,!;:()\"']", " ", cleaned)

    # Split into potential entity chunks (noun phrases)
    words = cleaned.split()
    entities: list[str] = []
    current: list[str] = []

    for word in words:
        if word[0].isupper() if word else False:
            if current:
                entities.append(" ".join(current))
                current = []
            current.append(word)
        elif len(word) > 3:  # longer content words
            current.append(word)
        else:
            if current:
                entities.append(" ".join(current))
                current = []

    if current:
        entities.append(" ".join(current))

    # Fallback: use individual words > 3 chars
    if not entities:
        entities = [w for w in words if len(w) > 3]

    return entities[:5]  # limit to 5 entities


def _looks_german(text: str) -> bool:
    """Quick heuristic: does text contain German-specific characters/words?"""
    de_chars = set("äöüßÄÖÜ")
    de_words = {
        "der",
        "die",
        "das",
        "und",
        "oder",
        "mit",
        "von",
        "für",
        "eine",
        "ein",
        "auf",
        "ist",
        "nicht",
        "sich",
        "auch",
    }
    text_lower = text.lower()
    # Check for umlauts
    if any(c in text for c in de_chars):
        return True
    # Check for common German words
    words = set(text_lower.split())
    if words & de_words:
        return True
    return False


def _looks_english(text: str) -> bool:
    """Quick heuristic: does text look like English?"""
    en_words = {
        "the",
        "and",
        "or",
        "with",
        "for",
        "from",
        "that",
        "this",
        "what",
        "how",
        "when",
        "where",
        "which",
        "not",
        "but",
    }
    words = set(text.lower().split())
    if words & en_words:
        return not _looks_german(text)
    return False


def _german_to_english_hint(question: str) -> str:
    """Wrap German question as an English search hint."""
    return f"(EN) {question}"


def _english_to_german_hint(question: str) -> str:
    """Wrap English question as a German search hint."""
    return f"(DE) {question}"
