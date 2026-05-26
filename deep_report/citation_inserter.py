"""Citation Inserter — embeds inline citations [S1], [S2] into report text.

Rules:
- Every central claim needs a citation
- No citations without Evidence Store segments
- No invented sources
- Prompt-injection content neutralized, not executed
"""

from __future__ import annotations


def insert_citations(
    text: str,
    citations: list[dict],
    *,
    format_label: str = "[S{idx}]",
) -> str:
    """Insert citation markers into text after key sentences.

    Args:
        text: The report text to enhance with citations.
        citations: List of citation dicts with 'label', 'quote', 'url', 'segment_id'.
        format_label: Format string for citation labels.

    Returns:
        Text with inline citation markers appended.
    """
    if not citations:
        return text

    lines = text.split("\n")
    result: list[str] = []

    for line in lines:
        result.append(line)
        # Find sentences that match citation quotes (fuzzy)
        for cite in citations:
            quote = cite.get("quote", "")
            if quote and _fuzzy_contains(line, quote):
                label = cite.get("label", "")
                if label and label not in line:
                    result[-1] = f"{line} {label}"

    return "\n".join(result)


def generate_source_table(sources: list[dict]) -> str:
    """Generate a Markdown source table for the Evidence Table section.

    Args:
        sources: List with 'source_id', 'url', 'domain', 'retrieved_at', 'title'.
    """
    if not sources:
        return "*No sources available.*"

    lines = [
        "| # | Source | Domain | Retrieved |",
        "|---|--------|--------|------------|",
    ]
    for idx, src in enumerate(sources, 1):
        title = src.get("title", src.get("url", "Unknown"))
        domain = src.get("domain", "-")
        retrieved = src.get("retrieved_at", "-")[:10]
        lines.append(f"| {idx} | {title[:60]} | {domain[:30]} | {retrieved} |")

    return "\n".join(lines)


def generate_source_list(sources: list[dict]) -> str:
    """Generate a numbered source list with URLs."""
    if not sources:
        return "*No sources.*"

    lines: list[str] = []
    for idx, src in enumerate(sources, 1):
        url = src.get("url", "")
        title = src.get("title", url)
        lines.append(f"[S{idx}] **{title}** — {url}")

    return "\n".join(lines)


def _fuzzy_contains(text: str, quote: str, threshold: float = 0.6) -> bool:
    """Check if text contains the quote with fuzzy matching."""
    if quote in text:
        return True
    # Simple word overlap check
    quote_words = set(quote.lower().split())
    text_words = set(text.lower().split())
    if not quote_words:
        return False
    overlap = len(quote_words & text_words) / len(quote_words)
    return overlap >= threshold
