# Dependency Research — 2026-05-16

## Summary
- Dependencies checked: 12
- CVEs found: 16 direkt/relevant geprüft
- Updates recommended: 7

## Findings

### gpt-researcher v0.14.8
- **Current used:** v0.14.8
- **Latest stable:** v0.14.8 (PyPI 2026-03-13)
- **CVEs:** CVE-2026-5625, CVE-2026-5630, CVE-2026-5631, CVE-2026-5632, CVE-2026-5633
- **Assessment:** caution — XSS, Code Injection, Missing Auth, SSRF
- **Recommendation:** Nur lokal betreiben, nicht öffentlich exponieren

### Whoosh v2.7.4
- **Current used:** v2.7.4
- **Latest stable:** v2.7.4 (PyPI 2016-04-04) — **unmaintained**
- **CVEs:** Keine bekannten
- **Assessment:** caution — funktional OK für lokalen Index, aber 10 Jahre alt
- **Recommendation:** Mittelfristig Alternative prüfen (ADR-008)

### chromadb v1.5.9
- **Current used:** `>=0.5.0`
- **Latest stable:** v1.5.9 (PyPI 2026-05-05)
- **CVEs:** Keine direkten ChromaDB-CVEs
- **Assessment:** update recommended
- **Recommendation:** Auf aktuelle 1.x pinnen

### requests v2.34.2
- **Current used:** `>=2.32.3`
- **Latest stable:** v2.34.2 (PyPI 2026-05-14)
- **CVEs:** Keine aktuellen für v2.34.2
- **Assessment:** update recommended
- **Recommendation:** Untergrenze auf 2.34.2 erhöhen

### lxml v6.1.0
- **Current used:** transitiv
- **Latest stable:** v6.1.0 (PyPI 2026-04-18)
- **CVEs:** CVE-2026-41066 (XXE vor 6.1.0)
- **Assessment:** update recommended
- **Recommendation:** `lxml>=6.1.0` pinnen

### ollama
- **Current used:** nicht gepinnt
- **Latest stable:** v0.24.0 (GitHub 2026-05-14)
- **CVEs:** Mehrere historische (CVE-2024-28224, -37032, -45436 u.a.)
- **Assessment:** update recommended
- **Recommendation:** Auf v0.24.0 aktualisieren, Port 11434 localhost-only

### pynvml / nvidia-ml-py
- **pynvml v13.0.1:** deprecated/inactive — **nicht verwenden**
- **nvidia-ml-py v13.595.45:** aktuell, maintained
- **Recommendation:** Auf `nvidia-ml-py` migrieren

### SearXNG
- **Current used:** Docker, nicht gepinnt
- **Latest stable:** master 2026.5.15+afafca93f
- **CVEs:** Keine bekannten
- **Assessment:** caution
- **Recommendation:** Docker-Image pinnen, `secret_key` setzen

### Tor SOCKS5
- **Current used:** `socks5h://127.0.0.1:9050` ✅ (DNS-Leak-Schutz aktiv)
- **CVEs:** Keine aktuellen
- **Assessment:** safe bei korrekter Konfiguration
- **Recommendation:** Stream-Isolation via SOCKS5 Username/Password für Identitätsschutz

## Schlussfolgerung

### Sofort handeln
1. **pynvml → nvidia-ml-py** migrieren (deprecated)
2. **lxml >=6.1.0** pinnen (CVE-2026-41066)
3. **requests >=2.34.2** pinnen (aktueller Patchstand)
4. **Ollama** auf v0.24.0 aktualisieren

### Nächste Iteration
5. **chromadb** auf 1.x pinnen
6. **SearXNG** Docker-Image pinnen
7. **Whoosh** mittelfristig ersetzen (ADR-008)

### Sicher betreibbar
- gpt-researcher nur lokal
- beautifulsoup4 / playwright ohne bekannte CVEs
- Tor SOCKS5 korrekt konfiguriert (socks5h)
