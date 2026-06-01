"""Tests für deep_report — DR-06: Report Writer + Evaluation Loop."""

from __future__ import annotations

from deep_report.citation_inserter import (
    generate_source_list,
    generate_source_table,
    insert_citations,
)
from deep_report.evaluator import (
    evaluate_report,
    is_report_acceptable,
    rejection_reasons,
)
from deep_report.outline import REQUIRED_SECTIONS, generate_outline
from deep_report.revision_loop import (
    generate_gap_queries,
    revision_needed,
    revision_request,
)
from deep_report.writer import write_report, write_report_with_evaluation

# ── Outline ──────────────────────────────────────────────────────────────


def test_outline_has_all_required_sections():
    """Outline enthält alle Pflichtsektionen."""
    outline = generate_outline("Test query")
    titles = [s["title"] for s in outline]
    for section in REQUIRED_SECTIONS:
        assert section in titles, f"Missing section: {section}"


def test_outline_includes_query_in_title():
    """Titel-Platzhalter enthält die Query."""
    outline = generate_outline("GPU Vergleich GTX 1070")
    title_section = next(s for s in outline if s["title"] == "Title")
    assert "GPU Vergleich GTX 1070" in title_section["placeholder"]


# ── Citation Inserter ────────────────────────────────────────────────────


def test_insert_citations_adds_labels():
    """Citations werden als [S1] Inline-Labels eingefügt."""
    text = "GPUs are important for machine learning."
    citations = [
        {"label": "[S1]", "quote": "GPUs are important for machine learning."},
    ]
    result = insert_citations(text, citations)
    assert "[S1]" in result


def test_insert_citations_empty():
    """Ohne Citations bleibt Text unverändert."""
    text = "Some content."
    assert insert_citations(text, []) == text


def test_generate_source_table():
    """Source-Tabelle wird als Markdown erzeugt."""
    sources = [
        {
            "title": "GPU Benchmarks",
            "url": "https://gpu.example.com",
            "domain": "gpu.example.com",
            "retrieved_at": "2026-05-24T00:00:00Z",
        },
    ]
    table = generate_source_table(sources)
    assert "GPU Benchmarks" in table
    assert "gpu.example.com" in table


def test_generate_source_table_empty():
    """Leere Source-Tabelle."""
    assert "No sources" in generate_source_table([])


def test_generate_source_list():
    """Source-Liste mit [S1]-Labels."""
    sources = [
        {"title": "Source A", "url": "https://a.com"},
        {"title": "Source B", "url": "https://b.com"},
    ]
    lst = generate_source_list(sources)
    assert "[S1]" in lst
    assert "[S2]" in lst
    assert "https://a.com" in lst


# ── Evaluator ────────────────────────────────────────────────────────────


def test_evaluate_perfect_report():
    """Perfekter Report erhält hohe Scores."""
    scores = evaluate_report(
        node_count=3,
        nodes_with_evidence=3,
        total_citations=3,
        total_claims=3,
        unique_domains=3,
        total_sources=3,
        nodes_completed=3,
        cloud_detected=False,
    )
    assert scores["source_coverage"] == 100.0
    assert scores["traceability"] == 100.0
    assert scores["evidence_diversity"] == 100.0
    assert scores["node_completion"] == 100.0
    assert scores["local_first"] == 100.0
    assert scores["overall"] >= 90


def test_evaluate_cloud_penalty():
    """Cloud-Erkennung → local_first = 0."""
    scores = evaluate_report(cloud_detected=True)
    assert scores["local_first"] == 0.0


def test_evaluate_low_coverage():
    """Niedrige Source Coverage → niedrige Scores."""
    scores = evaluate_report(
        node_count=5,
        nodes_with_evidence=1,
        total_citations=1,
        total_claims=5,
    )
    assert scores["source_coverage"] == 20.0
    assert scores["traceability"] == 20.0


def test_is_report_acceptable_perfect():
    """Perfekter Report ist akzeptabel."""
    scores = {
        "overall": 95,
        "source_coverage": 100,
        "traceability": 100,
        "local_first": 100,
    }
    assert is_report_acceptable(scores)


def test_is_report_acceptable_low_traceability():
    """Niedrige Traceability → nicht akzeptabel."""
    scores = {
        "overall": 85,
        "source_coverage": 90,
        "traceability": 50,
        "local_first": 100,
    }
    assert not is_report_acceptable(scores)


def test_is_report_acceptable_cloud():
    """Cloud erkannt → nicht akzeptabel."""
    scores = {
        "overall": 95,
        "source_coverage": 100,
        "traceability": 100,
        "local_first": 0,
    }
    assert not is_report_acceptable(scores)


def test_rejection_reasons():
    """Rejection-Reasons nennen konkrete Schwellwerte."""
    reasons = rejection_reasons(
        {"overall": 50, "source_coverage": 30, "traceability": 40, "local_first": 50}
    )
    assert len(reasons) >= 4
    assert any("overall" in r for r in reasons)
    assert any("local_first" in r for r in reasons)


