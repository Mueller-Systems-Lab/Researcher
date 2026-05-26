# =============================================================================
# Claim Retriever — Quellen für Claim-Validierung finden und fetchen
# =============================================================================
# Getrennt vom Scoring und Index-Schreiben. Nur für Retrieval zuständig.
# Nutzt CompositeRetriever (Web) und SearchIndexRepository (Volltext).
# =============================================================================

import logging

logger = logging.getLogger(__name__)


def _sanitize_url(url: str) -> str:
    """Ersetzt rohe Onion-URLs durch gehashte Referenz.

    ADR-006/007: Onion-URLs dürfen NICHT roh in API-Responses oder Logs erscheinen.
    """
    if not url:
        return ""
    if ".onion" in url:
        import hashlib

        # raw URL never leaves this module
        return f"onion://{hashlib.sha256(url.encode()).hexdigest()[:16]}"
    return url


def retrieve_composite(claim: str, max_sources: int = 5) -> dict:
    """Sucht über CompositeRetriever (SearXNG Web-Suche).

    Args:
        claim: Der zu validierende Claim.
        max_sources: Maximale Anzahl Quellen.

    Returns:
        Dict mit:
          - "results": Liste von Ergebnis-Dicts
          - "errors": dict mit Fehlerdetails pro Backend (None wenn OK)
          - "total": Anzahl Ergebnisse
    """
    result: dict = {"results": [], "errors": {}, "total": 0}
    try:
        from search.composite import CompositeRetriever

        retriever = CompositeRetriever(claim, searx_url="http://localhost:8080")
        retriever.darknet_enabled = False  # Nur Web für Validierung
        search_results = retriever.search(max_results=max_sources)
        for r in search_results:
            result["results"].append(
                {
                    "url": _sanitize_url(r.get("url", "")),
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")[:300],
                    "source": r.get("source", "web"),
                    "score": r.get("score", 0),
                    "match_type": "keyword",
                }
            )
        result["errors"] = retriever.last_errors
        result["total"] = len(result["results"])
    except ImportError as e:
        result["errors"]["import"] = f"CompositeRetriever nicht importierbar: {e}"
        logger.error(result["errors"]["import"], exc_info=True)
    except Exception as e:
        result["errors"]["runtime"] = f"Retrieval-Fehler: {e}"
        logger.error(result["errors"]["runtime"], exc_info=True)
    return result


def retrieve_fulltext(claim: str, max_sources: int = 5) -> dict:
    """Sucht im Volltext-Index (Whoosh/SQLite FTS5).

    Args:
        claim: Der zu validierende Claim.
        max_sources: Maximale Anzahl Quellen.

    Returns:
        Dict mit:
          - "results": Liste von Ergebnis-Dicts
          - "errors": dict mit Fehlerdetails (None wenn OK)
          - "total": Anzahl Ergebnisse
    """
    result: dict = {"results": [], "errors": {}, "total": 0}
    try:
        from darknet_search.index import WhooshIndex

        idx = WhooshIndex()
        index_results = idx.search(claim, limit=max_sources)
        for r in index_results:
            result["results"].append(
                {
                    "url": _sanitize_url(r.get("url", "")),
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:300],
                    "source": r.get("source", "index"),
                    "score": r.get("score", 0),
                    "match_type": "fulltext",
                }
            )
        result["total"] = len(result["results"])
    except ImportError as e:
        result["errors"]["import"] = f"WhooshIndex nicht importierbar: {e}"
        logger.error(result["errors"]["import"], exc_info=True)
    except Exception as e:
        result["errors"]["runtime"] = f"Index-Suche fehlgeschlagen: {e}"
        logger.error(result["errors"]["runtime"], exc_info=True)
    return result
