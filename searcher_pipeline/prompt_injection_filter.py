"""Prompt Injection Filter — isolates suspicious content from fetched text.

Does NOT block content. Marks injection-risk segments so downstream
components (Report Writer, Evidence Store) can handle them safely.
Never executes injected instructions from web content.
"""

from __future__ import annotations

import re

# Known injection patterns (matching common attack vectors)
_INJECTION_PATTERNS = [
    # Override system prompts
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|directions?)",
    r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions?|training)",
    r"you\s+are\s+now\s+(a\s+)?\w+\s+(bot|assistant|agent)",
    r"new\s+(system\s+)?prompt\s*:",
    r"your\s+new\s+(role|task|job)\s+is",
    # DAN / jailbreak patterns
    r"\bDAN\b.*\b(do\s+anything\s+now|jailbreak)\b",
    r"you\s+are\s+(no\s+longer|not)\s+(an?\s+)?(AI|assistant|language\s+model)",
    # Instruction injection in text
    r"\[INST\].*\[/INST\]",
    r"<\|im_start\|>.*<\|im_end\|>",
    r"\[SYSTEM\].*\[/SYSTEM\]",
]


def detect_injection_flags(text: str) -> list[str]:
    """Detect prompt injection patterns in text.

    Returns a list of flag strings indicating what was detected.
    Empty list means no injection patterns found.
    """
    flags: list[str] = []
    text_lower = text.lower()

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            flags.append(f"injection_pattern:{pattern[:40]}")

    return flags


def is_suspicious(text: str) -> bool:
    """Quick check: does the text contain any injection patterns?"""
    return len(detect_injection_flags(text)) > 0


def sanitize_for_safe_display(text: str) -> str:
    """Neutralize injection content for safe display in reports.

    Replaces known injection tokens with safe markers.
    Does NOT modify the original stored evidence.
    """
    safe = text
    safe = re.sub(
        r"\[INST\].*?\[/INST\]",
        "[INJECTION_BLOCKED]",
        safe,
        flags=re.IGNORECASE | re.DOTALL,
    )
    safe = re.sub(
        r"<\|im_start\|>.*?<\|im_end\|>",
        "[INJECTION_BLOCKED]",
        safe,
        flags=re.IGNORECASE | re.DOTALL,
    )
    safe = re.sub(
        r"\[SYSTEM\].*?\[/SYSTEM\]",
        "[INJECTION_BLOCKED]",
        safe,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return safe
