# ADR-007: Onion Discovery Engine

**Status:** Proposed

**Date:** 2026-05-16

**Deciders:** Architecture Review Agent

## Context

Onion Services sind nicht über DNS oder Standard-Suchmaschinen auffindbar. Eine allgemeine `.onion`-Suche kann daher nicht wie Clearnet-Suche über Domain-Auflösung, Suchmaschinen-APIs oder offene Web-Crawler modelliert werden. Sie benötigt bekannte Seeds, policy-gesteuerte Traversal-Regeln, Tor-isolierten Zugriff, Link-Extraktion, Normalisierung, Klassifikation und einen lokalen Suchindex.

Die bestehende Architektur definiert bereits relevante Leitplanken:

- **ADR-006 Evidence-first Research Pipeline** trennt strikt drei Netzwerkzonen: Clearnet, Onion und Offline. Die Onion-Zone ist **disabled by default**, darf nur über Tor-Egress arbeiten, darf keine `.onion`-Domains durch Clearnet-Worker auflösen und verlangt **Human Approval vor dauerhafter Speicherung**.
- `design.md` definiert mit **ADR-002** das `CompositeRetriever`-Pattern und mit **ADR-004** Whoosh als Pure-Python-Volltextindex für Darknet-Inhalte.
- T-005/T-006 beschreiben bereits einen Darknet-Crawler mit Tor, Login, Parser, Rate-Limits und Whoosh-Index. Dieser ist jedoch auf ein einzelnes Forum und einen login-basierten Crawl-Workflow zugeschnitten.
- Issue #12 fordert eine allgemeinere Onion Discovery Engine: seed-basiert, multi-site, policy-gesteuert, mit Parser, Link-Extractor, Klassifikation und Suchindex.
- `researcher_research_first_rule.md` verlangt: keine Onion-Bruteforce-Discovery, keine Live-Tor-Abfragen in GPT-Researcher-Retriever-Anfragen, Blocklist/Opt-out vor Ausgabe, begrenzter `raw_content` und klare Trennung zwischen Onion Discovery Engine, GPT-Researcher Custom Retriever API und Search Broker MCP.
- Das Deployment-Ziel bleibt eine lokale Workstation mit GTX 1070 und 8 GB VRAM. Zusätzliche Serverprozesse müssen daher begründet werden und dürfen LLM/Embedding-Betrieb nicht destabilisieren.

Die zentrale Architekturfrage lautet: Soll die neue Onion Discovery Engine den bestehenden Darknet-Crawler ersetzen oder ergänzen, und welcher Index-/Integrationspfad passt zu ADR-006 und den Ressourcenlimits?

## Decision

Wir wählen **Option A: Onion Discovery Engine als Erweiterung und Generalisierung des bestehenden Whoosh-basierten Darknet-Crawler-/Retriever-Pfads**.

Die neue Engine **ersetzt den bestehenden Darknet-Crawler nicht sofort**, sondern ergänzt und refaktoriert ihn schrittweise:

1. Der bestehende T-005-Crawler wird als spezifische **Crawler Strategy** für login-basierte Foren behandelt.
2. Die neue Onion Discovery Engine wird als separater Onion-Zone-Worker eingeführt, der Seeds verarbeitet, Onion-Links extrahiert, klassifiziert und zur Human Review Queue weitergibt.
3. Nur freigegebene Quellen/Extrakte werden dauerhaft in den bestehenden Evidence-/Index-Pfad übernommen.
4. T-006/Whoosh bleibt für den MVP der lokale Volltextindex. Ein Wechsel zu Meilisearch, Typesense, Elasticsearch oder PostgreSQL FTS wird als späterer Skalierungspfad betrachtet, nicht als Issue-#12-MVP.

### Architekturtrennung

Die Engine wird logisch in drei Schichten getrennt:

```text
Onion Discovery Engine (Onion Zone, disabled by default)
  - Seed Queue
  - Tor Fetch Strategy
  - HTML/Text Parser
  - Onion Link Extractor
  - Policy Check: allowlist/blocklist/opt-out/rate-limit/content-type
  - Classifier: Quelle, Thema, Risiko, Indexierbarkeit
  - Human Review Queue

Onion Crawler / Extractor (Onion Zone)
  - crawlt nur freigegebene Seeds/Sites
  - extrahiert begrenzte Textartefakte
  - keine Binary-Verarbeitung
  - schreibt nur nach Approval in Evidence Store/Index

GPT-Researcher Retriever (Offline bzw. lokaler Indexzugriff)
  - sucht ausschließlich im bestehenden lokalen Index
  - löst keine Live-Tor-Abfragen aus
  - liefert GPT-Researcher-kompatible Ergebnisse
```

