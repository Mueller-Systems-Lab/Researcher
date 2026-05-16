# Researcher-Projekt: Research-First-Regel für GPT-Researcher, MCP, Retriever und Onion-Research

## Zweck

Diese Datei ist eine projektspezifische Regel für das Researcher-/GPT-Researcher-basierte System.

Sie ist nicht als allgemeine OpenCode-Regel gedacht, sondern speziell für ein Research-System, das folgende Bausteine kombinieren soll:

- GPT-Researcher
- GPT-Researcher Custom Retriever
- GPT-Researcher MCP-Integration
- lokale Search APIs
- Onion Discovery / Onion Index
- Search Broker MCP
- lokale LLMs
- Research-Bundles
- Security-/OSINT-bezogene Recherche

Kernregel:

> Kein Retriever, MCP-Tool, Crawler, Search-Provider oder Research-Workflow wird skizziert oder implementiert, bevor aktuelle offizielle Dokumentation geprüft und die Erkenntnisse dokumentiert wurden.

---

## Validierungsbasis

Diese Regel wurde an folgenden aktuellen Dokumentationen ausgerichtet:

- GPT-Researcher Search Engines: GPT-Researcher unterstützt mehrere Retriever über `RETRIEVER`, darunter `tavily`, `bing`, `google`, `searchapi`, `serpapi`, `serper`, `searx`, `duckduckgo`, `arxiv`, `exa`, `pubmed_central` und `custom`.
- GPT-Researcher Custom Retriever: `RETRIEVER=custom`, `RETRIEVER_ENDPOINT` und zusätzliche `RETRIEVER_ARG_*`-Variablen; erwartete Antwort ist eine Liste mit `{ "url": "...", "raw_content": "..." }`.
- GPT-Researcher MCP Server: stellt MCP Resources, Tools und Prompts bereit, darunter `deep_research`, `quick_search`, `write_report`, `get_research_sources`, `get_research_context` und `research_query`.
- GPT-Researcher GitHub README: MCP kann mit Websuche kombiniert werden, z. B. `RETRIEVER=tavily,mcp`.
- MCP-Spezifikation: Server können Resources, Prompts und Tools bereitstellen; Tools sind ausführbare Funktionen und müssen sicher begrenzt werden.
- Tor Onion Services: Onion Discovery ist nicht DNS-basiert; Onion Crawling muss seed-basiert, begrenzt und policy-gesteuert sein.

Quellen:

- https://docs.gptr.dev/docs/gpt-researcher/search-engines
- https://docs.gptr.dev/docs/gpt-researcher/mcp-server/getting-started
- https://github.com/assafelovic/gpt-researcher
- https://modelcontextprotocol.io/specification/2025-06-18
- https://spec.torproject.org/rend-spec-v3
- https://community.torproject.org/onion-services/

---

# Research-First-Regel für das Researcher-Projekt

## Kurzfassung

```markdown
## Research-First for Researcher

Bei jeder Änderung an GPT-Researcher, Retrievern, MCP, Search APIs, Onion Discovery, lokalen LLMs, Crawling oder Research-Bundles musst du zuerst aktuelle Dokumentation lesen.

Pflicht:
- offizielle GPT-Researcher-Doku prüfen
- offizielle MCP-Doku prüfen, falls MCP betroffen ist
- offizielle Provider-Doku prüfen, falls Search APIs betroffen sind
- Tor-/Onion-Doku prüfen, falls .onion betroffen ist
- Security-/Compliance-Risiken prüfen
- Erkenntnisse als GitHub-Kommentar dokumentieren
- erst danach Architektur, Issue oder Code formulieren
```

---

## Geltungsbereich

Die Regel gilt für:

- GPT-Researcher-Konfiguration
- `RETRIEVER`-Änderungen
- `RETRIEVER=custom`
- `RETRIEVER_ENDPOINT`
- `RETRIEVER_ARG_*`
- Search Provider Adapter
- Tavily/Bing/Google/SearchApi/SerpApi/Serper/Searx/DuckDuckGo/Arxiv/Exa/PubMed
- MCP-Server
- MCP-Tools
- MCP-Resources
- MCP-Prompts
- Onion Discovery
- Onion Search Index
- Tor Fetcher
- robots.txt / Rate Limits / Opt-out
- Research Bundle Builder
- Report-Generatoren
- lokale LLM-Auswertung
- OSINT-Workflows
- Security-relevante Recherche

