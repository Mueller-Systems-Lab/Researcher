"""Hybrid Planner — decomposes a user query into a ResearchPlan DAG.

Strategy:
1. Deterministic rule/template-based decomposition (baseline, always available).
2. Optional local LLM refinement via llama-server (if available).
3. Falls back to deterministic planner on timeout, failure, or invalid JSON.
"""

from __future__ import annotations

import json
import logging
import re
import time

from config.services import LLAMA_SERVER_URL, OLLAMA_CHAT_MODEL
from research_planner.models import (
    ResearchNode,
    ResearchPlan,
    RiskLevel,
)
from research_planner.validation import validate_plan

logger = logging.getLogger(__name__)

# ── Deterministic Planner ────────────────────────────────────────────────


def _deterministic_plan(
    query: str,
    language: str = "unknown",
    assumptions: list[str] | None = None,
    constraints: list[str] | None = None,
) -> ResearchPlan:
    """Generate a basic ResearchPlan from a query using template decomposition.

    Splits compound questions by common delimiters/conjunctions and creates
    one ResearchNode per sub-question with sequential dependencies.
    """
    plan = ResearchPlan(
        query=query,
        language=language,
        assumptions=assumptions or [],
        constraints=constraints or [],
    )

    sub_questions = _split_query(query)

    if not sub_questions:
        # Fallback: single-node plan
        sub_questions = [query.strip()]

    nodes: list[ResearchNode] = []
    for idx, sub_q in enumerate(sub_questions):
        node = ResearchNode(
            title=f"Research Step {idx + 1}",
            question=sub_q.strip(),
            rationale=f"Decomposed from user query: {query[:80]}...",
            risk_level=RiskLevel.UNKNOWN,
        )
        nodes.append(node)

    # Create sequential dependencies: step 1 → step 2 → step 3 → ...
    for i in range(1, len(nodes)):
        nodes[i].depends_on.append(nodes[i - 1].node_id)
        plan.add_dependency(nodes[i - 1].node_id, nodes[i].node_id)

    for node in nodes:
        plan.add_node(node)

    plan.touch()
    return plan


def _split_query(query: str) -> list[str]:
    """Split a compound query into sub-questions.

    Detects common separators: ';', numbered lists, conjunctions.
    """
    # Try semicolon/pipe splitting first
    parts = re.split(r"\s*[;|]\s*", query)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # German conjunctions that indicate separate topics
    de_conj = (
        r"\s+(?:und\s+bestimme|und\s+vergleiche|und\s+analysiere|"
        r"und\s+bewerte|sowie|bzw\.|beziehungsweise)\s+"
    )
    parts = re.split(de_conj, query, flags=re.IGNORECASE)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # English conjunctions
    en_conj = (
        r"\s+(?:and\s+determine|and\s+compare|"
        r"and\s+analyze|and\s+evaluate|as well as)\s+"
    )
    parts = re.split(en_conj, query, flags=re.IGNORECASE)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    # Numbered list: "1. ... 2. ..."
    numbered = re.findall(r"\d+\.\s*(.+?)(?=\s*\d+\.\s|$)", query)
    if len(numbered) > 1:
        return [n.strip() for n in numbered if n.strip()]

    # Sentence boundary split: ". " or "? " followed by capital letter
    sentence_parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", query)
    if len(sentence_parts) > 1:
        return [p.strip() for p in sentence_parts if p.strip()]

    # Single question
    return [query.strip()]


# ── Optional LLM Planner ─────────────────────────────────────────────────


def _llm_plan(
    query: str,
    base_url: str = "",
    model: str = "",
    timeout: float = 30.0,
) -> ResearchPlan | None:
    """Try to generate a richer plan using a local LLM via OpenAI-compatible API.

    Uses LLAMA_SERVER_URL and OLLAMA_CHAT_MODEL from centralized config
    as defaults. Returns None on any failure — caller falls back to
    deterministic planner.
    """
    if not base_url:
        base_url = LLAMA_SERVER_URL
    if not model:
        model = OLLAMA_CHAT_MODEL
    try:
        import requests
    except ImportError:
        logger.warning("LLM planner: requests not available — cannot call %s", base_url)
        return None

    prompt = _build_llm_prompt(query)

    try:
        logger.info(
            "LLM planner calling %s with model %s (timeout=%ss)",
            base_url,
            model,
            timeout,
        )
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a research planning assistant. "
                            "Output ONLY valid JSON. "
                            "No explanations, no markdown fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except ImportError:
        return None
    except requests.exceptions.Timeout:
        logger.warning("LLM planner request timed out (%ss) for %s", timeout, base_url)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning(
            "LLM planner connection refused at %s — is llama-server running?", base_url
        )
        return None
    except Exception as exc:
        logger.warning("LLM planner request failed: %s (%s)", type(exc).__name__, exc)
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except (KeyError, json.JSONDecodeError, IndexError) as exc:
        logger.warning("LLM planner response parse failed: %s", exc)
        return None

    return _parse_llm_output(data, query)