Damit bleibt **Discovery** das Finden und Bewerten neuer `.onion`-Adressen, während **Crawling** das Extrahieren von Inhalten aus bereits erlaubten/freigegebenen Quellen ist. GPT-Researcher erhält nur indexierte Ergebnisse, nie direkten Tor-Zugriff während einer Rechercheanfrage.

### Muster

- **Composite**: `CompositeRetriever` kombiniert weiterhin Clearnet- und lokale Onion-/Darknet-Index-Suche.
- **Strategy**: unterschiedliche Crawler/Fetche-Strategien für statische Onion-Seiten, Foren mit Login, API-ähnliche Seiten oder nur manuell importierte Seeds.
- **Pipeline**: Seed → Fetch → Parse → Link Extract → Classify → Policy Check → Human Review → Evidence/Index.
- **Repository**: Index-/Evidence-Zugriff wird über Repository-Schnittstellen gekapselt, damit Whoosh später ersetzt werden kann.
- **Observer/Scheduler**: periodische Discovery-Läufe außerhalb des GPT-Researcher-Request-Pfads.
- **Policy Gateway**: zentrale Prüfung von Blocklist, Opt-out, Rate-Limits, Content-Type und Speicherfreigabe.

### Netzwerkzonen gemäß ADR-006

- Onion Discovery und Onion Crawling laufen ausschließlich in der **Onion Zone** und sind standardmäßig deaktiviert.
- `.onion`-Fetches erfolgen nur über `socks5h://127.0.0.1:9050` bzw. einen explizit konfigurierten Tor-SOCKS-Endpunkt.
- Clearnet-Worker dürfen keine `.onion`-Adressen auflösen oder fetchen.
- GPT-Researcher/CompositeRetriever sucht nur im lokalen Index und triggert keine Live-Tor-Anfragen.
- Persistente Speicherung in Evidence Store/Whoosh erfolgt erst nach Human Approval.
- Binary-Downloads, Login-Formular-Automatisierung außerhalb explizit freigegebener Strategien, Captcha-Bypass, Port-Scanning und Onion-Bruteforce sind außerhalb des Scopes.

## Alternatives Considered

### Option A: Neue Engine als Erweiterung des bestehenden Whoosh-basierten Darknet-Crawlers

- **Aufwand:** Mittel. T-005/T-006 bleiben nutzbar, müssen aber in Discovery, Crawl Strategies, Policy Gateway und Index Repository aufgeteilt werden.
- **Skalierbarkeit:** Für MVP und kleine bis mittlere Onion-Korpora ausreichend. Whoosh ist dateibasiert und nicht für stark parallele Writes oder sehr große Korpora optimiert, aber passend für lokale, rate-limitierte Tor-Crawls.
- **Sicherheit:** Gut vereinbar mit ADR-006, weil bestehender lokaler Index genutzt wird und Live-Tor-Zugriff vom Retriever getrennt bleibt. Human Approval kann vor Indexierung erzwungen werden.
- **Wartbarkeit:** Hoch für das aktuelle Projekt, da Pure-Python, geringe Infrastruktur und Anschluss an bestehende ADRs/T-Tasks. Wichtig ist eine klare Modultrennung, damit der bisherige Single-Forum-Crawler nicht zur God Class wird.
- **Ressourcen/GTX 1070:** Günstig. Kein zusätzlicher Suchserver, kein nennenswerter VRAM-Verbrauch, CPU-/Disk-Last kontrollierbar.
- **Vergleich mit ADR-006:** Beste Übereinstimmung mit Netzwerkzonen, Offline-Synthese und Human Gates.
- **Why chosen:** Beste Balance aus geringer Kopplung, hoher Kohäsion, niedrigen Ressourcenanforderungen und Kompatibilität mit ADR-002/ADR-004/ADR-006.

### Option B: Separate Onion Discovery Engine mit Meilisearch/Typesense als Index

