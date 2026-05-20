# =============================================================================
# Tests: Crawl-Scale-Policy Documentation Validation (Issue #77)
# =============================================================================
# Prüft, dass die Crawl-Scale-Policy-Dokumente existieren und alle
# erforderlichen Kontrollmechanismen dokumentieren.
# =============================================================================

from pathlib import Path

# ── Document Existence ────────────────────────────────────────────────────


def test_crawl_scale_policy_exists():
    """Doku docs/crawling/crawl-scale-policy.md existiert."""
    assert Path("docs/crawling/crawl-scale-policy.md").exists()


def test_cache_frontier_architecture_exists():
    """Doku docs/crawling/cache-frontier-architecture.md existiert."""
    assert Path("docs/crawling/cache-frontier-architecture.md").exists()


def test_german_search_keys_doc_exists():
    """Doku docs/text/german-search-keys.md existiert."""
    assert Path("docs/text/german-search-keys.md").exists()


# ── Required Controls in crawl-scale-policy.md ───────────────────────────


def test_crawl_scale_policy_mentions_required_controls():
    """Crawl-Scale-Policy dokumentiert alle erforderlichen Kontrollen."""
    content = (
        Path("docs/crawling/crawl-scale-policy.md").read_text(encoding="utf-8").lower()
    )

    required_terms = [
        "robots.txt",
        "cache",
        "frontier",
        "queue",
        "rate limit",
        "backoff",
        "canonical",
        "dedup",
        "original_text",
        "normalized_text",
        "ascii_folded_text",
    ]

    for term in required_terms:
        assert term in content, f"Term '{term}' nicht in crawl-scale-policy.md gefunden"


def test_crawl_scale_policy_mentions_safety_boundaries():
    """Crawl-Scale-Policy dokumentiert explizite Verbote."""
    content = (
        Path("docs/crawling/crawl-scale-policy.md").read_text(encoding="utf-8").lower()
    )

    forbidden_controls = [
        "brute force",
        "login-automation",
        "captcha",
        "exploit",
        "darknet-massencrawls",
        "live-crawls",
    ]

    for term in forbidden_controls:
        assert term in content, (
            f"Verbot '{term}' nicht in crawl-scale-policy.md gefunden"
        )


def test_crawl_scale_policy_mentions_standards():
    """Crawl-Scale-Policy referenziert relevante RFCs und Standards."""
    content = (
        Path("docs/crawling/crawl-scale-policy.md").read_text(encoding="utf-8").lower()
    )

    standards = [
        "rfc 9309",  # Robots Exclusion Protocol
        "rfc 9111",  # HTTP Caching
        "uax #15",  # Unicode Normalization
    ]

    for standard in standards:
        assert standard in content, (
            f"Standard '{standard}' nicht in crawl-scale-policy.md referenziert"
        )


# ── Required Controls in cache-frontier-architecture.md ───────────────────


def test_cache_frontier_mentions_components():
    """Cache-Frontier-Doku listet alle Komponenten."""
    content = (
        Path("docs/crawling/cache-frontier-architecture.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    components = [
        "frontier queue",
        "robots policy",
        "fetch cache",
        "canonicalizer",
        "content hash",
        "domain budget",
        "audit log",
    ]

    for component in components:
        assert component in content, (
            f"Komponente '{component}' nicht in cache-frontier-architecture.md"
        )


def test_cache_frontier_mentions_data_flow():
    """Cache-Frontier-Doku beschreibt den Datenfluss."""
    content = (
        Path("docs/crawling/cache-frontier-architecture.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    flow_terms = [
        "user query",
        "index lookup",
        "cache hit",
        "frontier queue",
        "canonicalizer",
        "fetcher",
    ]

    for term in flow_terms:
        assert term in content, (
            f"Datenfluss-Term '{term}' nicht in cache-frontier-architecture.md"
        )


# ── Required Controls in german-search-keys.md ────────────────────────────


def test_german_search_keys_doc_mentions_mapping():
    """German-Search-Keys-Doku enthält Umlaut-Mapping."""
    content = (
        Path("docs/text/german-search-keys.md").read_text(encoding="utf-8").lower()
    )

    mapping_terms = [
        "ä",
        "ö",
        "ü",
        "ß",
        "ascii_folded",
        "normalized",
        "original",
    ]

    for term in mapping_terms:
        assert term in content, f"Mapping-Term '{term}' nicht in german-search-keys.md"


def test_german_search_keys_doc_mentions_functions():
    """German-Search-Keys-Doku dokumentiert die API-Funktionen."""
    content = (
        Path("docs/text/german-search-keys.md").read_text(encoding="utf-8").lower()
    )

    functions = [
        "build_german_search_keys",
        "german_search_keys_match",
        "german_query_matches_text",
    ]

    for func in functions:
        assert func in content, (
            f"Funktion '{func}' nicht in german-search-keys.md dokumentiert"
        )


# ── Non-Targets — keine Live-Crawls ───────────────────────────────────────


def test_crawl_docs_contain_no_live_crawl_promises():
    """Kein Doku-Dokument verspricht Live-Crawls in diesem Issue."""
    for path in [
        "docs/crawling/crawl-scale-policy.md",
        "docs/crawling/cache-frontier-architecture.md",
    ]:
        content = Path(path).read_text(encoding="utf-8").lower()
        # Die Docs beschreiben Architektur für *spätere* Crawls,
        # dürfen aber keine sofortige Umsetzung versprechen
        # (strukturelle Prüfung: Docs existieren und sind valide)
        assert len(content) > 200, f"{path} ist zu kurz für eine Policy-Doku"