def _build_llm_prompt(query: str) -> str:
    return f"""Decompose this research question into a DAG of sub-questions.

Research question: {query}

Output JSON with this exact structure:
{{
  "nodes": [
    {{
      "title": "short title",
      "question": "detailed sub-question",
      "rationale": "why this step is needed",
      "depends_on": [],
      "risk_level": "low|medium|high|unknown"
    }}
  ],
  "dependencies": [
    {{"from": "node_index_0", "to": "node_index_1"}}
  ]
}}

Rules:
- Use array indices for depends_on and dependencies (0-based)
- At least 3 nodes for a complex question
- Last node should synthesize findings
- Dependencies must form a valid DAG (no cycles)
- Include risk_level for each node"""


def _parse_llm_output(data: dict, query: str) -> ResearchPlan | None:
    """Convert LLM JSON output into a validated ResearchPlan."""
    try:
        raw_nodes = data.get("nodes", [])
        raw_deps = data.get("dependencies", [])

        if len(raw_nodes) < 1:
            return None

        plan = ResearchPlan(query=query, language="unknown")
        nodes: list[ResearchNode] = []

        for rn in raw_nodes:
            node = ResearchNode(
                title=str(rn.get("title", "Untitled")),
                question=str(rn.get("question", "")),
                rationale=str(rn.get("rationale", "")),
                risk_level=_parse_risk(str(rn.get("risk_level", "unknown"))),
            )
            nodes.append(node)

        # Resolve index-based dependencies to node IDs
        for dep in raw_deps:
            from_idx = int(dep.get("from", -1))
            to_idx = int(dep.get("to", -1))
            if 0 <= from_idx < len(nodes) and 0 <= to_idx < len(nodes):
                nodes[to_idx].depends_on.append(nodes[from_idx].node_id)
                plan.add_dependency(nodes[from_idx].node_id, nodes[to_idx].node_id)

        for node in nodes:
            plan.add_node(node)

        # Validate the generated DAG
        validate_plan(plan)
        plan.touch()
        return plan

    except Exception as exc:
        logger.warning("LLM plan parsing failed: %s", exc)
        return None


def _parse_risk(raw: str) -> RiskLevel:
    try:
        return RiskLevel(raw.lower().strip())
    except ValueError:
        return RiskLevel.UNKNOWN


# ── Public API ───────────────────────────────────────────────────────────


def generate_plan(
    query: str,
    *,
    language: str = "unknown",
    assumptions: list[str] | None = None,
    constraints: list[str] | None = None,
    use_llm: bool = False,
    llm_base_url: str = "",
    llm_model: str = "",
    llm_timeout: float = 30.0,
) -> ResearchPlan:
    """Generate a validated ResearchPlan from a user query.

    Args:
        query: The research question to decompose.
        language: Hint for language-specific decomposition ('de', 'en', 'unknown').
        assumptions: Known assumptions to include in the plan.
        constraints: Known constraints (e.g., local-first, no cloud).
        use_llm: If True, attempt LLM-based planning with deterministic fallback.
        llm_base_url: llama-server base URL for LLM planning.
        llm_model: Model name for LLM planning.
        llm_timeout: Timeout in seconds for LLM planning.

    Returns:
        A validated ResearchPlan with status DRAFT.
    """
    plan: ResearchPlan | None = None

    if use_llm:
        logger.info("Attempting LLM-based plan generation...")
        plan = _llm_plan(
            query, base_url=llm_base_url, model=llm_model, timeout=llm_timeout
        )
        if plan is not None:
            plan.language = language
            plan.assumptions = assumptions or []
            plan.constraints = constraints or []
            logger.info(
                "LLM plan generated successfully with %d nodes.", len(plan.nodes)
            )

    if plan is None:
        logger.info("Using deterministic planner for query.")
        plan = _deterministic_plan(
            query, language=language, assumptions=assumptions, constraints=constraints
        )

    # Ensure the plan validates
    validate_plan(plan)
    return plan