- **Aufwand:** Mittel bis hoch. Zusätzlicher Index-Server, neues Betriebsmodell, neue Schemas und Migration vom Whoosh-DarknetRetriever nötig.
- **Skalierbarkeit:** Besser als Whoosh für größere Korpora, schnelle Suche und API-basierte Abfragen. Für eine einzelne lokale Workstation aber zunächst überdimensioniert.
- **Sicherheit:** Trennung kann sauber umgesetzt werden, erhöht aber Angriffs- und Fehlkonfigurationsfläche durch einen weiteren lokalen Dienst. Zugriff muss strikt auf `127.0.0.1` begrenzt werden.
- **Wartbarkeit:** Gemischt. Bessere Suchfeatures, aber mehr Betriebsaufwand, Backups, Versionierung und Failure Modes.
- **Ressourcen/GTX 1070:** Kein VRAM-Problem, aber zusätzlicher RAM-/CPU-/Disk-Verbrauch neben Ollama, ChromaDB und SearXNG.
- **Vergleich mit ADR-006:** Vereinbar, wenn Human Approval vor Indexierung und Onion-Zonen-Isolation eingehalten werden. Für MVP jedoch mehr Infrastruktur als nötig.
- **Why rejected:** Nicht notwendig für den erwarteten MVP-Umfang; widerspricht dem bisherigen ADR-004-Minimalismus.

### Option C: Eigenständiger Microservice mit REST API und PostgreSQL + Volltextindex

- **Aufwand:** Hoch. Erfordert Service-Grenzen, API-Design, Datenmodell, Migration, Auth/Localhost-Sicherung, Backups und Betriebsdokumentation.
- **Skalierbarkeit:** Gut für spätere Mehrbenutzer-, Audit- und Query-Szenarien. PostgreSQL kann Metadaten, Crawl-Status, Review-Queue und Volltextsuche konsolidieren.
- **Sicherheit:** Potenziell sehr gut durch klare Prozess- und API-Grenzen, aber nur bei sauberer Authentisierung, lokaler Bindung und Policy-Durchsetzung. Falsch konfiguriert entsteht ein riskanter Onion-Search-Dienst.
- **Wartbarkeit:** Langfristig gut, kurzfristig deutlich komplexer. Höhere Kopplung an API-Versionen und Betriebszustand des Microservice.
- **Ressourcen/GTX 1070:** Kein VRAM-Verbrauch, aber zusätzlicher persistenter Datenbankdienst. Für eine Single-Workstation mit lokalem LLM unnötige Komplexität im MVP.
- **Vergleich mit ADR-006:** Gut als Zielbild für Evidence Store/Metadata/Audit, aber nicht als erster Schritt für Issue #12.
- **Why rejected:** Zu großer Scope-Sprung gegenüber T-005/T-006; besser als spätere ADR für produktive Skalierung.

### Status Quo: Nur bestehenden Darknet-Crawler nutzen

- **Aufwand:** Niedrig. Keine neue Architektur, keine neuen Module.
- **Skalierbarkeit:** Niedrig. Single-Forum- und login-zentrierter Ansatz erfüllt keine seed-basierte Multi-Site-Discovery.
- **Sicherheit:** Bestehende Tor- und Rate-Limit-Regeln bleiben, aber zentrale Policy-Gates, Blocklist/Opt-out und Human Review sind nicht ausreichend modelliert.
- **Wartbarkeit:** Anfangs einfach, langfristig schlecht, weil neue Discovery-Funktionen in den bestehenden Crawler hineingemischt würden.
- **Ressourcen/GTX 1070:** Günstig, aber funktional unzureichend.
- **Vergleich mit ADR-006:** Unvollständig, da Human Approval und Zonentrennung nicht als durchgängiger Discovery-Prozess abgebildet sind.
- **Why rejected:** Erfüllt Issue #12 nicht.

## Consequences

### Positive

- Die vorhandenen T-005/T-006-Artefakte bleiben nutzbar und werden nicht verworfen.
- Whoosh bleibt gemäß ADR-004 der MVP-Index; keine neue Server-Infrastruktur ist nötig.
- GPT-Researcher-Integration bleibt einfach: `CompositeRetriever` bzw. ein Custom Retriever liest aus dem lokalen Index und liefert bereinigte, begrenzte Ergebnisse.
- ADR-006 wird konkretisiert: Onion-Zone, Human Approval und Offline-/Index-Suche werden technisch getrennt.
- Discovery und Crawling erhalten hohe Kohäsion und niedrigere Kopplung zum Orchestrator.
- Der Ressourcenverbrauch bleibt passend für eine GTX-1070-Workstation, weil Discovery/Crawling CPU-/I/O-lastig und außerhalb paralleler LLM-Last planbar ist.

