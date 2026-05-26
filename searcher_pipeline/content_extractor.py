"""Content Extractor — extracts readable text from HTML content.

Basic HTML → text extraction without external dependencies.
Strips scripts, styles, and normalizes whitespace.
"""

from __future__ import annotations

import re


def extract_text(html: str) -> str:
    """Extract readable text from HTML content.

    Removes script/style tags, decodes entities, normalizes whitespace.
    """
    if not html or not html.strip():
        return ""

    # Remove script and style elements
    text = re.sub(
        r"<(script|style|noscript|iframe|svg)[^>]*>.*?</\1>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = _decode_entities(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def extract_metadata(html: str) -> dict[str, str]:
    """Extract basic metadata from HTML (title, description)."""
    meta: dict[str, str] = {}

    # Title
    title_match = re.search(
        r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
    )
    if title_match:
        meta["title"] = extract_text(title_match.group(1))

    # Meta description
    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if desc_match:
        meta["description"] = desc_match.group(1)

    return meta


def _decode_entities(text: str) -> str:
    """Decode common HTML entities."""
    entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&nbsp;": " ",
        "&auml;": "ä",
        "&ouml;": "ö",
        "&uuml;": "ü",
        "&Auml;": "Ä",
        "&Ouml;": "Ö",
        "&Uuml;": "Ü",
        "&szlig;": "ß",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    # Numeric entities
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
    return text
