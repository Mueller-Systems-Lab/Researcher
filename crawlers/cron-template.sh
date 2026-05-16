#!/bin/bash
# =============================================================================
# Cron-Job-Vorlage für den Darknet-Crawler
# =============================================================================
# Führt den Darknet-Crawler periodisch aus (z. B. alle 6 Stunden).
#
# Installation:
#   crontab -e
#   Füge folgende Zeile hinzu:
#     0 */6 * * * /pfad/zu/researcher/crawlers/cron-template.sh
#
# Wichtig:
#   - .env muss im PROJECT_ROOT vorhanden sein
#   - Tor muss laufen (systemctl start tor)
#   - Forum-Login muss gültig sein
# =============================================================================

set -euo pipefail

# === KONFIGURATION (anpassen) ===
PROJECT_ROOT="/home/xxammaxx/Schreibtisch/Researcher"
VENV_PATH="$PROJECT_ROOT/.venv"
LOG_DIR="$PROJECT_ROOT/logs"
MAX_PAGES="${CRAWL_MAX_PAGES:-5}"

# === LOGGING ===
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/crawler-$TIMESTAMP.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# === AUSFÜHRUNG ===
log "=== Darknet-Crawler gestartet ==="
log "Max Seiten: $MAX_PAGES"

# Aktivierung der virtuellen Umgebung
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    log "Venv aktiviert: $VENV_PATH"
else
    log "WARNUNG: Kein Venv gefunden unter $VENV_PATH"
fi

# Wechsel ins Projektverzeichnis
cd "$PROJECT_ROOT"

# Prüfe ob Tor läuft
if curl -s --socks5-hostname 127.0.0.1:9050 \
    --max-time 5 http://check.torproject.org/api/ip > /dev/null 2>&1; then
    log "Tor-Verbindung OK"
else
    log "FEHLER: Tor läuft nicht auf 127.0.0.1:9050"
    log "Crawling abgebrochen"
    exit 1
fi

# Crawler ausführen
python -m crawlers.darknet_crawler --max-pages "$MAX_PAGES" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    log "=== Crawler erfolgreich beendet ==="
else
    log "=== Crawler mit Fehler beendet (Exit: $EXIT_CODE) ==="
fi

exit $EXIT_CODE
