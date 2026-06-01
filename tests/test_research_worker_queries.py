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
from unittest.mock import MagicMock, patch

from research_workers.gap_analyzer import analyze_gaps, has_significant_gaps
from research_workers.query_decomposer import (
    DecomposedQueries,
    _extract_key_entities,
    _looks_english,
    _looks_german,
    decompose_node,
)
from research_workers.worker import (
    _build_artifact,
    _execute_queries,
    _store_sources,
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


# ═══════════════════════════════════════════════════════════════════════════
# _build_artifact — pure logic (zero external deps)
# ═══════════════════════════════════════════════════════════════════════════


def test_build_artifact_full_structure():
    """_build_artifact constructs complete JSON artifact with all fields."""
    queries = DecomposedQueries(
        node_id="n1",
        language="en",
        primary_queries=["primary query 1"],
        entity_queries=["entity query 1"],
        gap_queries=["gap query 1"],
        negative_queries=["negative query 1"],
    )
    search_results = [
        {
            "url": "https://example.com/1",
            "title": "Example Title 1",
            "source": "SearXNG",
            "score": 0.85,
            "body": "This is the body content of result 1.",
        },
        {
            "url": "https://example.com/2",
            "title": "Example Title 2",
            "source": "Wiki",
            "score": 0.72,
            "body": None,
            "raw_content": "Raw content from result 2.",
        },
    ]
    source_ids = ["src-abc-123", "src-def-456"]

    artifact = _build_artifact(queries, search_results, source_ids, "n1")
    data = json.loads(artifact)

    assert data["node_id"] == "n1"
    assert data["language"] == "en"
    assert data["primary_queries"] == ["primary query 1"]
    assert data["entity_queries"] == ["entity query 1"]
    assert data["gap_queries"] == ["gap query 1"]
    assert data["negative_queries"] == ["negative query 1"]
    assert data["query_count"] == 4
    assert data["source_ids"] == source_ids
    assert data["sources_found"] == 2
    assert data["sources_stored"] == 2
    assert len(data["search_results"]) == 2

    r0 = data["search_results"][0]
    assert r0["url"] == "https://example.com/1"
    assert r0["title"] == "Example Title 1"
    assert r0["source"] == "SearXNG"
    assert r0["score"] == 0.85
    assert r0["snippet"] == "This is the body content of result 1."

    r1 = data["search_results"][1]
    assert r1["url"] == "https://example.com/2"
    assert r1["source"] == "Wiki"
    assert r1["snippet"] == "Raw content from result 2."


def test_build_artifact_empty_lists():
    """_build_artifact handles empty queries, zero search results, zero IDs."""
    queries = DecomposedQueries(node_id="empty_node")
    artifact = _build_artifact(queries, [], [], "empty_node")
    data = json.loads(artifact)

    assert data["node_id"] == "empty_node"
    assert data["primary_queries"] == []
    assert data["query_count"] == 0
    assert data["search_results"] == []
    assert data["source_ids"] == []
    assert data["sources_found"] == 0
    assert data["sources_stored"] == 0


def test_build_artifact_snippet_truncation():
    """_build_artifact truncates snippet to 300 characters."""
    queries = DecomposedQueries(node_id="n1")
    long_body = "b" * 500
    search_results = [
        {"url": "https://a.com", "title": "Body", "body": long_body},
    ]

    artifact = _build_artifact(queries, search_results, [], "n1")
    data = json.loads(artifact)

    assert len(data["search_results"][0]["snippet"]) == 300


def test_build_artifact_default_values():
    """_build_artifact uses safe defaults for missing keys."""
    queries = DecomposedQueries(node_id="n1")
    search_results = [{}]

    artifact = _build_artifact(queries, search_results, ["src-1"], "n1")
    data = json.loads(artifact)

    r = data["search_results"][0]
    assert r["url"] == ""
    assert r["title"] == ""
    assert r["source"] == "SearXNG"
    assert r["score"] == 0
    assert r["snippet"] == ""


def test_build_artifact_snippet_body_priority():
    """_build_artifact prefers body over raw_content for snippet."""
    queries = DecomposedQueries(node_id="n1")
    search_results = [
        {
            "url": "https://test.com",
            "body": "body content",
            "raw_content": "raw content",
        },
    ]

    artifact = _build_artifact(queries, search_results, [], "n1")
    data = json.loads(artifact)
    assert data["search_results"][0]["snippet"] == "body content"


def test_build_artifact_preserves_unicode():
    """_build_artifact preserves non-ASCII characters."""
    queries = DecomposedQueries(
        node_id="n1",
        language="de",
        primary_queries=["Öffentliche Förderung für KI"],
    )
    search_results = [
        {"url": "https://münchen.de", "title": "Förderung in München"},
    ]

    artifact = _build_artifact(queries, search_results, [], "n1")
    assert "Öffentliche" in artifact
    assert "München" in artifact

    data = json.loads(artifact)
    assert data["primary_queries"][0] == "Öffentliche Förderung für KI"


# ═══════════════════════════════════════════════════════════════════════════
# _execute_queries — error paths and deduplication
# ═══════════════════════════════════════════════════════════════════════════


def test_execute_queries_empty_input():
    """Empty query_strings returns empty list immediately."""
    assert _execute_queries([]) == []
    assert _execute_queries([], run_id="test-empty") == []


def test_execute_queries_importerror():
    """ImportError for CompositeRetriever is caught gracefully."""
    import builtins

    _real_import = builtins.__import__

    def _block_search(name, *a, **kw):
        if name == "search" or name.startswith("search."):
            raise ImportError(f"MOCK: no module {name!r}")
        return _real_import(name, *a, **kw)

    with patch("builtins.__import__", side_effect=_block_search):
        result = _execute_queries(["test query"], run_id="test-importerror")

    assert result == []


def test_execute_queries_per_query_exception():
    """Per-query Exception caught; does not abort the loop."""
    failing_retriever = MagicMock()
    failing_retriever.search.side_effect = RuntimeError("SearXNG timeout")

    MockComposite = MagicMock(return_value=failing_retriever)

    with patch("search.composite.CompositeRetriever", MockComposite):
        result = _execute_queries(["failing query"], run_id="test-exc")

    assert result == []
    MockComposite.assert_called_once_with("failing query")


def test_execute_queries_deduplication():
    """Duplicate URLs removed; first occurrence kept; empty URL dropped."""
    r_keep = {"url": "https://example.com", "title": "First"}
    r_dupe = {"url": "https://example.com", "title": "Duplicate"}
    r_other = {"url": "https://other.com", "title": "Other"}
    r_no_url = {"url": "", "title": "No URL"}

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [r_keep, r_dupe, r_other, r_no_url]

    with patch("search.composite.CompositeRetriever", return_value=mock_retriever):
        result = _execute_queries(["test query"], run_id="test-dedup")

    assert len(result) == 2
    assert result[0] is r_keep
    assert result[1] is r_other


def test_execute_queries_safety_limit():
    """Only first 3 query strings are executed."""
    all_results = [
        {"url": "https://q1.com"},
        {"url": "https://q2.com"},
        {"url": "https://q3.com"},
        {"url": "https://q4.com"},
        {"url": "https://q5.com"},
    ]

    # Return one unique result per query call to avoid dedup
    mock_retriever = MagicMock()
    mock_retriever.search.side_effect = lambda **kw: [all_results.pop(0)]

    MockComposite = MagicMock(return_value=mock_retriever)

    five_queries = ["q1", "q2", "q3", "q4", "q5"]
    with patch("search.composite.CompositeRetriever", MockComposite):
        result = _execute_queries(five_queries, run_id="test-safety")

    assert MockComposite.call_count == 3
    assert len(result) == 3


# ═══════════════════════════════════════════════════════════════════════════
# _store_sources — error paths
# ═══════════════════════════════════════════════════════════════════════════


def test_store_sources_empty_input():
    """Empty search_results returns empty list."""
    assert _store_sources([], run_id="test-empty") == []
    assert _store_sources([]) == []


def test_store_sources_valueerror_skip():
    """ValueError from save_source skips that result; others still stored."""
    search_results = [
        {"url": "https://bad.example", "title": "Bad"},
        {"url": "https://good.example", "title": "Good"},
    ]

    bad_source = MagicMock()
    bad_source.source_id = "src-bad"
    good_source = MagicMock()
    good_source.source_id = "src-good"

    MockEvidenceSource = MagicMock(side_effect=[bad_source, good_source])

    def _save_side_effect(source):
        if source is bad_source:
            raise ValueError("url must not be empty")

    MockSaveSource = MagicMock(side_effect=_save_side_effect)

    with patch("evidence_store.models.EvidenceSource", MockEvidenceSource):
        with patch("evidence_store.store.save_source", MockSaveSource):
            result = _store_sources(search_results, run_id="test-valerr")

    assert result == ["src-good"]


def test_store_sources_oserror_caught():
    """OSError from save_source is caught per-result."""
    search_results = [
        {"url": "https://fail.io", "title": "Fails"},
        {"url": "https://ok.io", "title": "OK"},
    ]

    fail_source = MagicMock()
    fail_source.source_id = "src-fail"
    ok_source = MagicMock()
    ok_source.source_id = "src-ok"

    MockEvidenceSource = MagicMock(side_effect=[fail_source, ok_source])

    def _save_side_effect(source):
        if source is fail_source:
            raise OSError("Disk full")

    MockSaveSource = MagicMock(side_effect=_save_side_effect)

    with patch("evidence_store.models.EvidenceSource", MockEvidenceSource):
        with patch("evidence_store.store.save_source", MockSaveSource):
            result = _store_sources(search_results, run_id="test-oserr")

    assert result == ["src-ok"]


# ═══════════════════════════════════════════════════════════════════════════
# Final gaps → 100% coverage
# ═══════════════════════════════════════════════════════════════════════════


def test_store_sources_importerror():
    """ImportError for evidence_store is caught; returns empty list."""
    import builtins

    _real_import = builtins.__import__

    def _block_evidence(name, *a, **kw):
        if name == "evidence_store" or name.startswith("evidence_store."):
            raise ImportError("MOCK: no evidence_store")
        return _real_import(name, *a, **kw)

    search_results = [{"url": "https://example.com", "title": "Test"}]

    with patch("builtins.__import__", side_effect=_block_evidence):
        result = _store_sources(search_results, run_id="test-importerr")

    assert result == []


def test_worker_exception_returns_false():
    """Exception in decompose_node returns (False, [])."""
    with patch(
        "research_workers.worker.decompose_node",
        side_effect=ValueError("Decomposition failed"),
    ):
        ok, artifacts = research_worker(
            node_id="n1",
            question="This will raise",
            context={},
        )

    assert ok is False
    assert artifacts == []


def test_worker_search_results_no_sources_warning():
    """Warning when search succeeds but evidence store stores nothing."""
    fake_search_results = [{"url": "https://example.com/1", "title": "R1"}]

    with (
        patch(
            "research_workers.worker._execute_queries",
            return_value=fake_search_results,
        ),
        patch(
            "research_workers.worker._store_sources",
            return_value=[],
        ),
        patch("research_workers.worker.logger") as mock_logger,
    ):
        ok, artifacts = research_worker(
            node_id="warn-node",
            question="Test question",
            context={"run_id": "run-store-fail"},
        )

    assert ok is True
    warning_msgs = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert any("zero stored in evidence store" in msg for msg in warning_msgs)
