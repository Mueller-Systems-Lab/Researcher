"""Tests für Report Quality Evaluation (gemockt, keine echten Dienste)."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── parse_report ──────────────────────────────────────────────────────────────


def _make_report(content: str, tmpdir: str) -> str:
    """Schreibt einen Report und gibt den Pfad zurück."""
    path = os.path.join(tmpdir, "research_test.md")
    with open(path, "w") as f:
        f.write(content)
    return path


def test_parse_report_basic():
    from scripts.evaluate_research_report import parse_report

    with tempfile.TemporaryDirectory() as d:
        path = _make_report(
            "# Research Report\n\n"
            "**Query:** What is SearXNG?\n\n"
            "**Sources:** 5\n\n"
            "## Summary\n\nTest summary.\n\n"
            "## Sources\n\n1. **Source A**...\n",
            d,
        )
        report = parse_report(path)
        assert report["query"] == "What is SearXNG?"
        assert report["source_count"] == 5
        assert report["has_source_section"] is True
        assert report["has_summary_section"] is True


def test_parse_report_no_sources():
    from scripts.evaluate_research_report import parse_report

    with tempfile.TemporaryDirectory() as d:
        path = _make_report(
            "# Research Report\n\n**Query:** test\n\n**Sources:** 0\n",
            d,
        )
        report = parse_report(path)
        assert report["source_count"] == 0
        assert report["has_source_section"] is False


# ── Scores ────────────────────────────────────────────────────────────────────


def test_source_coverage_high():
    from scripts.evaluate_research_report import score_source_coverage

    report = {
        "has_source_section": True,
        "source_count": 5,
        "sources_listed": 5,
        "has_summary_section": True,
    }
    score, _ = score_source_coverage(report)
    assert score >= 80


def test_source_coverage_low():
    from scripts.evaluate_research_report import score_source_coverage

    report = {
        "has_source_section": False,
        "source_count": 0,
        "sources_listed": 0,
        "has_summary_section": False,
    }
    score, notes = score_source_coverage(report)
    assert score <= 20
    assert notes != "OK"


def test_traceability_high():
    from scripts.evaluate_research_report import score_traceability

    report = {
        "query": "What is SearXNG?",
        "source_count": 5,
        "source_ids": 5,
        "model_requested": "qwen3.5:9b",
        "model_used": "qwen3.5:9b",
        "model_fallback": False,
        "has_metadata_section": True,
        "has_limitations_section": True,
        "degraded": False,
        "sources_listed": 5,
        "model_mentioned": True,
    }
    score, _ = score_traceability(report)
    assert score >= 85


def test_traceability_no_query():
    from scripts.evaluate_research_report import score_traceability

    report = {
        "query": "",
        "source_count": 0,
        "source_ids": 0,
        "model_requested": "",
        "model_used": "",
        "has_metadata_section": False,
        "has_limitations_section": False,
        "degraded": True,
        "sources_listed": 0,
        "model_mentioned": False,
    }
    score, notes = score_traceability(report)
    assert score <= 30


def test_hallucination_risk_clean():
    from scripts.evaluate_research_report import score_hallucination_risk

    report = {
        "summary": "A simple factual summary based on sources.",
        "has_source_section": True,
        "source_count": 5,
    }
    score, _ = score_hallucination_risk(report)
    assert score >= 90


def test_hallucination_risk_high():
    from scripts.evaluate_research_report import score_hallucination_risk

    report = {
        "summary": "This guaranteed proves without any doubt that...",
        "has_source_section": False,
        "source_count": 0,
    }
    score, notes = score_hallucination_risk(report)
    assert score < 50
    assert "Riskante Wörter" in notes


def test_local_first_clean():
    from scripts.evaluate_research_report import score_local_first

    report = {"cloud_references": [], "model_mentioned": True}
    score, _ = score_local_first(report)
    assert score == 100


def test_local_first_cloud():
    from scripts.evaluate_research_report import score_local_first

    report = {"cloud_references": ["openai"], "model_mentioned": True}
    score, notes = score_local_first(report)
    assert score < 100
    assert "openai" in notes


def test_calculate_overall():
    from scripts.evaluate_research_report import calculate_overall

    scores = {
        "source_coverage": 100,
        "traceability": 100,
        "hallucination_risk": 100,
        "local_first": 100,
    }
    assert calculate_overall(scores) == 100


def test_generate_evaluation():
    from scripts.evaluate_research_report import generate_evaluation

    with tempfile.TemporaryDirectory() as d:
        path = _make_report(
            "# Research Report\n\n"
            "**Query:** test\n\n**Sources:** 3\n\n"
            "## Summary\n\nA test.\n\n"
            "## Sources\n\n1. **A**\n2. **B**\n3. **C**\n",
            d,
        )
        eval_data = generate_evaluation(path, os.path.join(d, "eval"))
        assert eval_data["overall"] > 0
        assert os.path.exists(eval_data["json_path"])
        assert os.path.exists(eval_data["md_path"])

        with open(eval_data["json_path"]) as f:
            j = json.load(f)
            assert "scores" in j

        with open(eval_data["md_path"]) as f:
            md = f.read()
            assert "Overall Score" in md