---

## Verbindlicher Ablauf

### 1. Quellen lesen

Vor jeder Skizze oder Implementierung müssen je nach Thema Quellen geprüft werden:

#### GPT-Researcher

- Search Engines / Retriever
- Custom Retriever
- MCP Integration
- Testing your Retriever, falls verfügbar
- README-Beispiele im offiziellen Repository

#### MCP

- MCP-Spezifikation
- Tools
- Resources
- Prompts
- Security / Trust & Safety
- verwendetes SDK, falls implementiert wird

#### Onion / Tor

- Onion Service Grundlagen
- v3-Spezifikation
- Grenzen von Discovery
- Risiken von Crawling
- Rate Limits und Netzschonung

#### Search Provider

- Authentifizierung
- Rate Limits
- Pricing / Free Tier
- Response-Format
- Nutzungsbedingungen
- SDK-Version

---

### 2. Erkenntnisse dokumentieren

Vor der Umsetzung muss ein Kommentar angelegt werden:

```markdown
## Researcher: Research-First Kommentar

### Aufgabe

- Issue: #...
- Thema: GPT-Researcher / MCP / Retriever / Onion / Search API / ...

### Gelesene offizielle Quellen

- Quelle 1:
  - Erkenntnis:
- Quelle 2:
  - Erkenntnis:
- Quelle 3:
  - Erkenntnis:

### Validierte Fakten

- Fakt 1:
- Fakt 2:
- Fakt 3:

### Architekturentscheidung

- Entscheidung:
- Begründung:

### Annahmen / Unsicherheiten

- ...

### Sicherheitsgrenzen

- Kein Onion-Bruteforce: ja/nein/nicht relevant
- Keine Live-Tor-Abfrage in Retriever: ja/nein/nicht relevant
- Kein Login/Formular/Captcha: ja/nein/nicht relevant
- Keine Secrets in Logs: ja/nein/nicht relevant
- Raw Content begrenzt: ja/nein/nicht relevant
```

---

### 3. Erst danach entwerfen

Jede Skizze oder jedes Issue muss aus den geprüften Quellen abgeleitet sein.

Verboten:

- `RETRIEVER`-Namen erfinden
- Custom-Retriever-Response-Format erfinden
- MCP-Primitive falsch benennen
- MCP als Ersatz für Custom Retriever darstellen, wenn GPT-Researcher eine Retriever-API erwartet
- Onion-Discovery als DNS-Enumeration darstellen
- Live-Crawling in Suchanfragen auslösen
- Credentials, Leaks oder sensible Inhalte ungekürzt ausgeben
- Provider-APIs ohne aktuelle Doku skizzieren

---

# Projektentscheidung: Trennung der Schichten

Für dieses Researcher-Projekt gilt folgende Architekturtrennung:

```text
Onion Discovery Engine
  → sammelt, crawlt und indexiert bekannte .onion-Quellen

GPT-Researcher Custom Retriever API
  → liefert GPT-Researcher-kompatible Ergebnisse im Format [{url, raw_content}]

Search Broker MCP
  → steuert Provider, Status, Research-Bundles und Strategie über Tools/Resources/Prompts
```

## Regel

MCP ist nicht automatisch der primäre GPT-Researcher-Retriever.

- Für direkte Ergebnisübergabe an GPT-Researcher: `RETRIEVER=custom` + `RETRIEVER_ENDPOINT`.
- Für Agentensteuerung, Provider-Status, Research-Bundles und Strategie: MCP.
- Für hybride Recherche: offizielle `RETRIEVER=tavily,mcp`-ähnliche Konfiguration prüfen.

---

## Custom Retriever Pflichtformat

Wenn ein eigener Retriever gebaut wird, muss der Endpoint dieses Format liefern:

```json
[
  {
    "url": "http://example.com/page1",
    "raw_content": "Content of page 1"
  }
]
```

Projektregel:

- `raw_content` muss bereinigt und begrenzt sein.
- Onion-Ergebnisse dürfen nur aus bereits indexierten Quellen kommen.
- Keine Live-Tor-Abfrage innerhalb einer GPT-Researcher-Retriever-Anfrage.
- Blocklist und Opt-out müssen vor Ausgabe geprüft werden.
- Secrets dürfen nicht geloggt werden.