### Negative

- Whoosh begrenzt spätere Skalierung bei sehr großen Onion-Korpora oder hohen Write-Raten.
- Die Einführung von Seed Queue, Policy Gateway, Human Review Queue und Klassifikation erhöht die Komplexität gegenüber dem bisherigen Single-Crawler.
- Mehr Tests sind nötig: Zonentrennung, Policy-Entscheidungen, Opt-out/Blocklist, Rate-Limits, Index-Rebuilds und Retriever-Ausgabeformat.
- Human Approval kann Discovery verlangsamen und benötigt Bedien-/Review-Prozesse.

### Neutral

- T-005 wird von „ein Crawler-Skript“ zu einer Sammlung von Crawler/Fetche-Strategien unter einer Onion-Discovery-Pipeline.
- T-006 bleibt Whoosh-basiert, sollte aber ein Index Repository und ein erweitertes Schema erhalten, z. B. `source_id`, `onion_host_hash`, `synthetic_uri`, `title`, `content`, `content_hash`, `retrieved_at`, `classification`, `risk_level`, `approval_status`.
- `CompositeRetriever` bleibt das Integrationsmuster, sollte Onion-Ergebnisse aber nur aus `approval_status=approved` und mit synthetischen URIs ausgeben.
- GPT-Researcher bekommt keine Onion-Live-Suche, sondern eine lokale Search-API/Custom-Retriever-Schicht über freigegebene Indexdaten.

### Erforderliche Sicherheitsgrenzen

- **Blocklist:** Host-, URL-, Pattern- und Content-Type-Blocklist vor Fetch, vor Speicherung und vor Ausgabe prüfen.
- **Opt-out:** lokale Opt-out-Liste für Onion-Hosts/URLs; Treffer werden nicht gecrawlt, nicht indexiert und nicht ausgegeben.
- **Rate-Limits:** per Host und global; konservative Defaults, Jitter und Backoff bei Fehlern.
- **Seed-Allowlist:** Discovery startet nur aus explizit konfigurierten Seeds; kein Onion-Bruteforce.
- **No-live-retrieval:** GPT-Researcher-Retriever darf nie Tor-Fetches auslösen.
- **Human Approval:** dauerhafte Speicherung und Ausgabe nur nach Freigabe.
- **Content-Safety:** keine automatische Binary-Verarbeitung, keine Skriptausführung, Textgröße begrenzen, Secrets/PII nicht loggen.
- **Network Boundary:** Onion-Worker nutzt nur Tor-SOCKS mit Remote-DNS (`socks5h`); Clearnet-Worker blockieren `.onion`.
- **Audit:** Discovery-Entscheidungen, Policy-Rejections und Approval-Status werden protokolliert, aber ohne sensible Rohinhalte in Logs.

## References

- Issue #12: <https://github.com/xxammaxx/Researcher/issues/12>
- ADR-006: `docs/adr/006-evidence-first-pipeline.md`
- `design.md` — ADR-002 CompositeRetriever-Pattern, ADR-004 Whoosh, ADR-005 synthetische Darknet-URIs
- `docs/architecture.md` — C4-Kontext, Komponenten, Netzwerk- und Sicherheitsannahmen
- `docs/module-map.md` — Module `Search_Composite`, `Darknet_Crawler`, `Darknet_Search`, `Darknet_Index`
- `docs/dependency-graph.md` — T-005 → T-006 → T-007 kritischer Pfad
- `tasks.md` — T-005 Darknet-Crawler, T-006 Whoosh-Index + DarknetRetriever, T-007 CompositeRetriever
- `researcher_research_first_rule.md` — Onion/Tor-Regeln, Custom-Retriever-Format, keine Live-Tor-Abfragen im Retriever
- `blueprint.md` Abschnitt 3 — Darknet-Crawler mit Tor-SOCKS5 und Whoosh
- Tor Rendezvous Specification v3: <https://spec.torproject.org/rend-spec-v3>
