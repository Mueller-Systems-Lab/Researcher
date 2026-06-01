"""Tests für evidence_store — DR-05: Evidence Store + Citation Model.

Abdeckung:
- Source speichern/laden
- Segment speichern/laden
- Citation Labels stabil
- Duplicate Source/Segment erkannt
- injection flag bleibt erhalten
- quote_safe_text wird erzeugt
- JSONL Export funktioniert
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from evidence_store.citations import (
    create_citation,
    generate_citation_labels,
    validate_citation_references_segment,
)
from evidence_store.dedup import (
    deduplicate_segments,
    deduplicate_sources,
    hash_segment,
    hash_source,
    is_duplicate_segment,
    is_duplicate_source,
)
from evidence_store.models import EvidenceSegment, EvidenceSource
from evidence_store.store import (
    find_segments_for_source,
    find_source_by_url,
    load_citations,
    load_segments,
    load_sources,
    save_citation,
    save_segment,
    save_source,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_store(monkeypatch):
    """Redirect evidence store to a temp directory for each test."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr("evidence_store.store.EVIDENCE_DIR", Path(tmp) / "evidence")
    yield
    # Cleanup not strictly necessary with TemporaryDirectory


def _make_source(url: str = "https://example.com/test") -> EvidenceSource:
    return EvidenceSource(
        url=url,
        title="Test Source",
        retrieved_at="2026-05-24T00:00:00Z",
    )


def _make_segment(
    source_id: str = "src1", text: str = "Test content"
) -> EvidenceSegment:
    return EvidenceSegment(source_id=source_id, text=text)


# ── Source Tests ─────────────────────────────────────────────────────────


def test_save_and_load_source():
    """Source speichern und laden."""
    source = _make_source()
    save_source(source)

    sources = load_sources()
    assert len(sources) == 1
    assert sources[0].source_id == source.source_id
    assert sources[0].url == source.url


def test_source_has_retrieved_at():
    """Keine Quelle ohne retrieved_at (Pflichtfeld)."""
    source = _make_source()
    assert source.retrieved_at, "retrieved_at must not be empty"


def test_source_content_hash_generated():
    """Content Hash wird automatisch generiert."""
    source = _make_source()
    assert source.content_hash
    assert len(source.content_hash) > 0


def test_find_source_by_url():
    """Source über URL wiederfinden."""
    source = _make_source("https://unique.example.com/page")
    save_source(source)

    found = find_source_by_url("https://unique.example.com/page")
    assert found is not None
    assert found.source_id == source.source_id

    not_found = find_source_by_url("https://nonexistent.example.com")
    assert not_found is None


# ── Segment Tests ────────────────────────────────────────────────────────


def test_save_and_load_segment():
    """Segment speichern und laden."""
    segment = _make_segment()
    save_segment(segment)

    segments = load_segments()
    assert len(segments) == 1
    assert segments[0].segment_id == segment.segment_id


def test_segment_must_have_source_id():
    """Kein Segment ohne source_id."""
    with pytest.raises(ValueError, match="source_id"):
        EvidenceSegment(source_id="", text="content")


def test_segment_quote_safe_text_generated():
    """quote_safe_text wird automatisch erzeugt."""
    segment = _make_segment(text="Some important research finding.")
    assert segment.quote_safe_text
    assert len(segment.quote_safe_text) > 0


def test_segment_injection_flags_preserved():
    """injection_flags bleiben beim Speichern/Laden erhalten."""
    segment = _make_segment(text="Safe content")
    segment.injection_flags = ["prompt_injection_detected", "suspicious_pattern"]
    save_segment(segment)

    segments = load_segments()
    assert len(segments) == 1
    assert "prompt_injection_detected" in segments[0].injection_flags
    assert "suspicious_pattern" in segments[0].injection_flags


def test_find_segments_for_source():
    """Segmente einer Source finden."""
    source_id = "src_test_123"
    s1 = EvidenceSegment(source_id=source_id, text="Segment 1")
    s2 = EvidenceSegment(source_id=source_id, text="Segment 2")
    save_segment(s1)
    save_segment(s2)

    found = find_segments_for_source(source_id)
    assert len(found) == 2


