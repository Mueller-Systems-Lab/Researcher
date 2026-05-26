"""Citation management — create, label, and validate citations from evidence.

Rule: Citations MUST only reference EvidenceSegments that exist in the store.
No citation without evidence. No reports citing unverified web text.
"""

from __future__ import annotations

from evidence_store.models import Citation, EvidenceSegment


def create_citation(
    segment: EvidenceSegment,
    *,
    label: str | None = None,
    url: str = "",
    retrieved_at: str = "",
    quote: str | None = None,
) -> Citation:
    """Create a Citation from an EvidenceSegment.

    Args:
        segment: The evidence segment to cite.
        label: Optional citation label (e.g., "[S1]"). Auto-generated if None.
        url: URL of the original source (for display).
        retrieved_at: Retrieval timestamp (for traceability).
        quote: Specific quote text from the segment.

    Returns:
        A validated Citation linked to the segment.
    """
    if label is None:
        label = f"[{segment.segment_id[:4].upper()}]"

    return Citation(
        segment_id=segment.segment_id,
        label=label,
        quote=quote or segment.quote_safe_text,
        url=url,
        retrieved_at=retrieved_at,
    )


def generate_citation_labels(
    segments: list[EvidenceSegment],
) -> dict[str, str]:
    """Generate sequential citation labels [S1], [S2], ... for segments.

    Returns a dict mapping segment_id → label.
    """
    labels: dict[str, str] = {}
    for idx, seg in enumerate(segments, 1):
        labels[seg.segment_id] = f"[S{idx}]"
    return labels


def validate_citation_references_segment(
    citation: Citation, segments: list[EvidenceSegment]
) -> bool:
    """Verify that a citation references an existing segment."""
    return any(seg.segment_id == citation.segment_id for seg in segments)
