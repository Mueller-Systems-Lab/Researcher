# Troubleshooting

## Schnelle Diagnose

Wenn eine Recherche fehlschlägt, prüfe zuerst diese Komponenten in Reihenfolge:

1. `ollama serve`
2. SearXNG-Container (`docker compose -f searxng/docker-compose.yml up -d`)
3. Gemma 4 Chat-Modell auf Port `8081` (`./serve_gemma4_obliterated_researcher.sh`)
4. Ollama auf Port `11434` für Embeddings
5. Tor auf `9050`
6. GPT Researcher Web-UI

## Häufige Fehler

| Fehler | Woran erkennbar? | Wahrscheinliche Ursache | Lösung | Prävention |
|---|---|---|---|---|
| Ollama nicht gestartet | `ollama list` oder Modellaufrufe schlagen sofort fehl | `ollama serve` läuft nicht | 1. `ollama serve` starten.<br>2. In einem zweiten Terminal `ollama list` prüfen.<br>3. Danach Recherche neu starten. | Ollama vor der Web-UI starten. |
| Gemma 4 Chat-Modell startet nicht | `./serve_gemma4_obliterated_researcher.sh` schlägt fehl | GGUF-Datei fehlt oder Pfad falsch | 1. Prüfen: `ls -la /home/xxammaxx/Schreibtisch/gemma4/llama.cpp/models/gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf`<br>2. `llama-server` im Build-Pfad prüfen<br>3. Port 8081 prüfen: `lsof -ti :8081`<br>4. Server neu starten. | Vor dem Start `./research-serve.sh status` ausführen. |
| Port 8081/8086 belegt | Start des Modellservers endet mit Port-Fehler | Ein anderer Prozess blockiert den Port | 1. `lsof -ti :8081` oder `lsof -ti :8086` ausführen.<br>2. PID mit `kill <PID>` beenden.<br>3. Server neu starten. | Vor dem Start `./research-serve.sh status` ausführen. |
| SearXNG nicht erreichbar (Connection refused :8080) | `curl http://localhost:8080/...` bricht ab | Container läuft nicht oder ist abgestürzt | 1. `docker compose -f searxng/docker-compose.yml ps` prüfen.<br>2. Container neu starten.<br>3. Erreichbarkeit mit `curl http://localhost:8080/search?q=test&format=json` testen. | SearXNG vor der Recherche starten und Port nur an `127.0.0.1` binden. |
| VRAM-Überlauf (OOM / CUDA Out of Memory) | Abbruch bei langen Antworten oder Modellstart | `num_ctx` zu groß, Modell zu groß, parallele Anfragen | 1. `num_ctx` auf `4096` setzen.<br>2. `MAX_CONCURRENT_REQUESTS=1` setzen.<br>3. `OLLAMA_NUM_PARALLEL=1` setzen.<br>4. Andere Modellserver stoppen und erneut testen. | Auf GTX 1070 nur einen Modellserver gleichzeitig betreiben. |
| Darknet-Index leer | Darknet-Suchergebnisse fehlen komplett | Kein Crawler-Lauf ausgeführt | 1. Crawler starten.<br>2. Forum-Login prüfen.<br>3. Indexpfad `DARKNET_INDEX_PATH` kontrollieren.<br>4. Neu indexieren. | Crawler regelmäßig per Cron/Job ausführen. |
| Tor-Verbindung fehlschlägt | Crawler meldet Proxy-/Timeout-Fehler | Tor läuft nicht auf `:9050` | 1. `systemctl start tor` ausführen.<br>2. Prüfen, ob `127.0.0.1:9050` erreichbar ist.<br>3. Crawler erneut starten. | Tor vor dem Crawler starten. |
| GPT Researcher Web-UI startet nicht | Python-Prozess endet mit Import- oder Modulfehlern | Fehlende Abhängigkeiten oder falsche Python-Version | 1. Python-Version prüfen (`>=3.11`).<br>2. `pip install -r requirements.txt` ausführen.<br>3. Virtuelle Umgebung aktivieren und erneut starten. | Immer aus der aktiven `.venv` heraus arbeiten. |
| `requests.exceptions.ConnectionError` bei SearXNG | Recherche bricht beim Suchen ab | SearXNG nicht gestartet oder falsche URL | 1. `SEARX_URL` in `.env` prüfen.<br>2. SearXNG-Container kontrollieren.<br>3. `curl`-Test gegen die konfigurierte URL ausführen. | `.env` nach Änderungen neu laden und testen. |
| `ollama: command not found` | Der Shell-Befehl ist nicht verfügbar | Ollama nicht installiert | 1. Ollama installieren, z. B. mit `curl -fsSL https://ollama.com/install.sh | sh`.<br>2. Neues Terminal öffnen.<br>3. `ollama serve` erneut starten. | Installation direkt nach der Systemeinrichtung prüfen. |
| Docker-Container startet nicht | `docker compose -f searxng/docker-compose.yml up -d` schlägt fehl oder Container beendet sich sofort | Docker nicht installiert oder Dienst nicht aktiv | 1. Docker installieren oder Dienst starten.<br>2. `sudo systemctl start docker` ausführen.<br>3. SearXNG-Container neu starten. | Vor dem SearXNG-Start `docker compose -f searxng/docker-compose.yml ps` prüfen. |
| Keine Ergebnisse in der Recherche | Bericht bleibt leer oder sehr kurz | Keine Such-Backends verfügbar | 1. Gemma 4 Chat (Port 8081), Ollama (Port 11434), SearXNG, Tor und den Darknet-Index prüfen.<br>2. `./research-serve.sh status` ausführen.<br>3. CompositeRetriever-Logs kontrollieren.<br>4. Danach erneut suchen. | Vor einer Recherche alle Backends kurz testen. |

## Zusätzliche Prüfkommandos

```bash
ollama list
./research-serve.sh status
docker ps
curl http://localhost:8080/search?q=test&format=json
```

## Wenn nichts hilft

1. Alle Modellserver stoppen: `./research-serve.sh stop`
2. SearXNG und Ollama neu starten
3. Das Problem mit den letzten Logmeldungen eingrenzen
4. Erst danach die Recherche erneut starten
