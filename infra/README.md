# Researcher — Lokaler Stack mit LLM/Embedding-Trennung

## Architektur

```
┌────────────────────────────────────────────────┐
│  GPT Researcher (Orchestrator)                 │
│                                                │
│  LLM-Requests ──────────► Ollama (GPU)         │
│                            └─ qwen35-uncensored│
│                               dauerhaft in VRAM│
│                                                │
│  Embedding-Requests ────► sentence-transformers│
│                            └─ nomic-embed-text  │
│                               CPU-only          │
│                                                │
│  Search ────────────────► SearXNG (lokal)      │
│  Vector-DB ─────────────► ChromaDB (lokal)     │
└────────────────────────────────────────────────┘
```

## Setup-Reihenfolge

### 1. Modell herunterladen
```bash
chmod +x download_model.sh
./download_model.sh
```

### 2. Ollama-Modell registrieren
```bash
cd ~/models/qwen35-uncensored
ollama create qwen35-uncensored -f Modelfile
```

### 3. Ollama systemd optimieren
```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo cp override.conf /etc/systemd/system/ollama.service.d/
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 4. LLM im VRAM pinnen
```bash
chmod +x pin_llm.sh
./pin_llm.sh
```

### 5. Python Embedding-Umgebung
```bash
pip install sentence-transformers langchain-huggingface
python3 test_embeddings.py
```

### 6. .env kopieren
```bash
cp .env /pfad/zu/gpt-researcher/.env
```

### 7. Validieren
```bash
chmod +x check_vram.sh
./check_vram.sh

python3 integration_test.py
```

## Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| `ollama ps` zeigt 0 Modelle | LLM nicht gepinnt | `./pin_llm.sh` ausführen |
| VRAM > 7 GB | LLM + Embedding beide in Ollama | `EMBEDDING=huggingface:...` in .env prüfen |
| `test_embeddings.py`: CUDA erkannt | sentence-transformers nutzt GPU | `device="cpu"` im Code prüfen |
| `integration_test.py`: VRAM-Delta > 0 | Embeddings nutzen GPU | Ollama-Embedding deaktivieren |

## VRAM-Budget

| Komponente | VRAM |
|---|---|
| Qwen 3.5 9B Q4_K_M | ~5.6 GB |
| KV-Cache (ctx=2048) | ~0.3 GB |
| CUDA Overhead | ~0.3 GB |
| **Summe LLM** | **~6.2 GB** |
| Embeddings (CPU) | 0 GB |
| **Frei** | **~1.8 GB** |