# ── Citation Tests ───────────────────────────────────────────────────────


def test_create_citation_from_segment():
    """Citation wird aus Segment erstellt."""
    segment = _make_segment(text="Important finding.")
    citation = create_citation(segment, url="https://example.com")

    assert citation.segment_id == segment.segment_id
    assert citation.url == "https://example.com"
    assert citation.label


def test_generate_citation_labels():
    """Citation Labels [S1], [S2], ... stabil."""
    segments = [
        _make_segment(source_id="s1", text="A"),
        _make_segment(source_id="s2", text="B"),
        _make_segment(source_id="s3", text="C"),
    ]
    labels = generate_citation_labels(segments)
    assert len(labels) == 3
    # Verify sequential labels
    label_values = list(labels.values())
    assert label_values == ["[S1]", "[S2]", "[S3]"]


def test_validate_citation_references():
    """Citation-Validierung prüft Segment-Referenzen."""
    segment = _make_segment()
    citation = create_citation(segment)

    assert validate_citation_references_segment(citation, [segment]) is True
    assert validate_citation_references_segment(citation, []) is False


def test_save_and_load_citation():
    """Citation speichern und laden."""
    segment = _make_segment()
    citation = create_citation(segment, url="https://ref.example.com")
    save_citation(citation)

    citations = load_citations()
    assert len(citations) == 1
    assert citations[0].segment_id == segment.segment_id
    assert citations[0].url == "https://ref.example.com"


# ── Dedup Tests ──────────────────────────────────────────────────────────


def test_deduplicate_sources_removes_duplicates():
    """Deduplizierung entfernt doppelte Sources nach canonical_url."""
    existing = [
        EvidenceSource(
            url="https://a.com",
            canonical_url="https://a.com",
            retrieved_at="2026-01-01T00:00:00Z",
        ),
    ]
    candidates = [
        EvidenceSource(
            url="https://a.com",
            canonical_url="https://a.com",
            retrieved_at="2026-05-01T00:00:00Z",
        ),  # duplicate
        EvidenceSource(
            url="https://b.com",
            canonical_url="https://b.com",
            retrieved_at="2026-05-01T00:00:00Z",
        ),  # new
    ]
    result = deduplicate_sources(candidates, existing)
    assert len(result) == 1
    assert result[0].canonical_url == "https://b.com"


def test_is_duplicate_source_by_url():
    """is_duplicate_source erkennt URL-Duplikate."""
    existing = [_make_source("https://dup.example.com")]
    candidate = _make_source("https://dup.example.com")
    assert is_duplicate_source(candidate, existing) is True

    unique = _make_source("https://unique.example.com")
    assert is_duplicate_source(unique, existing) is False


def test_deduplicate_segments_removes_duplicates():
    """Deduplizierung entfernt doppelte Segmente."""
    existing = [
        EvidenceSegment(source_id="s1", text="The same content appears here."),
    ]
    candidates = [
        EvidenceSegment(source_id="s1", text="The same content appears here."),
        EvidenceSegment(source_id="s2", text="Completely different content."),
    ]
    result = deduplicate_segments(candidates, existing)
    assert len(result) == 1
    assert "different" in result[0].text.lower()


def test_is_duplicate_segment_fuzzy():
    """is_duplicate_segment erkennt Fuzzy-Duplikate."""
    existing = [
        EvidenceSegment(
            source_id="s1",
            text="The quick brown fox jumps over the lazy dog",
        ),
    ]
    # Nearly identical — only one word different
    candidate = EvidenceSegment(
        source_id="s1",
        text="The quick brown fox jumps over the lazy cat",
    )
    # With high threshold (0.95), this specific change should trigger
    # With word-level Jaccard: 7/9 ≈ 0.78 < 0.95 → not duplicate at 0.95
    # But exact hash match is different
    assert is_duplicate_segment(candidate, existing, threshold=0.75) is True
    assert is_duplicate_segment(candidate, existing, threshold=0.95) is False


