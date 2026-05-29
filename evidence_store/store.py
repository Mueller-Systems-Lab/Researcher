"""Evidence Store — JSONL-based persistence for sources and segments.

Storage layout:
    reports/deep_research/evidence/sources.jsonl
    reports/deep_research/evidence/segments.jsonl
    reports/deep_research/evidence/citations.jsonl

No database migration — append-only JSONL files.
Thread-safe via threading.Lock + atomic writes.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from evidence_store.models import Citation, EvidenceSegment, EvidenceSource

EVIDENCE_DIR = Path("reports/deep_research/evidence")

_lock = threading.Lock()


def _ensure_dir() -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return EVIDENCE_DIR


def _safe_append(path: Path, line: str) -> None:
    """Thread-safe JSONL append."""
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


# ── Sources ──────────────────────────────────────────────────────────────


def save_source(source: EvidenceSource) -> None:
    """Save a single EvidenceSource to the sources JSONL file."""
    _ensure_dir()
    path = EVIDENCE_DIR / "sources.jsonl"
    record = {
        "source_id": source.source_id,
        "url": source.url,
        "canonical_url": source.canonical_url,
        "title": source.title,
        "domain": source.domain,
        "retrieved_at": source.retrieved_at,
        "robots_status": source.robots_status,
        "cache_status": source.cache_status,
        "content_hash": source.content_hash,
        "run_id": source.run_id,
    }
    _safe_append(path, json.dumps(record, ensure_ascii=False))


def load_sources() -> list[EvidenceSource]:
    """Load all sources from the store."""
    _ensure_dir()
    path = EVIDENCE_DIR / "sources.jsonl"
    if not path.exists():
        return []

    sources: list[EvidenceSource] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        data = json.loads(line)
        sources.append(
            EvidenceSource(
                source_id=data["source_id"],
                url=data["url"],
                canonical_url=data.get("canonical_url", data["url"]),
                title=data.get("title", ""),
                domain=data.get("domain", ""),
                retrieved_at=data.get("retrieved_at", ""),
                robots_status=data.get("robots_status", "unknown"),
                cache_status=data.get("cache_status", "miss"),
                content_hash=data.get("content_hash", ""),
                run_id=data.get("run_id", ""),
            )
        )
    return sources


def load_sources_by_run_id(run_id: str) -> list[EvidenceSource]:
    """Load all sources scoped to a specific run ID."""
    return [s for s in load_sources() if s.run_id == run_id]


def find_source_by_url(url: str) -> EvidenceSource | None:
    """Find a source by its canonical URL."""
    for s in load_sources():
        if s.url == url or s.canonical_url == url:
            return s
    return None


# ── Segments ─────────────────────────────────────────────────────────────


def save_segment(segment: EvidenceSegment) -> None:
    """Save a single EvidenceSegment to the segments JSONL file."""
    _ensure_dir()
    path = EVIDENCE_DIR / "segments.jsonl"
    record = {
        "segment_id": segment.segment_id,
        "source_id": segment.source_id,
        "text": segment.text,
        "normalized_text": segment.normalized_text,
        "quote_safe_text": segment.quote_safe_text,
        "section": segment.section,
        "position": segment.position,
        "score": segment.score,
        "mmr_group": segment.mmr_group,
        "injection_flags": segment.injection_flags,
    }
    _safe_append(path, json.dumps(record, ensure_ascii=False))


def load_segments() -> list[EvidenceSegment]:
    """Load all segments from the store."""
    _ensure_dir()
    path = EVIDENCE_DIR / "segments.jsonl"
    if not path.exists():
        return []

    segments: list[EvidenceSegment] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        data = json.loads(line)
        segments.append(
            EvidenceSegment(
                segment_id=data["segment_id"],
                source_id=data["source_id"],
                text=data["text"],
                normalized_text=data.get("normalized_text", ""),
                quote_safe_text=data.get("quote_safe_text", ""),
                section=data.get("section", ""),
                position=data.get("position", 0),
                score=data.get("score", 0.0),
                mmr_group=data.get("mmr_group", ""),
                injection_flags=data.get("injection_flags", []),
            )
        )
    return segments


def find_segments_for_source(source_id: str) -> list[EvidenceSegment]:
    """Find all segments belonging to a source."""
    return [s for s in load_segments() if s.source_id == source_id]


# ── Citations ────────────────────────────────────────────────────────────


def save_citation(citation: Citation) -> None:
    """Save a single Citation to the citations JSONL file."""
    _ensure_dir()
    path = EVIDENCE_DIR / "citations.jsonl"
    record = {
        "citation_id": citation.citation_id,
        "segment_id": citation.segment_id,
        "label": citation.label,
        "quote": citation.quote,
        "url": citation.url,
        "retrieved_at": citation.retrieved_at,
    }
    _safe_append(path, json.dumps(record, ensure_ascii=False))


def load_citations() -> list[Citation]:
    """Load all citations from the store."""
    _ensure_dir()
    path = EVIDENCE_DIR / "citations.jsonl"
    if not path.exists():
        return []

    citations: list[Citation] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        data = json.loads(line)
        citations.append(
            Citation(
                citation_id=data["citation_id"],
                segment_id=data["segment_id"],
                label=data.get("label", ""),
                quote=data.get("quote", ""),
                url=data.get("url", ""),
                retrieved_at=data.get("retrieved_at", ""),
            )
        )
    return citations
