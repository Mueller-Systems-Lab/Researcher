"""Tests für Multi-Query Evaluation (keine echten Netzwerkdienste)."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_is_safe_query_ok():
    from scripts.research_multi_query_eval import is_safe_query

    assert is_safe_query("What is a search engine?") is True
    assert is_safe_query("What is SearXNG?") is True


def test_is_safe_query_blocked():
    from scripts.research_multi_query_eval import is_safe_query

    assert is_safe_query("exploit database") is False
    assert is_safe_query("CVE-2024 vulnerability") is False


def test_default_queries_all_safe():
    from scripts.research_multi_query_eval import DEFAULT_QUERIES, is_safe_query

    for q in DEFAULT_QUERIES:
        assert is_safe_query(q), f"Unexpected unsafe query: {q}"


def test_load_evaluation_scores():
    from scripts.research_multi_query_eval import load_evaluation_scores

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "eval.json")
        with open(path, "w") as f:
            json.dump({"scores": {"overall": 95, "source_coverage": 100}}, f)
        scores = load_evaluation_scores(path)
        assert scores["overall"] == 95


def test_load_evaluation_scores_missing():
    from scripts.research_multi_query_eval import load_evaluation_scores

    assert load_evaluation_scores("/nonexistent/eval.json") == {}


def test_generate_aggregate():
    from scripts.research_multi_query_eval import generate_aggregate

    results = [
        {
            "query": "q1",
            "success": True,
            "report_path": "/tmp/r1.md",
            "eval_path": "/tmp/e1.json",
            "scores": {
                "overall": 99,
                "source_coverage": 100,
                "traceability": 95,
                "hallucination_risk": 100,
                "local_first": 100,
            },
        },
        {
            "query": "q2",
            "success": True,
            "report_path": "/tmp/r2.md",
            "eval_path": "/tmp/e2.json",
            "scores": {
                "overall": 90,
                "source_coverage": 80,
                "traceability": 90,
                "hallucination_risk": 95,
                "local_first": 100,
            },
        },
        {
            "query": "q3",
            "success": False,
            "report_path": "",
            "eval_path": "",
            "scores": {},
        },
    ]

    with tempfile.TemporaryDirectory() as d:
        json_path = generate_aggregate(results, d)
        assert os.path.isfile(json_path)
        with open(json_path) as f:
            agg = json.load(f)
        assert agg["passed"] == 2
        assert agg["failed"] == 1
        assert 94 <= agg["aggregate_scores"]["overall_mean"] <= 95
        assert agg["aggregate_scores"]["overall_min"] == 90