def test_hash_segment_stable():
    """hash_segment ist deterministisch."""
    seg = _make_segment(text="Stable hash test")
    h1 = hash_segment(seg)
    h2 = hash_segment(seg)
    assert h1 == h2


def test_hash_source_stable():
    """hash_source ist deterministisch."""
    src = _make_source()
    h1 = hash_source(src)
    h2 = hash_source(src)
    assert h1 == h2


# ── Untested pure-logic dedup paths ─────────────────────────────────────


def test_is_duplicate_segment_exact_hash_match():
    """is_duplicate_segment erkennt exaktes Duplikat via Content-Hash."""
    existing = [EvidenceSegment(source_id="s1", text="Exact same.")]
    candidate = EvidenceSegment(source_id="s1", text="Exact same.")
    assert is_duplicate_segment(candidate, existing) is True


def test_is_duplicate_segment_completely_different():
    """is_duplicate_segment gibt False für verschiedene Texte."""
    existing = [EvidenceSegment(source_id="s1", text="The quick brown fox.")]
    candidate = EvidenceSegment(source_id="s2", text="A completely unrelated sentence.")
    assert is_duplicate_segment(candidate, existing) is False


def test_text_similarity_identical():
    """_text_similarity gibt 1.0 für identische Texte."""
    from evidence_store.dedup import _text_similarity

    assert _text_similarity("hello world", "hello world") == 1.0


def test_text_similarity_completely_disjoint():
    """_text_similarity gibt 0.0 für disjunkte Wörter."""
    from evidence_store.dedup import _text_similarity

    assert _text_similarity("alpha beta", "gamma delta") == 0.0


def test_text_similarity_empty_strings():
    """_text_similarity gibt 0.0 für leere Strings."""
    from evidence_store.dedup import _text_similarity

    assert _text_similarity("", "something") == 0.0
    assert _text_similarity("something", "") == 0.0


def test_text_similarity_single_word():
    """_text_similarity mit einzelnen Wörtern."""
    from evidence_store.dedup import _text_similarity

    assert _text_similarity("hello", "hello") == 1.0
    assert _text_similarity("hello", "world") == 0.0


def test_hash_segment_different_inputs():
    """hash_segment: verschiedene Inputs → verschiedene Hashes."""
    a = EvidenceSegment(source_id="s1", text="Content A")
    b = EvidenceSegment(source_id="s2", text="Content B")
    assert hash_segment(a) != hash_segment(b)


def test_hash_source_different_inputs():
    """hash_source: verschiedene Inputs → verschiedene Hashes."""
    a = _make_source(url="https://a.com")
    b = _make_source(url="https://b.com")
    assert hash_source(a) != hash_source(b)


def test_deduplicate_segments_empty():
    """deduplicate_segments mit leerer Liste → leere Liste."""
    assert deduplicate_segments([], []) == []


def test_deduplicate_sources_empty():
    """deduplicate_sources mit leerer Liste → leere Liste."""
    assert deduplicate_sources([], []) == []


def test_deduplicate_segments_intra_batch():
    """deduplicate_segments entfernt Duplikate innerhalb des Batches."""
    candidates = [
        EvidenceSegment(source_id="s1", text="Unique."),
        EvidenceSegment(source_id="s1", text="Unique."),
        EvidenceSegment(source_id="s2", text="Another."),
    ]
    result = deduplicate_segments(candidates, [])
    assert len(result) == 2


# ── Edge Cases ───────────────────────────────────────────────────────────


def test_empty_source_url_raises():
    """Source ohne URL wird abgelehnt."""
    with pytest.raises(ValueError, match="url must not be empty"):
        EvidenceSource(url="")


def test_empty_segment_text_raises():
    """Segment ohne Text wird abgelehnt."""
    with pytest.raises(ValueError, match="text must not be empty"):
        EvidenceSegment(source_id="s1", text="")


def test_load_empty_store():
    """Laden aus leerem Store gibt leere Liste."""
    assert load_sources() == []
    assert load_segments() == []
    assert load_citations() == []
