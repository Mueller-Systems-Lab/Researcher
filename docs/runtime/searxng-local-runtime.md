# SearXNG Local Runtime

**Datum:** 2026-05-19  
**Scope:** SearXNG-Integration für lokale Websuche  

---

## Ziel

SearXNG lokal starten, prüfen und debuggen. Kein Google/Bing/DuckDuckGo — nur lokale Metasuche.

---

## Starten

```bash
make searxng-up
# docker compose -f searxng/docker-compose.yml up -d
```

## Prüfen

```bash
# Nur SearXNG checken
make searxng-smoke

# Kompletter Runtime-Check
make runtime-smoke

# Direkter API-Test
curl "http://localhost:8080/search?q=test&format=json" --max-time 30
```

---

## Logs

```bash
make searxng-logs
# docker compose -f searxng/docker-compose.yml logs --tail=100
```

---

## Stoppen

```bash
make searxng-down
# docker compose -f searxng/docker-compose.yml down
```

---

## Fehlerklassen im Smoke-Test

| Klasse | Bedeutung | Lösung |
|---|---|---|
| `NOT_RUNNING` | Container nicht gestartet/Port nicht erreichbar | `make searxng-up` |
| `TIMEOUT` | Antwort dauert länger als konfiguriert | `SEARXNG_TIMEOUT_SECONDS=30` erhöhen |
| `BAD_STATUS` | HTTP-Status ≠ 200 | `make searxng-logs` prüfen |
| `BAD_JSON` | Antwort ist kein gültiges JSON | `format=json` im Request prüfen |
| `NO_RESULTS` | Erreichbar, aber keine Treffer für Test-Query | SearXNG-Engine-Konfiguration prüfen |
| `OK` | Ergebnisliste > 0 | — |

---

## Timeout konfigurieren

```bash
# Höherer Timeout (SearXNG kann beim ersten Request 20s+ brauchen)
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke

# Dauerhaft in .env
echo "SEARXNG_TIMEOUT_SECONDS=30" >> .env
```

---

## Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Timeout beim ersten Request | SearXNG initialisiert Engines | `SEARXNG_TIMEOUT_SECONDS=30`, Check `docker logs searxng` |
| 403/429 | SearXNG-Limiter aktiv | `searxng/settings.yml` prüfen |
| Keine Ergebnisse | Keine Engines konfiguriert/aktiv | `searxng/settings.yml`: `use_default_settings: true` |
| Port 8080 belegt | Anderer Dienst auf 8080 | `SEARX_URL=http://localhost:8081` setzen |

---

## CI-Hinweis

SearXNG-Tests sind optional und nicht Teil von `make quality` oder CI. Docker muss lokal verfügbar sein.
