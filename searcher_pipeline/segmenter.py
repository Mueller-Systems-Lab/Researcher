"""Text Segmenter — splits extracted content into structured segments.

Each segment carries metadata: section, position, score.
Designed to feed EvidenceSegment creation in the Evidence Store.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextSegment:
    """A text segment with structural metadata."""

    text: str
    section: str = ""
    position: int = 0
    score: float = 0.0
    heading: str = ""


def segment_text(content: str, source_url: str = "") -> list[TextSegment]:
    """Split text content into segments by paragraph/section boundaries.

    Preserves structural context (headings, sections) as metadata.
    """
    if not content.strip():
        return []

    segments: list[TextSegment] = []
    current_section = ""
    current_heading = ""

    # Split by double newlines (paragraphs) or heading markers
    # Try to detect headings first
    lines = content.split("\n")
    pos = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect heading-like lines (all caps, short, or starting with #)
        if _is_heading(line):
            current_heading = line
            current_section = line
            continue

        # Paragraph-level segments
        sentences = re.split(r"(?<=[.!?])\s+", line)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # skip very short fragments
                continue

            segments.append(
                TextSegment(
                    text=sentence,
                    section=current_section,
                    heading=current_heading,
                    position=pos,
                )
            )
            pos += 1

    return segments


def segment_with_metadata(content: str, source_url: str = "") -> list[dict]:
    """Segment text and return dicts suitable for EvidenceSegment creation."""
    raw = segment_text(content, source_url)
    return [
        {
            "text": seg.text,
            "section": seg.section,
            "position": seg.position,
            "score": seg.score,
        }
        for seg in raw
    ]


def _is_heading(line: str) -> bool:
    """Heuristic: detect if a line is a heading."""
    if line.startswith("#"):
        return True
    if len(line) < 80 and line.isupper():
        return True
    # Markdown heading without #
    if re.match(r"^[A-ZÄÖÜ][^.!?]{5,60}$", line):
        return len(line.split()) <= 8
    return False
