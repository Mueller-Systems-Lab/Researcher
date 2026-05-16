# Issue Prompt: T-005

## Ziel
Tor-SOCKS5-Verbindung konfigurieren, Login-Skript mit CSRF-Token-Extraktion, Thread-Crawler mit HTML-Parsing (BeautifulSoup), Crawl-Pausen und Rate-Limiting, Cron-Job für periodische Ausführung.

## Kontext
Der Darknet-Crawler ist die kritischste Eigenentwicklung. Er crawlt ein Darknet-Forum über Tor und extrahiert Thread-Inhalte. Sicherheit und Isolierung haben höchste Priorität.

## Betroffene Module
- `Darknet_Crawler`

## Relevante Dateien
- `crawlers/darknet_crawler.py`
- `crawlers/__init__.py`
- Cron-Job-Definition (`crontab` oder Systemd-Timer)
- `requirements.txt` (ggf. ergänzen: `requests[socks]`, `beautifulsoup4`, `lxml`)

## Architekturregeln
- Tor MUSS über SOCKS5-Proxy (`socks5h://127.0.0.1:9050`) genutzt werden
- Login MUSS CSRF-Token-Extraktion unterstützen
- Crawler DARF KEIN JavaScript ausführen (nur BeautifulSoup/LXML – passiv)
- `time.sleep()` MUSS zwischen Requests eingehalten werden (min. 2 Sekunden)
- Cookies und Sessions automatisch von `requests` verwalten lassen
- Wegwerf-Account verwenden – NIEMALS persönliche Daten assoziieren

## Best Practices
- Crawl-Pausen dynamisch anpassen (exponentielles Backoff bei Fehlern)
- User-Agent setzen (realistischer Browser-String)
- Fehlerbehandlung: Timeout, Connection-Error, HTTP-Error (403, 429, 5xx)
- Logging für Debugging und Audit
- Crawl-Ergebnisse als JSONL für Wiederverwendbarkeit zwischenspeichern

## Akzeptanzkriterien
- **GIVEN** Tor läuft auf 127.0.0.1:9050 **WHEN** der Crawler gestartet wird **THEN** werden Forum-Posts mit URL, Autor, Timestamp und Content extrahiert.
- **GIVEN** der Crawler läuft **WHEN** eine Seite gecrawlt wird **THEN** wird `time.sleep()` zwischen Requests eingehalten (min. 2 Sekunden).

## Tests
- Tor-Verfügbarkeit prüfen: `curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org`
- Crawler mit Test-URL (öffentliches Forum ohne Login) testen
- HTML-Parsing mit Beispiel-HTML validieren
- CSRF-Extraktion mit Mock-HTML testen
- `time.sleep()` via Mock/Spy verifizieren

## Risiken
- 🔴 Hoch – Rechtliche Risiken (Darknet-Crawling); Technisch: Forum kann Crawler blocken
