# =============================================================================
# Shared Blocked Terms — Zentrale Quelle der Wahrheit für Query-Safety-Guards
# =============================================================================
# Einzige Definition aller geblockten Query-Begriffe.
# Alle Skripte und Tests importieren von hier, statt die Menge
# lokal zu duplizieren.
#
# Nutzung:
#   from config.blocked_terms import BLOCKED_TERMS
#   if any(term in query.lower() for term in BLOCKED_TERMS):
#       raise ValueError("Query enthält blockierte Begriffe")
# =============================================================================

BLOCKED_TERMS: set[str] = {
    "exploit",
    "cve",
    "vulnerability",
    "target.com",
    "credential",
    "password dump",
    "darknet",
    "onion forum",
    "person:",
    "site:",
    "malware",
    "ransomware",
}
