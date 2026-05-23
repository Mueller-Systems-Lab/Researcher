# Local Runtime Smoke Test

**Datum:** 2026-05-19  
**Scope:** Optionaler Healthcheck für lokale Runtime-Dienste  

---

## Ziel

Validiert, dass die lokale Research-Runtime (Ollama, SearXNG, Tor) korrekt läuft und keine Cloud-Provider aktiv sind.

---

## Was geprüft wird

| Dienst | Default | Standard | Strict Mode |
|---|---|---|---|
| Ollama | `localhost:11434` | ⚠️ Warnung | ✅ Pflicht |
| SearXNG | `localhost:8080` | ⚠️ Warnung | ✅ Pflicht |
| Tor | `127.0.0.1:9050` | ⚠️ Warnung | ✅ Pflicht |
| Cloud-Blocker | Env-Vars | ✅ Pflicht | ✅ Pflicht |

---

## Befehle

```bash
# Standard (Warnung bei fehlenden optionalen Diensten)
make runtime-smoke

# Strict (alle Dienste müssen laufen)
make runtime-smoke-strict
```

---

## Erwartete Ausgabe (Standard, alle Dienste verfügbar)

```
🔍 Researcher Runtime Smoke Test
   Ollama:  http://localhost:11434
   SearXNG: http://localhost:8080
   Tor:     127.0.0.1:9050

☁️  Cloud-Blocker:
  ✅ Keine Cloud-Provider ohne ALLOW_CLOUD

🦙 Ollama:
  ✅ Ollama (http://localhost:11434) — Modell: nomic-embed-text:latest

🔎 SearXNG:
  ✅ SearXNG (http://localhost:8080) — 3 results

🧅 Tor:
  ✅ Tor SOCKS5 (127.0.0.1:9050)

──────────────────────────────────────────────────
Ergebnis: 4/4 Dienste erreichbar
✅ Alle Pflicht-Dienste OK
```

---

## Dienste starten

### Ollama

```bash
ollama serve
ollama pull nomic-embed-text:latest
```

### SearXNG

```bash
docker compose up searxng -d
```

### Tor

```bash
sudo systemctl start tor
```

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| Ollama nicht erreichbar | `ollama serve` starten |
| Modell fehlt | `ollama pull nomic-embed-text:latest` |
| SearXNG nicht erreichbar | `docker compose up searxng -d` |
| SearXNG keine Ergebnisse | SearXNG-Instanz prüfen, `docker logs searxng` |
| Tor nicht erreichbar | `sudo systemctl start tor` |
| Cloud-Provider aktiv | `ALLOW_CLOUD=true` setzen oder Provider deaktivieren |

---

## CI-Hinweis

Dieser Test ist **nicht Teil** von `make quality` oder `make ci-local`. Er ist optional und erfordert laufende lokale Dienste.
