# =============================================================================
# Claim Index Writer — Ergebnisse in den Suchindex schreiben
# =============================================================================
# Getrennt vom Retrieval und Scoring. Nur für Index-Persistenz zuständig.
# Nutzt SearchIndexRepository (Port) statt direktem WhooshIndex.
# =============================================================================

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def write_results_to_index(
    results: list[dict],
    claim: str = "",
    index_backend=None,
) -> int:
    """Schreibt validierte Claim-Ergebnisse in den Index.

    Args:
        results: Liste von Ergebnis-Dicts.
        claim: Der ursprüngliche Claim (optional).
        index_backend: SearchIndexRepository-Instanz. Wenn None, wird
                       Default basierend auf SEARCH_INDEX_BACKEND erstellt.

    Returns:
        Anzahl erfolgreich indexierter Dokumente.
    """
    if index_backend is None:
        backend_name = os.getenv("SEARCH_INDEX_BACKEND", "whoosh").lower()
        index_path = os.getenv("DARKNET_INDEX_PATH", "./darknet_index")

        if backend_name == "sqlite_fts5":
            import os as _os

            from gpt_researcher.adapters.sqlite_fts5_adapter import SQLiteFTS5Adapter

            db_path = _os.path.join(index_path, "darknet_index.sqlite3")
            index_backend = SQLiteFTS5Adapter(db_path)
        else:
            from gpt_researcher.adapters.whoosh_index_adapter import WhooshIndexAdapter

            index_backend = WhooshIndexAdapter(index_path)

    count = 0
    for r in results:
        doc = {
            "url": r.get("url", ""),
            "author": "claim_validator",
            "title": r.get("title", ""),
            "timestamp": datetime.now(),
            "content": r.get("snippet", "")[:2000],
            "forum_id": "evidence",
        }
        if index_backend.index(doc):
            count += 1

    logger.info(f"Claim Index Writer: {count}/{len(results)} Ergebnisse indexiert")
    return count
