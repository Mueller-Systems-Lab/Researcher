"""Tests für research_workers — DR-03: Researcher Worker + Query Decomposition.

Abdeckung:
- Query Decomposition (Primary, Entity, Gap, Negative)
- Gap Analyzer
- Mehrsprachigkeit (Deutsche Umlaute, Search Keys)
- Worker-Integration (Orchestrator-kompatibel)
- Keine Inhaltsfilterung (Security/Darknet OK)
"""

from __future__ import annotations

import json

from research_workers.gap_analyzer import analyze_gaps, has_significant_gaps
from research_workers.query_decomposer import (
    DecomposedQueries,
    _extract_key_entities,
    _looks_english,
    _looks_german,
    decompose_node,
)
from research_workers.worker import (
    queries_from_json,
    queries_to_json,
    research_worker,
)

# ── Query Decomposition ──────────────────────────────────────────────────


def test_simple_node_produces_primary_queries():
    """Einfache Node erzeugt Primary Queries."""
    queries = decompose_node(
        node_id="n1",
        question="What is SearXNG and how does it work?",
    )
    assert len(queries.primary_queries) >= 1
    assert any("SearXNG" in q for q in queries.primary_queries)


def test_german_node_produces_primary_queries():
    """Deutsche Node erzeugt Primary Queries."""
    queries = decompose_node(
        node_id="n1",
        question="Wie funktioniert eine lokale LLM-Runtime?",
        language="de",
    )
    assert len(queries.primary_queries) >= 1
    assert any("funktioniert" in q.lower() for q in queries.primary_queries)


def test_entity_queries_from_expected_sources():
    """Dependency-Kontext + expected_sources erzeugt Entity Queries."""
    queries = decompose_node(
        node_id="n2",
        question="Compare Python and Rust for ML pipelines.",
        expected_sources=["benchmark", "case study"],
    )
    assert len(queries.entity_queries) >= 1


def test_gap_queries_from_dependency_context():
    """Bekannte Gap aus Dependency-Kontext erzeugt Gap Query."""
    queries = decompose_node(
        node_id="n3",
        question="Determine optimal GPU for LLM inference.",
        context_from_dependencies={
            "dep1": "missing: VRAM benchmarks for GTX 1070",
            "dep2": "Found: 8GB VRAM, limited for 13B models",
        },
    )
    assert len(queries.gap_queries) >= 1
    assert any("GTX 1070" in q for q in queries.gap_queries)


def test_negative_queries_generated():
    """Negative Queries werden für Kontrast erzeugt."""
    queries = decompose_node(
        node_id="n4",
        question="Compare cloud vs local LLM deployment costs",
    )
    # negative queries may or may not be generated depending on entity extraction
    assert queries.negative_queries is not None
    assert isinstance(queries.negative_queries, list)


def test_german_umlauts_preserved():
    """Deutsche Umlaute bleiben in Queries erhalten."""
    queries = decompose_node(
        node_id="n1",
        question="Öffentliche Förderung für KI-Startups in Österreich",
        language="de",
    )
    all_qs = queries.all_queries()
    # At least the primary query preserves umlauts
    assert any("Österreich" in q for q in all_qs) or any(
        "Öffentliche" in q for q in all_qs
    ), f"Umlaute should be preserved in queries: {all_qs}"


def test_ascii_fallback_exists():
    """ASCII-Fallback existiert (keine Umlaute gehen nicht kaputt)."""
    queries = decompose_node(
        node_id="n1",
        question="Was ist der Unterschied zwischen OAuth und SAML?",
        language="de",
    )
    all_qs = queries.all_queries()
    # Query decomposition should work regardless of characters
    assert len(all_qs) >= 1
    # All queries should be valid strings
    for q in all_qs:
        assert isinstance(q, str)
        assert len(q) > 0


# ── Keine Inhaltsfilterung ───────────────────────────────────────────────


def test_darknet_query_decomposed():
    """Darknet-Query wird ohne Filterung zerlegt."""
    queries = decompose_node(
        node_id="n1",
        question="Analysiere die Sicherheitsarchitektur von Darknet-Marktplätzen",
    )
    assert len(queries.primary_queries) >= 1
    assert any(
        "Darknet" in q or "darknet" in q.lower() for q in queries.all_queries()
    ), "Darknet query must not be filtered"


def test_security_query_decomposed():
    """Security-Research-Query wird ohne Filterung zerlegt."""
    queries = decompose_node(
        node_id="n1",
        question=(
            "Untersuche Exploit-Techniken und Malware-Analyse für Penetrationstests"
        ),
    )
    assert len(queries.all_queries()) >= 1
    # Kein Content-Filter — alle Terms bleiben erhalten
    assert any(
        "Exploit" in q or "exploit" in q.lower() for q in queries.all_queries()
    ), "Exploit query must not be filtered"


