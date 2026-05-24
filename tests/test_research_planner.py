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
)
from research_planner.planner import generate_plan
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
