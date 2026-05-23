# ADR-011: MCP Tool Registry und Sicherheitsmodell

**Status:** Accepted  
**Date:** 2026-05-18  
**Deciders:** Architecture Review Agent, Issue Orchestrator  
**Context:** Architecture Review nach ADR-010, Block 6.1

---

## Context

Das Researcher-Projekt exponiert fünf MCP-Tools über eine zentrale Registry (`mcp_tools/registry.py`), die sowohl für lokale Research-Pipelines als auch potenziell für externe MCP-Clients (Claude Desktop, OpenCode, etc.) verfügbar sind:

- `web-fetch` — HTTP-Fetch mit SSRF-Schutz, keine Onion-URLs
- `evidence-store` — Embedding-basierte Evidenzspeicherung in ChromaDB
- `claim-validator` — Claim-Validierung gegen CompositeRetriever + Volltextindex
- `audit-log` — Audit-Trail für alle Tool-Aufrufe
- `human-review-request` — Human-Approval-Requests für Onion-Inhalte

Jedes Tool erbt von `MCPToolBase` (ABC) und implementiert `run(params)`, `name`, `description`, `parameters`. Die Registry erlaubt deny-by-default: unbekannte Tool-Namen werden abgelehnt.

Das Sicherheitsmodell dieser Tool-Schicht benötigt eine formale ADR, weil sie die primäre Schnittstelle zwischen Research-Funktionalität und externer/exponierter API ist.

## Decision

**Die MCP Tool Registry wird als zentraler, deny-by-default Sicherheitsgatekeeper betrieben:**

1. **Deny-by-default:** Unbekannte Tool-Namen werden abgelehnt.
2. **Keine generischen Tools:** Kein `crawl_anything`, kein Live-Tor-Fetch, kein `run_command`.
3. **Getrennte Trust-Level:**
   - **Read-only:** `web-fetch` (SSRF-geschützt), `claim-validator`, `evidence-store:search`
   - **Write:** `evidence-store:store`, `audit-log`
   - **Human-only:** `human-review-request` (MCP kann nur Request, nicht approve/reject)
4. **Keine Live-Onion-Abfragen:** Alle Onion-Tools sind disabled-by-default; `web-fetch` blockiert `.onion` URLs.
5. **Audit-Trail:** Jeder Tool-Aufruf wird in `audit-log` protokolliert.
6. **Keine Modifikation über MCP:** `human-review-request` erlaubt nur `request`, `list_pending`, `stats` — `approve`/`reject` sind MCP-seitig blockiert, nur CLI/Dashboard.

## Alternatives Considered

### Alternative A: Direkte Imports ohne Registry

- **Pros:** Weniger Code, keine zentrale Konfiguration.
- **Cons:** Keine Zugriffskontrolle, keine Auditierung, kein deny-by-default, schwieriger zu testen.
- **Decision:** Abgelehnt. Erhöht Sicherheitsrisiko und Kopplung.

### Alternative B: Dynamische Plugin-Discovery

- **Pros:** Einfaches Hinzufügen neuer Tools ohne Code-Änderung.
- **Cons:** Erhöht Angriffsfläche (jede Datei im Tool-Verzeichnis wird geladen), keine statische Sicherheitsanalyse möglich, höhere Komplexität.
- **Decision:** Abgelehnt für MVP. Statische Registry ist sicherer und ausreichend.

### Alternative C: MCP-Tools komplett deaktivieren im Produktivbetrieb

- **Pros:** Maximale Sicherheit.
- **Cons:** Verfehlt den Projektzweck (Research-System muss Tools exponieren), verhindert MCP-Client-Integration.
- **Decision:** Abgelehnt. Registry mit deny-by-default ist der bessere Mittelweg.

## Consequences

### Positive

- Klare Sicherheitsgrenzen für jedes Tool und jede Operation.
- Audit-Trail für alle Tool-Aufrufe ermöglicht Nachvollziehbarkeit.
- Deny-by-default verhindert unbefugte Tool-Nutzung.
- Getrennte Trust-Level erleichtern Sicherheitsaudits.
- Keine Live-Onion- oder generischen Crawl-Tools aus dem MCP-Layer.

### Negative

- Neue Tools müssen explizit registriert und geprüft werden.
- Trust-Level-Klassifikation muss bei neuen Tools manuell aktualisiert werden.
- Keine dynamische Tool-Erweiterung ohne Registry-Änderung.

### Risiken

- Fehlklassifikation eines Tools (z.B. Write als Read-only) könnte Sicherheitslücken öffnen.
- MCP-Transport-Sicherheit (stdio/HTTP) muss separat gehärtet werden.

## References

- `mcp_tools/registry.py` — Zentrale Tool-Registry
- `mcp_tools/base.py` — MCPToolBase ABC und MCPToolResult
- `mcp_tools/web_fetch.py` — SSRF-geschützter Web-Fetch
- `mcp_tools/human_review.py` — Human-Review mit MCP-seitiger Blocklist
- `mcp_tools/claim_validator.py` — Claim-Validator Orchestrator
- ADR-006: Evidence-first Pipeline (Human Approval Gates)
- ADR-010: Final Architecture Review (Missing ADR-011 identifiziert)
- MCP-Spezifikation: https://modelcontextprotocol.io/specification/2025-06-18
