"""Approval gate for ResearchPlan — Human-in-the-loop enforcement.

DR-01 Rule: No orchestrator may start without status=approved.
"""

from __future__ import annotations

from datetime import UTC, datetime

from research_planner.models import ResearchPlan, ResearchPlanStatus


class PlanNotApprovedError(RuntimeError):
    """Raised when an operation requires an approved plan but status != APPROVED."""


def approve_plan(plan: ResearchPlan, approved_by: str = "user") -> None:
    """Approve a ResearchPlan for execution.

    Sets status to APPROVED and records approval metadata.
    """
    if plan.status == ResearchPlanStatus.APPROVED:
        return  # idempotent

    plan.status = ResearchPlanStatus.APPROVED
    plan.approved_at = datetime.now(UTC).isoformat()
    plan.approved_by = approved_by
    plan.touch()


def assert_plan_approved(plan: ResearchPlan) -> None:
    """Assert that a plan is approved. Raises PlanNotApprovedError otherwise."""
    if plan.status != ResearchPlanStatus.APPROVED:
        raise PlanNotApprovedError(
            f"Plan '{plan.plan_id}' has status '{plan.status.value}'. "
            f"Only '{ResearchPlanStatus.APPROVED.value}' plans may be started."
        )


def is_plan_approved(plan: ResearchPlan) -> bool:
    """Check if a plan is approved (non-raising)."""
    return plan.status == ResearchPlanStatus.APPROVED


def revoke_approval(plan: ResearchPlan) -> None:
    """Revert an approved plan back to draft status."""
    plan.status = ResearchPlanStatus.DRAFT
    plan.approved_at = None
    plan.approved_by = None
    plan.touch()
