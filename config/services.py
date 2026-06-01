# =============================================================================
# Centralized Service URL Configuration
# =============================================================================
# Einzige Quelle der Wahrheit für alle Service-URLs und Ports.
# Jede Datei im Projekt sollte von hier importieren statt selbst
# URLs hardcoded zu definieren.
#
# Alle URLs haben einen env-var override via os.getenv.
# =============================================================================

import os

# ── Ollama ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_URL: str = f"{OLLAMA_BASE_URL}/api"

# ── SearXNG ─────────────────────────────────────────────────────────────────
SEARXNG_URL: str = os.getenv(
    "SEARXNG_URL", os.getenv("SEARX_URL", "http://localhost:8080")
)
SEARXNG_SEARCH_URL: str = f"{SEARXNG_URL}/search"

# ── Tor ─────────────────────────────────────────────────────────────────────
TOR_HOST: str = os.getenv("TOR_HOST", "127.0.0.1")
TOR_PORT: int = int(os.getenv("TOR_PORT", "9050"))
TOR_PROXY: str = os.getenv("TOR_PROXY", f"socks5h://{TOR_HOST}:{TOR_PORT}")

# ── Dashboard ───────────────────────────────────────────────────────────────
DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8888"))
DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "127.0.0.1")

# ── MCP Server ──────────────────────────────────────────────────────────────
MCP_PORT: int = int(os.getenv("MCP_PORT", "8766"))
MCP_HOST: str = os.getenv("MCP_HOST", "127.0.0.1")

# ── Llama Server (OpenAI-compatible) ────────────────────────────────────────
LLAMA_SERVER_URL: str = os.getenv(
    "OPENAI_BASE_URL",
    os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8082/v1"),
)

# ── Embedding ───────────────────────────────────────────────────────────────
OLLAMA_EMBEDDING_MODEL: str = os.getenv(
    "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
)
# PRIMARY Chat-Modell: Qwen3.5-Uncensored-HauhauCS via llama-server
#   FAST_LLM=openai:qwen3.5-uncensored (OPENAI_BASE_URL, Port 8082)
# OLLAMA_CHAT_MODEL ist NUR der Fallback, wenn INFERENCE_BACKEND=ollama gesetzt ist.
# Siehe docs/adr/ADR-016-gemma4-chat-model.md
OLLAMA_CHAT_MODEL: str = os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5:9b")  # DEPRECATED

# ── Storage Paths ───────────────────────────────────────────────────────────
CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
DARKNET_INDEX_PATH: str = os.getenv("DARKNET_INDEX_PATH", "./darknet_index")
AUDIT_LOG_FILE: str = os.getenv("AUDIT_LOG_FILE", "./audit_trail.jsonl")
ONION_SEED_FILE: str = os.getenv("ONION_SEED_FILE", "./onion_seeds.json")
ONION_REVIEW_FILE: str = os.getenv("ONION_REVIEW_FILE", "./onion_review_queue.json")

# ── Other ───────────────────────────────────────────────────────────────────
SEARXNG_TIMEOUT: int = int(os.getenv("SEARXNG_TIMEOUT", "30"))
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
TOR_TIMEOUT: int = int(os.getenv("TOR_TIMEOUT", "10"))
MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "10"))
