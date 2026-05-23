# ADR-012: Dashboard Live-Updates via SSE + WCAG 2.1 AA Accessibility

**Status:** Accepted  
**Date:** 2026-05-18  
**Deciders:** Architecture Review Agent, Issue Orchestrator  
**Context:** Architecture Review nach ADR-010, Block 6.2; Issue #41 (a11y)

---

## Context

Das GPU-Dashboard (`dashboard/server.py`) stellt Live-Telemetrie der NVIDIA GTX 1070 (GPU-Auslastung, VRAM, Temperatur, Prozesse) über einen eingebetteten HTTP-Server bereit. Die Telemetrie wird per `nvidia-smi` Subprocess erhoben und als JSON/SSE gestreamt.

Zwei architektonische Entscheidungen stehen zur Dokumentation:

1. **SSE (Server-Sent Events) vs WebSocket** für den Live-Stream
2. **WCAG 2.1 AA Accessibility** als Quality Gate für die Dashboard-UI

Issue #41 hat Playwright-basierte Accessibility-Tests (ARIA-Labels, Kontrast, Keyboard-Navigation) hinzugefügt.

## Decision

### SSE statt WebSocket

**SSE bleibt der MVP-Mechanismus für einseitige GPU-Telemetrie.**

- SSE ist simpler: kein Upgrade-Handshake, kein Ping/Pong, kein Connection-Management.
- Für GPU-Telemetrie ist nur Server→Client-Kommunikation nötig (kein Client→Server).
- SSE ist nativ in Browsern (`EventSource` API) ohne zusätzliche Bibliothek.
- Der Dashboard-Server (`http.server.HTTPServer`) unterstützt SSE ohne zusätzliche Dependencies.

**WebSocket wird abgelehnt**, weil:
- Keine bidirektionale Kommunikation nötig (Dashboard liest nur).
- Erhöhte Komplexität (Handshake, Heartbeat, Reconnect-Logik).
- Zusätzliche Abhängigkeit (websockets-Bibliothek) oder Framework-Wechsel nötig.

### WCAG 2.1 AA als Quality Gate

**Das Dashboard muss WCAG 2.1 AA erfüllen**, verifiziert durch Playwright-Tests:

- `aria-label` an allen interaktiven Elementen und Regionen
- `role`-Attribute (`status`, `progressbar`, `region`, `alert`)
- `aria-live` für dynamische Inhalte (GPU-Daten, Fehlermeldungen)
- `aria-atomic` für vollständige Updates
- Farbkontrast ≥ 4.5:1 für Text, ≥ 3:1 für große Texte
- Keyboard-Navigation (Tab-Reihenfolge, Fokus-Indikatoren)
- Playwright a11y-Tests als REQUIRED Gate (kein Skip erlaubt)

## Alternatives Considered

### Alternative A: Polling statt SSE

- **Pros:** Einfacher (GET /api/gpu alle N Sekunden), keine dauerhafte Verbindung.
- **Cons:** Höhere Latenz, mehr Requests, ineffizient bei niedrigen Update-Raten.
- **Decision:** Abgelehnt. SSE ist effizienter für Echtzeit-Dashboard.

### Alternative B: WebSocket

- **Pros:** Bidirektional, niedrige Latenz, etablierter Standard.
- **Cons:** Overkill für einseitige Telemetrie, komplexeres Connection-Management, zusätzliche Dependency.
- **Decision:** Abgelehnt für MVP.

### Alternative C: Keine Accessibility-Anforderungen

- **Pros:** Weniger Entwicklungsaufwand.
- **Cons:** Schließt Nutzer mit Einschränkungen aus, verstößt gegen Best Practices.
- **Decision:** Abgelehnt. WCAG 2.1 AA ist minimaler Standard.

## Consequences

### Positive

- SSE ist leichtgewichtig und ressourcenschonend.
- `EventSource` API ist nativ in allen modernen Browsern.
- WCAG 2.1 AA stellt sicher, dass das Dashboard für alle Nutzer zugänglich ist.
- Playwright-Tests automatisieren die Accessibility-Prüfung.

### Negative

- SSE unterstützt nur Text-basierte Events (kein Binary).
- Keine bidirektionale Kommunikation (Dashboard kann keine Befehle senden).
- Accessibility-Tests erhöhen die CI-Laufzeit.

### Risiken

- Lange SSE-Connections können HTTP/1.1-Connection-Limits erreichen (bei single-user MVP irrelevant).
- Änderungen an der Dashboard-UI müssen Accessibility-Tests bestehen.

## References

- Issue #41: WCAG 2.1 AA Accessibility Tests
- `dashboard/server.py` — SSE-Implementierung (Zeilen 122-141)
- `dashboard/static/index.html` — Dashboard-UI mit ARIA-Attributen
- `tests/playwright/test_dashboard_accessibility.py` — Playwright a11y Tests
- ADR-010: Final Architecture Review (Missing ADR-012 identifiziert)
- WCAG 2.1 AA: https://www.w3.org/TR/WCAG21/
- Playwright Accessibility: https://playwright.dev/docs/accessibility-testing
