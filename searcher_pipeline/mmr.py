"""MMR — Maximal Marginal Relevance for result diversification.

Removes redundant segments and increases source diversity.
Prevents flooding the Evidence Store with nearly identical snippets.
"""

from __future__ import annotations

import math


def mmr_select(
    items: list[dict],
    *,
    k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """Select diverse items using Maximal Marginal Relevance.

    Args:
        items: List of dicts with at least 'text' and 'score' keys.
        k: Number of items to return.
        lambda_param: Trade-off between relevance (high) and diversity (low).
                      0.7 = 70% relevance, 30% diversity.

    Returns:
        Top-k diverse items.
    """
    if not items:
        return []
    if len(items) <= k:
        return items

    selected: list[dict] = []
    remaining = list(items)

    # First item: highest scored
    remaining.sort(key=lambda x: x.get("score", 0), reverse=True)
    first = remaining.pop(0)
    selected.append(first)

    while len(selected) < k and remaining:
        best_item = None
        best_score = -math.inf

        for item in remaining:
            relevance = item.get("score", 0)
            diversity = _min_similarity(item, selected)
            mmr = lambda_param * relevance - (1 - lambda_param) * diversity

            if mmr > best_score:
                best_score = mmr
                best_item = item

        if best_item:
            remaining.remove(best_item)
            selected.append(best_item)
        else:
            break

    return selected


def _min_similarity(item: dict, selected: list[dict]) -> float:
    """Compute minimum cosine-like similarity between item and any selected item."""
    min_sim = 1.0
    item_terms = set(item.get("text", "").lower().split())

    for sel in selected:
        sel_terms = set(sel.get("text", "").lower().split())
        if not item_terms or not sel_terms:
            continue
        # Jaccard similarity
        intersection = len(item_terms & sel_terms)
        union = len(item_terms | sel_terms)
        sim = intersection / union if union > 0 else 1.0
        min_sim = min(min_sim, sim)

    return min_sim


def deduplicate_texts(
    texts: list[str],
    *,
    threshold: float = 0.85,
) -> list[str]:
    """Simple Jaccard-based text deduplication."""
    result: list[str] = []
    result_sets: list[set[str]] = []

    for text in texts:
        terms = set(text.lower().split())
        is_dup = False
        for existing in result_sets:
            if not terms or not existing:
                continue
            sim = len(terms & existing) / len(terms | existing)
            if sim >= threshold:
                is_dup = True
                break
        if not is_dup:
            result.append(text)
            result_sets.append(terms)

    return result
