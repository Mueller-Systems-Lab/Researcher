"""Tests für research_planner — DR-01: Collaborative Planner + Research Plan DAG.

Abdeckung:
- Plan-Erzeugung (deterministic + LLM fallback)
- DAG-Validierung (Zyklen, Eindeutigkeit)
- JSON Import/Export
- Markdown Export
- Approval-Gate
- Query-Decomposition (inkl. deutsche Umlaute, Security/Darknet)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from research_planner.approval import (
    PlanNotApprovedError,
    approve_plan,
    assert_plan_approved,
    is_plan_approved,
    revoke_approval,
)
from research_planner.models import (
    ResearchNode,
    ResearchPlan,
    ResearchPlanStatus,
    RiskLevel,
)
from research_planner.planner import (
    _deterministic_plan,
    _parse_llm_output,
    _parse_risk,
    _split_query,
    generate_plan,
)
from research_planner.serialization import (
    plan_from_dict,
    plan_from_json,
    plan_to_dict,
    plan_to_json,
    plan_to_markdown,
)
from research_planner.validation import (
    DAGValidationError,
    get_topological_order,
    has_cycle,
    validate_plan,
)

# ── Plan Generation ──────────────────────────────────────────────────────


def test_generate_plan_creates_at_least_three_nodes():
    """Plan für komplexe Query mit Semikolons enthält mindestens 3 Knoten."""
    query = (
        "Hardware Constraints erfassen; Modellkandidaten auflisten; "
        "Runtime-Optionen vergleichen; Stabilität bewerten"
    )
    plan = generate_plan(query)
    assert len(plan.nodes) >= 3, f"Expected >=3 nodes, got {len(plan.nodes)}"
    assert plan.query == query
    assert plan.status == ResearchPlanStatus.DRAFT


def test_generate_plan_all_nodes_have_unique_ids():
    """Jeder Knoten hat eine eindeutige ID."""
    plan = generate_plan("Vergleiche Python und Rust für ML-Pipelines.")
    ids = [n.node_id for n in plan.nodes]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


def test_generate_plan_simple_query_creates_plan():
    """Auch einfache Queries erzeugen einen validen Plan."""
    plan = generate_plan("Was ist SearXNG?")
    assert len(plan.nodes) >= 1
    assert plan.status == ResearchPlanStatus.DRAFT


def test_generate_plan_fallback_with_invalid_llm():
    """LLM-Planner-Fallback: deterministic planner wird genutzt wenn LLM fehlschlägt."""
    plan = generate_plan(
        "Test query for fallback.",
        use_llm=True,
        llm_base_url="http://127.0.0.1:19999",  # non-existent
        llm_timeout=1.0,
    )
    assert len(plan.nodes) >= 1
    assert plan.status == ResearchPlanStatus.DRAFT


# ── DAG Validation ───────────────────────────────────────────────────────


def test_dag_valid_topological_order():
    """Gültiger DAG liefert korrekte topologische Reihenfolge."""
    plan = ResearchPlan(query="Test DAG")
    n1 = ResearchNode(title="Step 1", question="Q1")
    n2 = ResearchNode(title="Step 2", question="Q2")
    n3 = ResearchNode(title="Step 3", question="Q3")
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_node(n3)
    plan.add_dependency(n1.node_id, n2.node_id)
    plan.add_dependency(n2.node_id, n3.node_id)

    order = validate_plan(plan)
    assert order == [n1.node_id, n2.node_id, n3.node_id]


def test_dag_cycle_detected():
    """Zyklischer Graph wird abgelehnt."""
    plan = ResearchPlan(query="Cycle test")
    n1 = ResearchNode(title="A", question="Qa")
    n2 = ResearchNode(title="B", question="Qb")
    plan.add_node(n1)
    plan.add_node(n2)
    plan.add_dependency(n1.node_id, n2.node_id)
    plan.add_dependency(n2.node_id, n1.node_id)  # cycle

    with pytest.raises(DAGValidationError, match="Cycle"):
        validate_plan(plan)


def test_has_cycle_returns_true_for_cycle():
    """has_cycle erkennt Zyklen (non-raising)."""
    plan = ResearchPlan(query="Cycle")
    a = ResearchNode(title="A", question="Q")
    b = ResearchNode(title="B", question="Q")
    plan.add_node(a)
    plan.add_node(b)
    plan.add_dependency(a.node_id, b.node_id)
    plan.add_dependency(b.node_id, a.node_id)
    assert has_cycle(plan) is True


def test_has_cycle_returns_false_for_dag():
    """has_cycle gibt False für azyklischen Plan."""
    plan = ResearchPlan(query="DAG")
    a = ResearchNode(title="A", question="Q")
    b = ResearchNode(title="B", question="Q")
    plan.add_node(a)
    plan.add_node(b)
    plan.add_dependency(a.node_id, b.node_id)
    assert has_cycle(plan) is False


def test_dag_duplicate_node_ids_rejected():
    """Doppelte node_ids werden abgelehnt."""
    plan = ResearchPlan(query="Dup test")
    n1 = ResearchNode(title="A", question="Q", node_id="dup")
    n2 = ResearchNode(title="B", question="Q", node_id="dup")
    plan.nodes = [n1, n2]

    with pytest.raises(DAGValidationError, match="Duplicate"):
        validate_plan(plan)


def test_dag_self_dependency_rejected():
    """Selbstabhängigkeit wird abgelehnt."""
    plan = ResearchPlan(query="Self")
    n = ResearchNode(title="Solo", question="Q")
    plan.add_node(n)
    plan.add_dependency(n.node_id, n.node_id)

    with pytest.raises(DAGValidationError, match="cannot depend on itself"):
        validate_plan(plan)


def test_dag_missing_dependency_node():
    """Fehlende Referenz in Dependencies wird abgelehnt."""
    plan = ResearchPlan(query="Missing")
    n = ResearchNode(title="A", question="Q")
    plan.add_node(n)
    plan.add_dependency("nonexistent", n.node_id)

    with pytest.raises(DAGValidationError, match="does not exist"):
        validate_plan(plan)


# ── Serialization ────────────────────────────────────────────────────────


def test_json_roundtrip():
    """Plan kann JSON exportieren und wieder importieren."""
    plan = generate_plan("Test JSON roundtrip: A; B; C")
    json_str = plan_to_json(plan)
    restored = plan_from_json(json_str)

    assert restored.query == plan.query
    assert restored.plan_id == plan.plan_id
    assert len(restored.nodes) == len(plan.nodes)
    assert len(restored.dependencies) == len(plan.dependencies)
    assert restored.status == plan.status


def test_json_roundtrip_via_file():
    """Plan kann als JSON-Datei geschrieben und gelesen werden."""
    plan = generate_plan("Test file roundtrip.")
    json_str = plan_to_json(plan)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "plan.json"
        path.write_text(json_str, encoding="utf-8")
        read_back = path.read_text(encoding="utf-8")
        restored = plan_from_json(read_back)

    assert restored.plan_id == plan.plan_id
    assert len(restored.nodes) == len(plan.nodes)


def test_dict_roundtrip():
    """Plan kann als Dict exportiert und wiederhergestellt werden."""
    plan = generate_plan("Dict roundtrip")
    d = plan_to_dict(plan)
    restored = plan_from_dict(d)
    assert restored.plan_id == plan.plan_id


def test_markdown_export_contains_nodes():
    """Markdown-Export enthält alle Knoten-Titel."""
    plan = generate_plan("Markdown test; extra; steps")
    md = plan_to_markdown(plan)
    for node in plan.nodes:
        assert node.title in md


def test_markdown_export_contains_plan_id():
    """Markdown-Export enthält die plan_id."""
    plan = generate_plan("Plan ID test")
    md = plan_to_markdown(plan)
    assert plan.plan_id in md


# ── Approval Gate ────────────────────────────────────────────────────────


def test_plan_starts_as_draft():
    """Neuer Plan hat Status DRAFT."""
    plan = generate_plan("Approval test")
    assert plan.status == ResearchPlanStatus.DRAFT


def test_approve_plan_sets_status():
    """approve_plan setzt Status auf APPROVED und Metadaten."""
    plan = generate_plan("Approve me")
    approve_plan(plan, approved_by="test_user")
    assert plan.status == ResearchPlanStatus.APPROVED
    assert plan.approved_at is not None
    assert plan.approved_by == "test_user"


def test_assert_plan_approved_raises_for_draft():
    """assert_plan_approved wirft Fehler bei DRAFT-Plan."""
    plan = generate_plan("Not approved")
    with pytest.raises(PlanNotApprovedError):
        assert_plan_approved(plan)


def test_assert_plan_approved_passes_for_approved():
    """assert_plan_approved wirft keinen Fehler bei APPROVED-Plan."""
    plan = generate_plan("Approved")
    approve_plan(plan)
    assert_plan_approved(plan)  # soll nicht werfen


def test_is_plan_approved_helpers():
    """is_plan_approved erkennt Status korrekt."""
    plan = generate_plan("Check")
    assert not is_plan_approved(plan)
    approve_plan(plan)
    assert is_plan_approved(plan)


def test_revoke_approval_resets_status():
    """revoke_approval setzt Status zurück auf DRAFT."""
    plan = generate_plan("Revoke")
    approve_plan(plan)
    assert plan.status == ResearchPlanStatus.APPROVED
    revoke_approval(plan)
    assert plan.status == ResearchPlanStatus.DRAFT
    assert plan.approved_at is None


# ── Security / Keine Inhaltsfilterung ────────────────────────────────────


def test_darknet_query_not_blocked():
    """Darknet-/Security-Queries werden nicht gefiltert (kein Safety Guard)."""
    plan = generate_plan(
        "Analysiere die Sicherheitsarchitektur von Darknet-Marktplätzen "
        "und vergleiche sie mit Clearnet-Alternativen."
    )
    assert len(plan.nodes) >= 1
    # Die Query muss unverändert im Plan sein
    assert "Darknet" in plan.query or any(
        "Darknet" in n.question or "darknet" in n.question.lower() for n in plan.nodes
    ), "Darknet query should NOT be blocked"


def test_security_research_query_not_blocked():
    """Security-Research-Queries werden nicht gefiltert."""
    plan = generate_plan(
        "Untersuche Exploit-Techniken für Penetrationstests "
        "und dokumentiere Gegenmaßnahmen."
    )
    assert len(plan.nodes) >= 1
    # Keine Blockierung — Query soll unverändert dekomponiert werden


def test_german_umlauts_preserved():
    """Deutsche Umlaute bleiben in Queries erhalten."""
    plan = generate_plan("Öffentliche Förderung für KI-Startups in Österreich")
    assert "Öffentliche" in plan.query
    assert "Österreich" in plan.query
    assert "für" in plan.query


def test_german_query_decomposes_correctly():
    """Deutsche Query mit 'und bestimme' wird korrekt zerlegt."""
    plan = generate_plan(
        "Analysiere die GPU-Anforderungen für LLM-Inferenz "
        "und bestimme die beste Budget-Option für 500€."
    )
    assert len(plan.nodes) >= 2, "German compound query should produce >=2 nodes"


# ── Edge Cases ───────────────────────────────────────────────────────────


def test_empty_query_raises():
    """Leere Query wird abgelehnt."""
    with pytest.raises(ValueError, match="query must not be empty"):
        ResearchPlan(query="")


def test_empty_node_title_raises():
    """Knoten ohne Titel wird abgelehnt."""
    with pytest.raises(ValueError, match="title must not be empty"):
        ResearchNode(title="", question="Q")


def test_empty_node_question_raises():
    """Knoten ohne Frage wird abgelehnt."""
    with pytest.raises(ValueError, match="question must not be empty"):
        ResearchNode(title="T", question="")


def test_plan_without_nodes_rejected():
    """Plan ohne Knoten wird von validate_plan abgelehnt."""
    plan = ResearchPlan(query="Empty")
    with pytest.raises(DAGValidationError, match="at least one node"):
        validate_plan(plan)


def test_topological_order_none_on_invalid():
    """get_topological_order gibt None für invaliden Plan."""
    plan = ResearchPlan(query="Invalid")
    a = ResearchNode(title="A", question="Q")
    b = ResearchNode(title="B", question="Q")
    plan.add_node(a)
    plan.add_node(b)
    plan.add_dependency(a.node_id, b.node_id)
    plan.add_dependency(b.node_id, a.node_id)
    assert get_topological_order(plan) is None


# ── _parse_risk ───────────────────────────────────────────────────────────


def test_parse_risk_low():
    """_parse_risk maps 'low' to RiskLevel.LOW."""
    assert _parse_risk("low") == RiskLevel.LOW


def test_parse_risk_medium():
    assert _parse_risk("medium") == RiskLevel.MEDIUM


def test_parse_risk_case_insensitive():
    assert _parse_risk("HIGH") == RiskLevel.HIGH
    assert _parse_risk("Medium") == RiskLevel.MEDIUM


def test_parse_risk_invalid_fallback():
    assert _parse_risk("invalid") == RiskLevel.UNKNOWN
    assert _parse_risk("") == RiskLevel.UNKNOWN


# ── _split_query ──────────────────────────────────────────────────────────


def test_split_query_semicolon():
    assert _split_query("A; B; C") == ["A", "B", "C"]


def test_split_query_semicolon_filters_empty():
    assert _split_query("A; ; B") == ["A", "B"]


def test_split_query_english_and_determine():
    result = _split_query("Find sources and determine their relevance")
    assert len(result) == 2


def test_split_query_numbered_list():
    result = _split_query("1. Hardware 2. Software 3. Compare")
    assert len(result) == 3


def test_split_query_sentence_boundary():
    result = _split_query("First analyze hardware. Then compare software.")
    assert len(result) == 2


def test_split_query_empty_semicolons():
    assert _split_query(";") == []


# ── _parse_llm_output ─────────────────────────────────────────────────────


def test_parse_llm_output_valid_single_node():
    data = {
        "nodes": [
            {"title": "R", "question": "Q", "rationale": "r", "risk_level": "low"}
        ],
        "dependencies": [],
    }
    plan = _parse_llm_output(data, "query")
    assert plan is not None
    assert len(plan.nodes) == 1
    assert plan.nodes[0].risk_level == RiskLevel.LOW


def test_parse_llm_output_empty_nodes():
    assert _parse_llm_output({"nodes": [], "dependencies": []}, "t") is None


def test_parse_llm_output_missing_nodes():
    assert _parse_llm_output({"dependencies": []}, "t") is None


def test_parse_llm_output_two_nodes_with_dep():
    data = {
        "nodes": [
            {"title": "A", "question": "Q", "rationale": "r", "risk_level": "low"},
            {"title": "B", "question": "Q2", "rationale": "r2", "risk_level": "medium"},
        ],
        "dependencies": [{"from": 0, "to": 1}],
    }
    plan = _parse_llm_output(data, "t")
    assert plan is not None
    assert len(plan.dependencies) == 1


def test_parse_llm_output_invalid_dep_ignored():
    data = {
        "nodes": [
            {"title": "A", "question": "Q", "rationale": "r", "risk_level": "low"}
        ],
        "dependencies": [{"from": 0, "to": 99}],
    }
    plan = _parse_llm_output(data, "t")
    assert plan is not None
    assert len(plan.dependencies) == 0


# ── _deterministic_plan edge cases ────────────────────────────────────────


def test_deterministic_plan_empty_split():
    plan = _deterministic_plan(";")
    assert len(plan.nodes) == 1


def test_deterministic_plan_sequential_deps():
    plan = _deterministic_plan("A; B; C")
    assert len(plan.nodes) == 3
    assert len(plan.dependencies) == 2


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 — B1-3: Serialization — plan_to_markdown Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


def test_markdown_export_with_assumptions():
    """plan_to_markdown mit assumptions → Assumptions-Sektion (lines 144-147)."""
    plan = generate_plan("Q")
    plan.assumptions = ["Assume X", "Assume Y"]
    md = plan_to_markdown(plan)
    assert "## Assumptions" in md
    assert "- Assume X" in md
    assert "- Assume Y" in md


def test_markdown_export_with_constraints():
    """plan_to_markdown mit constraints → Constraints-Sektion (lines 150-153)."""
    plan = generate_plan("Q")
    plan.constraints = ["Local only", "No cloud"]
    md = plan_to_markdown(plan)
    assert "## Constraints" in md
    assert "- Local only" in md


def test_markdown_export_with_approved_info():
    """plan_to_markdown mit approved_at → Approved-Zeile (line 140)."""
    plan = generate_plan("Q")
    plan.approved_at = "2024-01-01T00:00:00"
    plan.approved_by = "tester"
    md = plan_to_markdown(plan)
    assert "**Approved:** 2024-01-01T00:00:00 by tester" in md


def test_markdown_export_node_not_in_order():
    """plan_to_markdown: node_id in order aber nicht in nodes_by_id → continue (line 167)."""
    from unittest.mock import patch

    plan = generate_plan("Q")
    # Mock get_topological_order (imported from validation into serialization's scope)
    # to return a list with a non-existent ID
    with patch(
        "research_planner.validation.get_topological_order",
        return_value=["fake_id_999", plan.nodes[0].node_id],
    ):
        md = plan_to_markdown(plan)
        assert plan.nodes[0].title in md
        assert "fake_id_999" not in md  # skipped via continue


def test_markdown_export_with_expected_sources():
    """plan_to_markdown: node hat expected_sources (line 179)."""
    plan = generate_plan("Q")
    plan.nodes[0].expected_sources = ["arxiv.org", "ieee.org"]
    md = plan_to_markdown(plan)
    assert "**Expected sources:**" in md
    assert "arxiv.org" in md


def test_markdown_export_empty_assumptions_and_constraints():
    """plan_to_markdown mit leeren Listen → keine Assumptions/Constraints-Sektion."""
    plan = generate_plan("Q")
    plan.assumptions = []
    plan.constraints = []
    md = plan_to_markdown(plan)
    assert "## Assumptions" not in md
    assert "## Constraints" not in md


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 — B1-4: models.py + validation.py + approval.py Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


def test_research_node_empty_node_id_raises():
    """ResearchNode mit leerem/whitespace node_id → ValueError (line 53)."""
    with pytest.raises(ValueError, match="node_id must not be empty"):
        ResearchNode(node_id="   ", title="T", question="Q")


def test_plan_get_node_found():
    """get_node gibt Node zurück wenn ID existiert (lines 118-121)."""
    plan = generate_plan("Q")
    node = plan.get_node(plan.nodes[0].node_id)
    assert node is not None
    assert node.node_id == plan.nodes[0].node_id


def test_plan_get_node_not_found():
    """get_node gibt None zurück wenn ID nicht existiert (lines 118-121)."""
    plan = generate_plan("Q")
    node = plan.get_node("nonexistent_id")
    assert node is None


def test_dag_dependency_to_node_missing():
    """Dependency to_node nicht im Plan → DAGValidationError (lines 42-43)."""
    plan = ResearchPlan(query="Test")
    n = ResearchNode(title="A", question="Q")
    plan.add_node(n)
    plan.add_dependency(n.node_id, "nonexistent")

    with pytest.raises(DAGValidationError, match="to_node"):
        validate_plan(plan)


def test_node_depends_on_nonexistent():
    """Node depends_on nicht-existente ID → DAGValidationError (lines 51-53)."""
    plan = ResearchPlan(query="Test")
    n = ResearchNode(title="A", question="Q", depends_on=["nonexistent"])
    plan.add_node(n)

    with pytest.raises(DAGValidationError, match="depends_on non-existent"):
        validate_plan(plan)


def test_node_depends_on_self():
    """Node depends_on auf sich selbst → DAGValidationError (lines 55-57)."""
    plan = ResearchPlan(query="Test")
    n = ResearchNode(title="A", question="Q")
    plan.add_node(n)
    # Add the depends_on directly (not via add_dependency which checks differently)
    n.depends_on.append(n.node_id)

    with pytest.raises(DAGValidationError, match="cannot depend on itself"):
        validate_plan(plan)


def test_approve_plan_idempotent():
    """approve_plan auf bereits approved Plan → idempotent return (line 23)."""
    plan = generate_plan("Q")
    approve_plan(plan, approved_by="tester")
    first_approved_at = plan.approved_at
    # Second call should be idempotent — no state change
    approve_plan(plan, approved_by="another")
    assert plan.approved_at == first_approved_at
    assert plan.approved_by == "tester"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 — B1-1: LLM-API-Pfade (_llm_plan + generate_plan LLM)
# ═══════════════════════════════════════════════════════════════════════════
# NOTE: requests is imported lazily inside _llm_plan(), so we patch
# requests.post globally, NOT research_planner.planner.requests.


def test_llm_plan_successful_call_returns_research_plan():
    """LLM-Call erfolgreich → valides JSON → ResearchPlan."""
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"nodes": [{"title": "T", "question": "Q", '
                    '"rationale": "r", "risk_level": "low"}], '
                    '"dependencies": []}'
                }
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        plan = generate_plan("Test query", use_llm=True, llm_base_url="http://x:1/v1")
        assert plan is not None
        assert len(plan.nodes) >= 1
        assert plan.status == ResearchPlanStatus.DRAFT


def test_llm_plan_timeout_returns_none():
    """LLM-Call Timeout → _llm_plan returns None → fallback deterministic."""
    from unittest.mock import patch

    import requests as real_requests

    with patch(
        "requests.post",
        side_effect=real_requests.exceptions.Timeout("timed out"),
    ):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None
        assert len(plan.nodes) >= 1  # deterministic fallback


def test_llm_plan_connection_error_returns_none():
    """LLM-Call ConnectionError → _llm_plan returns None."""
    from unittest.mock import patch

    import requests as real_requests

    with patch(
        "requests.post",
        side_effect=real_requests.exceptions.ConnectionError("refused"),
    ):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # fallback works


def test_llm_plan_http_error_returns_none():
    """LLM-Call HTTP-Error (raise_for_status) → _llm_plan returns None."""
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("HTTP 500")

    with patch("requests.post", return_value=mock_resp):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # fallback to deterministic


def test_llm_plan_malformed_json_returns_none():
    """LLM-Antwort mit ungültigem JSON → _llm_plan returns None."""
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "not valid json {{"}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # fallback works


def test_llm_plan_missing_choices_key_returns_none():
    """LLM-Antwort ohne choices-Key → KeyError → returns None."""
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"unexpected": "format"}
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # fallback


def test_llm_plan_requests_not_importable():
    """requests-Import schlägt fehl → _llm_plan returns None."""
    from unittest.mock import patch

    import builtins

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("No requests module")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # deterministic fallback


def test_llm_plan_generic_exception_returns_none():
    """LLM-Call wirft generische Exception → _llm_plan returns None."""
    from unittest.mock import patch

    with patch("requests.post", side_effect=RuntimeError("Unexpected error")):
        plan = generate_plan(
            "Test", use_llm=True, llm_base_url="http://x:1/v1", llm_timeout=0.1
        )
        assert plan is not None  # fallback


def test_generate_plan_llm_success_path():
    """generate_plan mit use_llm=True und erfolgreichem LLM-Call."""
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"nodes": ['
                    '{"title": "Step 1", "question": "Q1", '
                    '"rationale": "r1", "risk_level": "low"}, '
                    '{"title": "Step 2", "question": "Q2", '
                    '"rationale": "r2", "risk_level": "medium"}'
                    "], "
                    '"dependencies": [{"from": 0, "to": 1}]}'
                }
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        plan = generate_plan(
            "LLM test query",
            use_llm=True,
            llm_base_url="http://x:1/v1",
            language="de",
            assumptions=["A"],
            constraints=["C"],
        )
        assert plan is not None
        assert len(plan.nodes) == 2
        assert plan.language == "de"
        assert plan.assumptions == ["A"]
        assert plan.constraints == ["C"]


def test_llm_plan_parse_output_exception_returns_none():
    """_parse_llm_output wirft Exception → except-Block → returns None."""
    from unittest.mock import MagicMock, patch

    from research_planner.planner import _llm_plan

    mock_resp = MagicMock()
    # This content will parse as valid JSON but "nodes" is a string, not a list,
    # causing len() to return string length, but iterating over it will iterate
    # over characters, causing ResearchNode creation to fail
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"nodes": "not_a_list"}'}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        result = _llm_plan("Q", base_url="http://x:1/v1", timeout=0.1)
        # _parse_llm_output fails on iterating string characters → Exception
        assert result is None


def test_llm_plan_uses_default_base_url():
    """_llm_plan ohne base_url → verwendet LLAMA_SERVER_URL default (line 132)."""
    from unittest.mock import MagicMock, patch

    from research_planner.planner import _llm_plan

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"nodes": [{"title": "T", "question": "Q", '
                    '"rationale": "r", "risk_level": "low"}], '
                    '"dependencies": []}'
                }
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_resp):
        # empty base_url triggers line 132: base_url = LLAMA_SERVER_URL
        result = _llm_plan("Q", base_url="", timeout=0.1)
        assert result is not None
        assert len(result.nodes) == 1


def test_llm_plan_second_importerror_handler():
    """_llm_plan: ImportError nach erfolgreichem requests-Import (line 173)."""
    from unittest.mock import patch

    from research_planner.planner import _llm_plan

    with patch("requests.post", side_effect=ImportError("delayed import failure")):
        result = _llm_plan("Q", base_url="http://x:1/v1", timeout=0.1)
        assert result is None  # line 173 caught
