#!/usr/bin/env bash
# =============================================================================
# start_all_services.sh — Researcher Infrastructure Autostart
# =============================================================================
# Starts all 5 core services with healthchecks, retry logic, and logging.
# Phase 8: Quality Hardening (Issue #143)
#
# Usage:
#   ./start_all_services.sh           # Start all services
#   ./start_all_services.sh --status  # Show service status
#   ./start_all_services.sh --stop    # Stop all services
#
# Logs: /var/log/researcher/
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    LOG_DIR="${LOG_DIR:-${RUNNER_TEMP:-/tmp}/researcher-logs}"
else
    LOG_DIR="${LOG_DIR:-/var/log/researcher}"
fi
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Port definitions
PORT_OLLAMA=11434
PORT_LLAMA=8082
PORT_SEARXNG=8090
PORT_GPTR=28202
PORT_DASHBOARD=8888

# Healthcheck settings
HEALTHCHECK_RETRIES=30
HEALTHCHECK_INTERVAL=2
HEALTHCHECK_TIMEOUT=5

# Create log directory
mkdir -p "$LOG_DIR"

# ── Logging ──────────────────────────────────────────────────────────────────
log() {
    local level="$1"; shift
    echo "[$(date +%H:%M:%S)] [$level] $*" | tee -a "$LOG_DIR/startup_${TIMESTAMP}.log"
}

log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

# ── Healthcheck Function ─────────────────────────────────────────────────────
# Usage: healthcheck "Service Name" PORT PATH [EXPECTED_STRING]
healthcheck() {
    local name="$1"
    local port="$2"
    local path="${3:-/}"
    local expect="${4:-}"

    log_info "Healthcheck: $name (port $port)..."
    for i in $(seq 1 $HEALTHCHECK_RETRIES); do
        if curl -s --max-time "$HEALTHCHECK_TIMEOUT" "http://127.0.0.1:${port}${path}" > /dev/null 2>&1; then
            if [ -n "$expect" ]; then
                if curl -s --max-time "$HEALTHCHECK_TIMEOUT" "http://127.0.0.1:${port}${path}" | grep -q "$expect"; then
                    log_info "  ✅ $name ready (attempt $i)"
                    return 0
                fi
            else
                log_info "  ✅ $name ready (attempt $i)"
                return 0
            fi
        fi
        sleep "$HEALTHCHECK_INTERVAL"
    done
    log_error "  ❌ $name FAILED healthcheck after $HEALTHCHECK_RETRIES attempts"
    return 1
}

# ── Service Starters ─────────────────────────────────────────────────────────

start_ollama() {
    log_info "Starting Ollama (port $PORT_OLLAMA)..."
    if curl -s --max-time 3 "http://127.0.0.1:${PORT_OLLAMA}/api/tags" > /dev/null 2>&1; then
        log_info "  Ollama already running"
        return 0
    fi
    # Start Ollama in background (system service if installed, otherwise direct)
    if systemctl --user is-active ollama > /dev/null 2>&1; then
        log_info "  Ollama systemd service already running"
    elif systemctl is-active ollama > /dev/null 2>&1; then
        log_info "  Ollama system service already running"
    else
        ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        log_info "  Ollama started (PID $!)"
    fi
    healthcheck "Ollama" "$PORT_OLLAMA" "/api/tags" || return 1
}

start_llama_server() {
    log_info "Starting llama-server Qwen3.5 (port $PORT_LLAMA)..."
    if curl -s --max-time 3 "http://127.0.0.1:${PORT_LLAMA}/health" > /dev/null 2>&1; then
        log_info "  llama-server already running"
        return 0
    fi
    if [ -f "$REPO_DIR/serve_qwen3.5_uncensored.sh" ]; then
        bash "$REPO_DIR/serve_qwen3.5_uncensored.sh" > "$LOG_DIR/llama_server.log" 2>&1 &
        echo $! > /tmp/researcher-llama.pid
        log_info "  llama-server started (PID $(cat /tmp/researcher-llama.pid))"
    else
        log_error "  serve_qwen3.5_uncensored.sh not found in $REPO_DIR"
        return 1
    fi
    healthcheck "llama-server" "$PORT_LLAMA" "/health" || return 1
}

start_searxng() {
    log_info "Starting SearXNG (port $PORT_SEARXNG)..."
    if curl -s --max-time 3 "http://127.0.0.1:${PORT_SEARXNG}/healthz" > /dev/null 2>&1; then
        log_info "  SearXNG already running"
        return 0
    fi
    if [ -f "$REPO_DIR/searxng/docker-compose.yml" ]; then
        docker compose -f "$REPO_DIR/searxng/docker-compose.yml" up -d > "$LOG_DIR/searxng.log" 2>&1 || {
            log_warn "  docker compose failed, trying 'docker-compose'..."
            docker-compose -f "$REPO_DIR/searxng/docker-compose.yml" up -d > "$LOG_DIR/searxng.log" 2>&1
        }
    else
        log_error "  searxng/docker-compose.yml not found"
        return 1
    fi
    healthcheck "SearXNG" "$PORT_SEARXNG" "/healthz" || return 1
}

