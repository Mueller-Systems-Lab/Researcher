"""Report Outline Generator — structural skeleton for Deep Research reports.

Produces the required section outline with metadata slots.
"""

from __future__ import annotations

REQUIRED_SECTIONS = [
    "Title",
    "Executive Summary",
    "Research Question",
    "Method / Search Plan",
    "Findings by DAG Node",
    "Evidence Table",
    "Limitations",
    "Uncertainty",
    "Source List",
    "Evaluation Summary",
]


def generate_outline(
    query: str,
    *,
    node_titles: list[str] | None = None,
    language: str = "en",
) -> list[dict]:
    """Generate a report outline with sections and content hints.

    Returns a list of section dicts with 'title' and 'placeholder'.
    """
    outline: list[dict] = []

    for section in REQUIRED_SECTIONS:
        entry: dict = {"title": section, "placeholder": ""}

        if section == "Title":
            entry["placeholder"] = f"# Deep Research Report: {query}"
        elif section == "Executive Summary":
            entry["placeholder"] = (
                "Brief summary of research findings, methodology, and key conclusions."
            )
        elif section == "Research Question":
            entry["placeholder"] = query
        elif section == "Method / Search Plan":
            entry["placeholder"] = (
                f"Research conducted using {len(node_titles or [])} planned steps."
            )
        elif section == "Findings by DAG Node":
            entry["placeholder"] = "\n".join(
                f"### {t}\n\n*Findings pending...*"
                for t in (node_titles or ["Research"])
            )
        elif section == "Evidence Table":
            entry["placeholder"] = (
                "| # | Source | Domain | Retrieved |\n"
                "|---|--------|--------|------------|\n"
            )
        elif section == "Limitations":
            entry["placeholder"] = (
                "- Scope limitations\n- Source availability\n- Model constraints"
            )
        elif section == "Uncertainty":
            entry["placeholder"] = (
                "Areas of uncertainty and confidence levels for key findings."
            )
        elif section == "Source List":
            entry["placeholder"] = "*Sources listed below.*"
        elif section == "Evaluation Summary":
            entry["placeholder"] = "*Evaluation scores pending.*"

        outline.append(entry)

    return outline
