"""Deduplication for Evidence Store — detects duplicate sources and segments.

Uses content hashes and normalized text comparison.
"""

from __future__ import annotations

import hashlib

from evidence_store.models import EvidenceSegment, EvidenceSource


def hash_source(source: EvidenceSource) -> str:
    """Compute a stable content hash for a source."""
    payload = f"{source.canonical_url}|{source.retrieved_at}|{source.title}"
    return hashlib.sha256(payload.encode()).hexdigest()


def hash_segment(segment: EvidenceSegment) -> str:
    """Compute a stable content hash for a segment."""
    payload = f"{segment.source_id}|{segment.normalized_text}"
    return hashlib.sha256(payload.encode()).hexdigest()


def is_duplicate_source(
    candidate: EvidenceSource, existing: list[EvidenceSource]
) -> bool:
    """Check if a source already exists in the store.

    Matches by canonical_url equality first, then content hash.
    """
    candidate_hash = candidate.content_hash
    for s in existing:
        if s.canonical_url == candidate.canonical_url:
            return True
        if s.content_hash and s.content_hash == candidate_hash:
            return True
    return False


def is_duplicate_segment(
    candidate: EvidenceSegment,
    existing: list[EvidenceSegment],
    *,
    threshold: float = 0.95,
) -> bool:
    """Check if a segment is a near-duplicate of any existing segment.

    Uses normalized text overlap ratio for fuzzy matching.
    """
    candidate_norm = candidate.normalized_text
    candidate_hash = hash_segment(candidate)

    for s in existing:
        # Exact hash match
        if hash_segment(s) == candidate_hash:
            return True
        # Fuzzy normalized overlap
        if _text_similarity(candidate_norm, s.normalized_text) >= threshold:
            return True

    return False


def deduplicate_sources(
    candidates: list[EvidenceSource],
    existing: list[EvidenceSource] | None = None,
) -> list[EvidenceSource]:
    """Filter out duplicate sources, returning only new ones."""
    if existing is None:
        from evidence_store.store import load_sources

        existing = load_sources()

    result: list[EvidenceSource] = []
    seen_urls: set[str] = set()

    for s in existing:
        seen_urls.add(s.canonical_url)

    for c in candidates:
        if c.canonical_url not in seen_urls:
            seen_urls.add(c.canonical_url)
            result.append(c)

    return result


def deduplicate_segments(
    candidates: list[EvidenceSegment],
    existing: list[EvidenceSegment] | None = None,
) -> list[EvidenceSegment]:
    """Filter out duplicate/near-duplicate segments."""
    if existing is None:
        from evidence_store.store import load_segments

        existing = load_segments()

    result: list[EvidenceSegment] = []
    for c in candidates:
        if not is_duplicate_segment(c, existing + result):
            result.append(c)

    return result


def _text_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity based on word sets."""
    if not a or not b:
        return 0.0

    set_a = set(a.split())
    set_b = set(b.split())

    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    return len(intersection) / len(union)
