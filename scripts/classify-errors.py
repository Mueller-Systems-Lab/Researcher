#!/usr/bin/env python3
# ============================================================================
# classify-errors.py — Fehlerklassifikation aus pytest JUnit XML
# ============================================================================
# Liest JUnit XML, klassifiziert jeden Fehler in:
#   INFRA    — Infrastruktur (ConnectionError, Timeout, ImportError etc.)
#   PRODUCT  — Produktfehler (AssertionError, falsches Verhalten)
#   TEST     — Testfehler (Testcode falsch, Selektor fragil)
# ============================================================================
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


INFRA_KEYWORDS = [
    "connectionerror",
    "connectionrefused",
    "connection refused",
    "timeout",
    "timeouterror",
    "timed out",
    "importerror",
    "modulenotfound",
    "no module named",
    "cannot connect",
    "could not connect",
    "unreachable",
    "dns",
    "name resolution",
    "econnrefused",
    "econnreset",
    "broken pipe",
    "pipe",
    "eof",
    "ssl",
    "certificate",
    "permission denied",
    "eacces",
    "too many open files",
    "out of memory",
    "disk full",
    "no space",
    "docker",
    "container",
    "service unavailable",
    "503",
    "not found",
    "404",  # HTTP 404 könnte auch PRODUCT sein, aber meist INFRA
]


def classify(text: str) -> str:
    """Classify a failure based on its error text."""
    lower = text.lower()
    for kw in INFRA_KEYWORDS:
        if kw in lower:
            return "INFRA"
    if "assert" in lower or "assertionerror" in lower or "expected" in lower:
        return "PRODUCT"
    return "TEST"


def parse_junit(junit_path: str) -> list[dict]:
    """Parse JUnit XML and return list of failures with classification."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    failures = []

    for testcase in root.iter("testcase"):
        for child in testcase:
            if child.tag in ("failure", "error"):
                full_text = f"{child.get('message', '')} {child.text or ''}"
                category = classify(full_text)
                failures.append(
                    {
                        "classname": testcase.get("classname", "?"),
                        "name": testcase.get("name", "?"),
                        "category": category,
                        "message": child.get("message", "")[:200],
                    }
                )

    return failures


def print_report(failures: list[dict]) -> int:
    """Print structured report and return exit code."""
    if not failures:
        print("✅ KEINE FEHLER — alle Tests bestanden.")
        return 0

    infra = [f for f in failures if f["category"] == "INFRA"]
    product = [f for f in failures if f["category"] == "PRODUCT"]
    test = [f for f in failures if f["category"] == "TEST"]

    print(f"❌ {len(failures)} Fehler gefunden:\n")
    print(f"  INFRA    ({len(infra)}) — Infrastruktur (Connection, Timeout, Import)")
    print(f"  PRODUCT  ({len(product)}) — Produkt (Assertion, falsches Verhalten)")
    print(f"  TEST     ({len(test)}) — Testcode (Selektor, Setup)\n")

    for f in failures:
        emoji = {"INFRA": "🔧", "PRODUCT": "🐛", "TEST": "🧪"}[f["category"]]
        print(f"  {emoji} [{f['category']}] {f['classname']}::{f['name']}")
        print(f"     {f['message']}\n")

    if infra:
        print(
            "🔧 INFRA-Fehler: Dienste prüfen (Ollama, SearXNG, Tor, Chromium, docker)"
        )
    if product:
        print("🐛 PRODUCT-Fehler: Verhalten prüfen — Produktänderung oder Regression?")
    if test:
        print("🧪 TEST-Fehler: Testcode prüfen — Selektor fragil? Setup falsch?")

    return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 classify-errors.py <junit.xml>", file=sys.stderr)
        sys.exit(2)

    junit_path = sys.argv[1]
    if not Path(junit_path).exists():
        print(f"classify-errors: Datei nicht gefunden: {junit_path}", file=sys.stderr)
        sys.exit(0)

    failures = parse_junit(junit_path)
    return print_report(failures)


if __name__ == "__main__":
    sys.exit(main())
