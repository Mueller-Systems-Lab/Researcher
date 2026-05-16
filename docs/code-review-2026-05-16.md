# Code Review — 2026-05-16

## Summary
- **Overall assessment: CONDITIONAL PASS** (2 HIGH findings need fixing)
- Files reviewed: 40
- Lines of code reviewed: ca. 3.400

## Findings

### HIGH: Unauthenticated Web-Fetch ermöglicht SSRF
- **File:** `mcp_tools/web_fetch.py:87-105`
- **Issue:** Das Tool akzeptiert jede nicht-`.onion` URL und fetcht sie direkt mit `requests`. Es gibt keine Sperre für `localhost`, RFC1918, Link-Local oder andere interne Ziele.
- **Impact:** high
- **Recommendation:** Nur allowlisted Hosts zulassen oder mindestens private/loopback/link-local Ziele blockieren; Fetches über eine nicht-bypassbare Policy-Schicht erzwingen.

### HIGH: Human-Review-Tool kann Gates selbst umgehen
- **File:** `mcp_tools/human_review.py:96-208`
- **Issue:** Ein einziges MCP-Tool bietet `request`, `approve` und `reject` ohne Rollen- oder Autorisierungsgrenze. Ein automatischer Caller kann damit eigene Review-Items erstellen und direkt freigeben.
- **Impact:** high
- **Recommendation:** Request und Approval trennen; Approve/Reject nur über einen Human-only Pfad oder mit zusätzlicher Authentisierung erlauben.

### HIGH: Dashboard-Static-Serving ist traversal-anfällig
- **File:** `dashboard/server.py:43-77`
- **Issue:** Request-Pfade werden ohne Normalisierung oder Root-Check an `STATIC_DIR` angehängt. Dadurch kann `../` aus dem Static-Verzeichnis ausbrechen und lokale Dateien lesen.
- **Impact:** high
- **Recommendation:** Pfade normalisieren, Traversal strikt ablehnen und nur über eine allowlist von Dateien ausliefern.

### MEDIUM: CLI-Entrypoint crasht im `--config-only`-Pfad
- **File:** `onion_discovery/__main__.py:66-76`
- **Issue:** Der Code nutzt `os.getenv`, importiert aber `os` nicht. Der `--config-only`-Pfad wirft dadurch `NameError`.
- **Impact:** medium
- **Recommendation:** `os` importieren und den CLI-Pfad mit einem kleinen Smoke-Test absichern.

### MEDIUM: DarknetCrawler mutiert eine globale Config-Instanz
- **File:** `crawlers/darknet_crawler.py:52-58`
- **Issue:** `config_override` schreibt direkt in das importierte globale `config`-Objekt. Dadurch können Instanz-Overrides in spätere Läufe oder Tests "durchsickern".
- **Impact:** medium
- **Recommendation:** Pro Instanz eine Kopie der Konfiguration verwenden statt das Singleton zu mutieren.

### MEDIUM: "Playwright"-Test ist kein Browser-Test
- **File:** `tests/playwright/test_dashboard_visual.py:16-71`
- **Issue:** Der Test startet keinen Browser und nutzt kein Playwright. Es wird nur HTML als Text geprüft; echte Render-/Screenshot-Regression bleiben ungetestet.
- **Impact:** medium
- **Recommendation:** Echte Browser-Tests mit Screenshot-Vergleich ergänzen; den HTML-Smoke-Test separat behalten.

### MEDIUM: `VectorStore.query` ignoriert mehrere Query-Embeddings
- **File:** `vectordb/store.py:135-177`
- **Issue:** Die Signatur akzeptiert `list[list[float]]`, aber die Implementierung wertet nur `results["documents"][0]` aus. Mehrere Query-Embeddings liefern damit unvollständige Ergebnisse.
- **Impact:** medium
- **Recommendation:** Entweder die API auf ein einzelnes Embedding einschränken oder alle Ergebnis-Sets verarbeiten.

### LOW: Blocklist sollte Allowlist überstimmen
- **File:** `onion_discovery/policy_gateway.py:72-90`
- **Issue:** Wenn ein Host gleichzeitig in Allowlist und Blocklist steht, gewinnt aktuell die Allowlist, weil sie zuerst geprüft wird.
- **Impact:** low
- **Recommendation:** Deny-overrides-allow als Policy festschreiben oder mindestens explizit dokumentieren und testen.