start_gpt_researcher() {
    log_info "Starting GPT Researcher (port $PORT_GPTR)..."
    if curl -s --max-time 3 "http://127.0.0.1:${PORT_GPTR}/docs" > /dev/null 2>&1; then
        log_info "  GPT Researcher already running"
        return 0
    fi

    # Load environment variables
    if [ -f "$REPO_DIR/.env" ]; then
        set -o allexport
        source "$REPO_DIR/.env"
        set +o allexport
    fi

    # Check if we should use Docker or direct Python
    if command -v docker &> /dev/null && [ -f "$REPO_DIR/gpt_researcher/Dockerfile" ]; then
        # Docker-based start
        log_info "  Starting GPT Researcher via Docker..."
        docker run -d \
            --name gpt-researcher \
            -e RETRIEVER="${RETRIEVER:-searx}" \
            -e SEARX_URL="${SEARX_URL:-http://127.0.0.1:8090}" \
            -e FAST_LLM="${FAST_LLM:-openai:qwen3.5-uncensored}" \
            -e SMART_LLM="${SMART_LLM:-openai:qwen3.5-uncensored}" \
            -e STRATEGIC_LLM="${STRATEGIC_LLM:-openai:qwen3.5-uncensored}" \
            -e OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8082/v1}" \
            -e OPENAI_API_KEY="${OPENAI_API_KEY:-not-needed}" \
            -e EMBEDDING="${EMBEDDING:-ollama:nomic-embed-text:latest}" \
            -e OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}" \
            -e LANGUAGE="${LANGUAGE:-german}" \
            -p "${PORT_GPTR}:8000" \
            gptresearcher/gpt-researcher \
            > "$LOG_DIR/gpt_researcher.log" 2>&1 || {
                log_warn "  Docker start failed. Container may need to be built first."
                log_info "  Try: docker build -t gptresearcher/gpt-researcher gpt_researcher/"
                return 1
            }
    else
        # Direct Python start
        log_info "  Starting GPT Researcher via Python (port $PORT_GPTR)..."
        cd "$REPO_DIR/gpt_researcher"
        python3 -m uvicorn main:app --host 127.0.0.1 --port "$PORT_GPTR" \
            > "$LOG_DIR/gpt_researcher.log" 2>&1 &
        echo $! > /tmp/researcher-gptr.pid
        cd "$REPO_DIR"
        log_info "  GPT Researcher started (PID $(cat /tmp/researcher-gptr.pid))"
    fi
    healthcheck "GPT Researcher" "$PORT_GPTR" "/docs" || return 1
}

start_dashboard() {
    log_info "Starting Dashboard (port $PORT_DASHBOARD)..."
    if curl -s --max-time 3 "http://127.0.0.1:${PORT_DASHBOARD}/health" > /dev/null 2>&1; then
        log_info "  Dashboard already running"
        return 0
    fi
    cd "$REPO_DIR"
    python3 -m dashboard.server > "$LOG_DIR/dashboard.log" 2>&1 &
    echo $! > /tmp/researcher-dashboard.pid
    log_info "  Dashboard started (PID $(cat /tmp/researcher-dashboard.pid))"
    healthcheck "Dashboard" "$PORT_DASHBOARD" "/health" || return 1
}

# ── Status ───────────────────────────────────────────────────────────────────
show_status() {
    echo "========================================"
    echo " Researcher Service Status"
    echo "========================================"
    check_service "Ollama"          "$PORT_OLLAMA"      "/api/tags"
    check_service "llama-server"    "$PORT_LLAMA"       "/health"
    check_service "SearXNG"         "$PORT_SEARXNG"     "/healthz"
    check_service "GPT Researcher"  "$PORT_GPTR"        "/docs"
    check_service "Dashboard"       "$PORT_DASHBOARD"   "/health"
    echo "========================================"
}

check_service() {
    local name="$1" port="$2" path="$3"
    if curl -s --max-time 3 "http://127.0.0.1:${port}${path}" > /dev/null 2>&1; then
        echo "  ✅ $name (port $port) — RUNNING"
    else
        echo "  ❌ $name (port $port) — STOPPED"
    fi
}

# ── Stop ──────────────────────────────────────────────────────────────────────
stop_services() {
    log_info "Stopping all Researcher services..."

    # Stop Python services via PID files
    for pidfile in /tmp/researcher-dashboard.pid /tmp/researcher-gptr.pid /tmp/researcher-llama.pid; do
        if [ -f "$pidfile" ]; then
            kill $(cat "$pidfile") 2>/dev/null && log_info "  Stopped $(basename $pidfile .pid | sed 's/researcher-//')" || true
            rm -f "$pidfile"
        fi
    done

    # Stop Docker containers
    docker stop gpt-researcher 2>/dev/null || true
    docker compose -f "$REPO_DIR/searxng/docker-compose.yml" down 2>/dev/null || \
        docker-compose -f "$REPO_DIR/searxng/docker-compose.yml" down 2>/dev/null || true

    # Don't stop Ollama by default (may be used by other services)
    log_info "Services stopped."
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "${1:-start}" in
    --status|status)
        show_status
        exit 0
        ;;
    --stop|stop)
        stop_services
        exit 0
        ;;
    --restart|restart)
        stop_services
        sleep 2
        ;&  # fall through to start
    start|--start|*)
        log_info "========================================="
        log_info " Researcher — Starting All Services"
        log_info " Log: $LOG_DIR/startup_${TIMESTAMP}.log"
        log_info "========================================="

        FAILURES=0

        # Start in dependency order
        start_ollama            || { FAILURES=$((FAILURES+1)); log_error "Ollama FAILED"; }
        start_llama_server      || { FAILURES=$((FAILURES+1)); log_error "llama-server FAILED"; }
        start_searxng           || { FAILURES=$((FAILURES+1)); log_error "SearXNG FAILED"; }
        start_gpt_researcher    || { FAILURES=$((FAILURES+1)); log_error "GPT Researcher FAILED"; }
        start_dashboard         || { FAILURES=$((FAILURES+1)); log_error "Dashboard FAILED"; }

        echo ""
        log_info "========================================="
        if [ "$FAILURES" -eq 0 ]; then
            log_info " ✅ All 5 services started successfully!"
        else
            log_error " ⚠️  $FAILURES service(s) failed to start"
        fi
        show_status
        log_info "========================================="

        exit "$FAILURES"
        ;;
esac