def test_evaluate_zero_denominators():
    """Divison durch Null → 0%."""
    scores = evaluate_report()
    assert scores["source_coverage"] == 0.0
    assert scores["traceability"] == 0.0


# ── Revision Loop ────────────────────────────────────────────────────────


def test_revision_needed_low_scores():
    """Niedrige Scores → Revision needed."""
    scores = {
        "overall": 50,
        "source_coverage": 30,
        "traceability": 40,
        "local_first": 100,
    }
    assert revision_needed(scores)


def test_revision_not_needed_high_scores():
    """Hohe Scores → keine Revision."""
    scores = {
        "overall": 95,
        "source_coverage": 100,
        "traceability": 100,
        "local_first": 100,
    }
    assert not revision_needed(scores)


def test_generate_gap_queries():
    """Gap-Queries werden aus schwachen Scores generiert."""
    gaps = generate_gap_queries(
        {"source_coverage": 30, "traceability": 40, "evidence_diversity": 20},
        original_query="GPU comparison",
    )
    assert len(gaps) >= 1


def test_revision_request_structure():
    """Revision-Request hat korrekte Struktur."""
    req = revision_request(
        {"overall": 50, "source_coverage": 30, "traceability": 40, "local_first": 100},
        original_query="Test",
    )
    assert req["action"] == "revise"
    assert "scores" in req
    assert "gap_queries" in req
    assert "reasons" in req


# ── Report Writer ────────────────────────────────────────────────────────


def test_write_report_has_required_sections():
    """Report enthält alle Pflichtsektionen."""
    report = write_report(
        query="Test research",
        node_results={"n1": "Finding about GPUs."},
        sources=[
            {
                "title": "GPU Doc",
                "url": "https://gpu.example.com",
                "domain": "gpu.example.com",
                "retrieved_at": "2026-05-24T00:00:00Z",
            }
        ],
        citations=[{"label": "[S1]", "quote": "Finding about GPUs."}],
    )
    for section in REQUIRED_SECTIONS:
        if section == "Title":
            assert "Deep Research Report" in report, "Missing: Title"
        elif section == "Findings by DAG Node":
            assert "Findings" in report, f"Missing: {section}"
        else:
            assert section.lower() in report.lower(), f"Missing: {section}"


def test_write_report_contains_query():
    """Report enthält die originale Query."""
    report = write_report(query="GPU benchmark comparison")
    assert "GPU benchmark comparison" in report


def test_write_report_contains_citations():
    """Report enthält Inline-Citations."""
    report = write_report(
        query="Test",
        node_results={"n1": "Important finding."},
        citations=[{"label": "[S1]", "quote": "Important finding."}],
    )
    assert "[S1]" in report


def test_write_report_cloud_detected_penalty():
    """Cloud-Erkennung wird im Report dokumentiert."""
    report = write_report(query="Test", cloud_detected=True)
    assert "Evaluation Summary" in report


def test_write_report_with_evaluation():
    """write_report_with_evaluation liefert Report + Scores."""
    result = write_report_with_evaluation(
        query="Test",
        node_results={"n1": "Finding.", "n2": "Another."},
        sources=[
            {
                "title": "S",
                "url": "https://s.com",
                "domain": "s.com",
                "retrieved_at": "2026-05-24T00:00:00Z",
            }
        ],
        citations=[{"label": "[S1]", "quote": "Finding."}],
    )
    assert "report" in result
    assert "scores" in result
    assert "acceptable" in result


def test_write_report_with_evaluation_low_quality():
    """Niedrige Qualität → revision gesetzt."""
    result = write_report_with_evaluation(
        query="Test",
        node_results={},
        sources=[],
        citations=[],
    )
    assert not result["acceptable"]
    assert result["revision"] is not None
    assert result["revision"]["action"] == "revise"


def test_write_report_empty_sources():
    """Report ohne Quellen funktioniert."""
    report = write_report(query="Minimal test")
    assert "Research Question" in report
    assert "*No sources" in report

def test_insert_citations_fuzzy_match():
    """Citations via fuzzy (non-exact) match."""
    from deep_report.citation_inserter import insert_citations

    text = "GPUs are crucial for machine learning workloads."
    citations = [
        {"label": "[S1]", "quote": "GPUs are important for machine learning."},
    ]
    result = insert_citations(text, citations)
    assert "[S1]" in result


def test_generate_gap_queries_with_node_questions():
    """Gap-Queries from node_questions."""
    from deep_report.revision_loop import generate_gap_queries

    gaps = generate_gap_queries(
        {"source_coverage": 30, "traceability": 40, "evidence_diversity": 20},
        original_query="GPU comparison",
        node_questions=["How fast?", "What cost?"],
    )
    assert any("verifiable citation" in g for g in gaps)