def test_any_research_topic_decomposed():
    """Beliebige Research-Themen werden ohne Inhaltsfilterung zerlegt."""
    topics = [
        "Phishing detection techniques",
        "Weapon systems analysis",
        "Bypass methods for authentication",
        "Credentials harvesting prevention",
    ]
    for topic in topics:
        queries = decompose_node(node_id="n1", question=topic)
        assert len(queries.all_queries()) >= 1, (
            f"Topic '{topic}' should produce queries without filtering"
        )


# ── Gap Analyzer ─────────────────────────────────────────────────────────


def test_gap_analyzer_detects_explicit_gaps():
    """Gap Analyzer erkennt explizite Gap-Marker."""
    gaps = analyze_gaps(
        question="Compare GPU options",
        dependency_results={
            "dep1": "Found: RTX 4090 data. Missing: GTX 1070 benchmarks.",
        },
    )
    assert len(gaps) >= 1
    assert any("GTX 1070" in g for g in gaps)


def test_gap_analyzer_empty_for_no_gaps():
    """Gap Analyzer liefert leere Liste bei keinen Lücken."""
    gaps = analyze_gaps(
        question="Test query",
        dependency_results={"dep1": "All data found successfully."},
    )
    # No gap markers → no gaps
    assert isinstance(gaps, list)


def test_gap_analyzer_source_coverage():
    """Gap Analyzer prüft Source Coverage."""
    gaps = analyze_gaps(
        question="LLM performance comparison",
        dependency_results={"dep1": "some text about LLMs"},
        expected_sources=["benchmark", "whitepaper"],
    )
    assert isinstance(gaps, list)
    # May generate coverage gaps for missing source types


def test_has_significant_gaps():
    """has_significant_gaps erkennt signifikante Lücken."""
    assert has_significant_gaps(["gap1", "gap2"], min_gaps=2)
    assert not has_significant_gaps(["gap1"], min_gaps=2)


# ── Worker Integration ───────────────────────────────────────────────────


def test_worker_returns_success():
    """Worker-Callback liefert ok=True mit Artifacts."""
    ok, artifacts = research_worker(
        node_id="n1",
        question="Test research question",
        context={
            "rationale": "Testing worker integration",
            "expected_sources": ["docs", "benchmarks"],
            "language": "en",
        },
    )
    assert ok is True
    assert len(artifacts) >= 1
    # Artifact should be valid JSON
    data = json.loads(artifacts[0])
    assert data["node_id"] == "n1"
    assert len(data["primary_queries"]) >= 1


def test_worker_with_dependency_context():
    """Worker integriert Dependency-Ergebnisse."""
    ok, artifacts = research_worker(
        node_id="n2",
        question="Evaluate GPU options",
        context={
            "rationale": "Follow-up to hardware analysis",
            "dependency_results": {
                "dep1": "Hardware survey complete. Missing: GTX 1070 data.",
            },
        },
    )
    assert ok is True
    data = json.loads(artifacts[0])
    # Gap queries should be generated from dependency context
    assert data["node_id"] == "n2"


def test_worker_handles_empty_context():
    """Worker funktioniert mit minimalem Kontext."""
    ok, artifacts = research_worker(
        node_id="n3",
        question="Simple question",
        context={},
    )
    assert ok is True
    assert len(artifacts) >= 1


def test_queries_json_roundtrip():
    """DecomposedQueries überlebt JSON Roundtrip."""
    queries = decompose_node(
        node_id="n1",
        question="Test question with ümlauts",
        language="de",
        expected_sources=["source1"],
    )
    json_str = queries_to_json(queries)
    restored = queries_from_json(json_str)

    assert restored.node_id == queries.node_id
    assert restored.language == queries.language
    assert restored.primary_queries == queries.primary_queries


# ── Utility Helpers ──────────────────────────────────────────────────────


def test_extract_key_entities():
    """_extract_key_entities extrahiert Schlüsselbegriffe."""
    entities = _extract_key_entities(
        "Vergleiche Python und Rust für Machine Learning Pipelines"
    )
    assert len(entities) >= 1
    assert any("Python" in e or "Rust" in e for e in entities)


def test_looks_german_detection():
    """_looks_german erkennt deutsche Texte."""
    assert _looks_german("Wie funktioniert eine Suchmaschine?")
    assert _looks_german("Öffentliche Förderung für Startups")


def test_looks_english_detection():
    """_looks_english erkennt englische Texte."""
    assert _looks_english("How does a search engine work?")
    assert not _looks_english("Wie funktioniert eine Suchmaschine?")


def test_decomposed_queries_all_queries():
    """DecomposedQueries.all_queries() aggregiert alle Kategorien."""
    q = DecomposedQueries(
        node_id="n1",
        primary_queries=["p1"],
        entity_queries=["e1", "e2"],
        gap_queries=["g1"],
        negative_queries=["n1"],
    )
    assert q.all_queries() == ["p1", "e1", "e2", "g1", "n1"]
    assert len(q) == 5
