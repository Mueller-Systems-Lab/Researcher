# Fresh Clone Onboarding

**Datum:** 2026-05-19  
**Ziel:** Reproduzierbarer Pfad von `git clone` zu grünen Quality Gates  

---

## Getestete Umgebung

| Feld | Wert |
|---|---|
| OS | Linux (Ubuntu 24.04, x86_64) |
| Python | 3.12.3 |
| pip | 25.0 |
| Branch | `qa/accessibility-tests` |
| Commit | `1cd7c9f` |
| Docker | Verfügbar (optional) |
| GPU | Nicht vorhanden (optional) |

---

## Schritte

### 1. Clone & Submodule

```bash
git clone https://github.com/Mueller-Systems-Lab/Researcher.git
cd Researcher
git submodule update --init --recursive
```

### 2. Virtuelle Umgebung

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Quality Gates

```bash
make quality        # lint + typecheck + security-project + test-fast
make coverage       # ≥78%
make test-e2e       # E2E Pipeline
make ci-local       # Alles zusammen
```

---

## Quality Gates (Erwartete Ergebnisse)

| Befehl | Erwartung | Laufzeit | Status |
|---|---|---|---|
| `make quality` | 0 Errors, 195 passed | ~30s | ✅ |
| `make coverage` | ≥78% | ~10s | ✅ 78.5% |
| `make test-e2e` | 9 passed | <2s | ✅ |
| `make ci-local` | Alle Gates grün | ~45s | ✅ |

---

## Optionale Dienste (nicht für Quality Loop nötig)

| Dienst | Zweck | Befehl |
|---|---|---|
| Ollama | Lokales LLM | `ollama serve` |
| SearXNG | Lokale Websuche | `docker compose up searxng` |
| Tor | Onion/Darknet | `tor` (systemd service) |
| GPU/NVIDIA | GPU-Monitor | `nvidia-smi` |
| Playwright | Visual/Accessibility | `playwright install chromium` |
| Benchmarks | Performance | `make test-benchmarks` |

---

## Troubleshooting

### Python-Version zu alt

```bash
python3 --version
# Erwartet: >= 3.11
```

**Fix:** Python 3.11+ installieren (via `apt`, `brew`, `pyenv`).

---

### Submodul nicht initialisiert

```bash
git submodule update --init --recursive
```

Fehler ohne Submodul: `ImportError: No module named 'gpt_researcher'`.

---

### `bandit` nicht gefunden

```bash
pip install bandit
```

Bandit ist in `requirements.txt` enthalten, aber bei System-Python (PEP 668) kann `--break-system-packages` nötig sein.

---

### Virtuelle Umgebung nicht aktiviert

```bash
source .venv/bin/activate
which python  # sollte auf .venv zeigen
```

---

### Playwright-Browser fehlen (optional)

```bash
python -m playwright install chromium
```

Nur für `make playwright` nötig. Nicht Teil von `make quality` oder `make ci-local`.

---

### Docker/Ollama/SearXNG/Tor nicht verfügbar

Alle Quality Gates (`make quality`, `make coverage`, `make test-e2e`) laufen ohne diese Dienste. Nur für echte Research-Ausführung nötig.

---

## Bekannte Grenzen

- `make test-fast` ignoriert: benchmarks, e2e, playwright-accessibility, playwright-visual
- `make coverage` verwendet denselben Ignore-Set
- `make ci-full` (~5min) inkludiert Benchmarks (optional)
- Echte Runtime-Tests (Ollama, SearXNG) nur mit `RUN_E2E_TESTS=true`

---

## Nächste Verbesserungen

1. `make doctor` — automatische Umgebungsprüfung
2. CI-Badge für `make quality` Status
3. Docker-Dev-Container für reproduzierbare Umgebung