---

## MCP-Projektregel

Wenn ein MCP-Server gebaut wird, muss er klar zwischen MCP-Primitives trennen:

```text
Resources = Kontext und Daten
Prompts   = wiederverwendbare Workflows
Tools     = ausführbare Funktionen
```

Für dieses Projekt sind gefährliche Tools verboten:

```text
browse_any_url
crawl_anything
bruteforce_onion_addresses
submit_login_form
bypass_captcha
scan_ports
exploit_target
collect_credentials
mirror_marketplace
```

Erlaubte Tools müssen begrenzt sein:

```text
list_search_providers
provider_health_check
search_existing_index
search_provider
create_research_bundle
create_gptr_context
suggest_retriever_strategy
get_onion_index_stats
```

---

# Acceptance Criteria für Researcher-Regel

- [ ] Regel ist in `AGENTS.md` oder projektspezifischer Agentendokumentation aufgenommen.
- [ ] Regel ist in den Issue-Templates aufgenommen.
- [ ] Regel ist in der PR-Checkliste aufgenommen.
- [ ] GPT-Researcher-spezifische Quellenpflicht ist dokumentiert.
- [ ] MCP-spezifische Quellenpflicht ist dokumentiert.
- [ ] Onion-/Tor-spezifische Quellenpflicht ist dokumentiert.
- [ ] Custom-Retriever-Format `{url, raw_content}` ist dokumentiert.
- [ ] Trennung zwischen Discovery, Retriever API und MCP ist dokumentiert.
- [ ] Sicherheitsgrenzen für Crawling, Search APIs und MCP Tools sind dokumentiert.
- [ ] Jeder Implementierungsagent muss Recherche-Erkenntnisse als Issue-Kommentar dokumentieren.

---

# Tests / Checks

## Dokumentations-Checks

- [ ] `AGENTS.md` enthält Researcher-Regel.
- [ ] Issue-Template enthält Pflichtfeld „Gelesene Quellen“.
- [ ] PR-Template enthält Checkbox „GPT-Researcher/MCP/Provider-Doku geprüft“.
- [ ] Custom-Retriever-Format ist dokumentiert.
- [ ] MCP-Primitives sind korrekt getrennt.

## Kompatibilitäts-Checks

- [ ] `RETRIEVER=custom` Beispiel vorhanden.
- [ ] `RETRIEVER_ENDPOINT` Beispiel vorhanden.
- [ ] `RETRIEVER_ARG_*` Beispiel vorhanden.
- [ ] `RETRIEVER=tavily,mcp` oder äquivalente Hybrid-Beispielkonfiguration geprüft und dokumentiert.
- [ ] MCP Tools/Resources/Prompts sind korrekt benannt.

## Negative Checks

- [ ] Output ohne Quellenprüfung wird abgelehnt.
- [ ] Output mit erfundenen Retriever-Namen wird abgelehnt.
- [ ] Output mit falschem Custom-Retriever-Format wird abgelehnt.
- [ ] Output mit gefährlichen MCP-Tools wird abgelehnt.
- [ ] Output mit Live-Tor-Abfrage in Retriever-Suche wird abgelehnt.

---

# Definition of Done

- [ ] Researcher-Regel in Agentendokumentation integriert.
- [ ] Issue-/PR-Templates erweitert.
- [ ] Beispiele für GPT-Researcher-Konfiguration ergänzt.
- [ ] Beispiele für MCP-Grenzen ergänzt.
- [ ] Sicherheitsregeln dokumentiert.
- [ ] Research-Kommentar-Template ergänzt.
- [ ] Tests/Checks dokumentiert.
- [ ] Abschlusskommentar im GitHub-Issue hinterlassen.

---

## Agenten-Hinweis

Vor Umsetzung dieser Regel im Researcher-Projekt muss der Agent aktuelle offizielle Dokumentation prüfen und die Erkenntnisse als GitHub-Kommentar dokumentieren:

- GPT-Researcher Retriever
- GPT-Researcher Custom Retriever
- GPT-Researcher MCP
- MCP-Spezifikation
- Onion/Tor-Dokumentation, falls `.onion` betroffen ist
- Provider-Dokumentation, falls konkrete Search APIs betroffen sind

Danach erst Dateien ändern.
