"""Evidence data models — DR-05: Evidence Store + Citation Model.

EvidenceSource — the origin of a piece of evidence (URL, domain, retrieval metadata).
EvidenceSegment — a specific text excerpt from a source.
Citation — a labeled reference [S1], [S2] linking a segment to report text.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class EvidenceSource:
    """A retrieved web source with retrieval metadata."""

    url: str
    canonical_url: str = ""
    title: str = ""
    domain: str = ""
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    robots_status: str = "unknown"
    cache_status: str = "miss"
    content_hash: str = ""
    source_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("url must not be empty")
        if not self.retrieved_at:
            raise ValueError("retrieved_at must not be empty")
        if not self.canonical_url:
            self.canonical_url = self.url
        if not self.domain:
            self.domain = _extract_domain(self.url)
        if not self.content_hash and self.url:
            self.content_hash = hashlib.sha256(self.url.encode()).hexdigest()[:16]


@dataclass
class EvidenceSegment:
    """A text excerpt from a source, ready for citation."""

    source_id: str
    text: str
    normalized_text: str = ""
    quote_safe_text: str = ""
    section: str = ""
    position: int = 0
    score: float = 0.0
    mmr_group: str = ""
    injection_flags: list[str] = field(default_factory=list)
    segment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.normalized_text:
            self.normalized_text = self.text.strip().lower()
        if not self.quote_safe_text:
            self.quote_safe_text = _make_quote_safe(self.text)


@dataclass
class Citation:
    """A labeled reference linking a segment to a report."""

    segment_id: str
    label: str  # e.g., "[S1]"
    quote: str = ""
    url: str = ""
    retrieved_at: str = ""
    citation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if not self.segment_id.strip():
            raise ValueError("segment_id must not be empty")
        if not self.label:
            self.label = f"[{self.citation_id[:4].upper()}]"


# ── Helpers ──────────────────────────────────────────────────────────────


def _extract_domain(url: str) -> str:
    """Extract domain from URL (basic)."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc or parsed.hostname or ""
    except Exception:
        return ""


def _make_quote_safe(text: str) -> str:
    """Normalize text for safe quoting: strip control chars, limit length."""
    import re

    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    cleaned = cleaned.strip()
    if len(cleaned) > 2000:
        cleaned = cleaned[:1997] + "..."
    return cleaned
