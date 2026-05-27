# v0.1.0-local-alpha — Erste lokale Research-Release

Erste validierte lokale Research-Pipeline-Release, vollständig ohne Cloud-Abhängigkeiten.

## Highlights

- ✅ **716 Tests bestanden**, 0 Failed, 85.06% Coverage
- ✅ **0 Lint Errors**, **0 Typecheck Errors**, **0 Security Findings (Medium+)**
- ✅ **ChromaDB count-Bug** gefixt (count=-1 → 0 bei fehlender Verbindung)
- ✅ **Security-Gate**: B310 (urlopen) + B314 (XML-Parsing) behoben, `defusedxml` integriert
- ✅ **Integrationstest** der kompletten Research-Pipeline (16 Tests)
- ✅ **Mock-Audit**: 20 Mock-Probleme durch echte Implementierungen ersetzt
- ✅ **Evidence Store**: Run-ID-Scoping für isolierte Quellen pro Research-Durchlauf
- ✅ **Verbindungs-Checker** erweitert: API, Plan-Roundtrip, Evidence Store
- ✅ **14 Security-Regression-Tests** (Timeouts, Cloud-Blocker, Hashing, SQL, SSL)
- ✅ **Zero Cloud Dependencies**: OpenAI, Tavily, Anthropic standardmäßig blockiert

## Quality Metrics

| Metrik | Wert |
|---|---|
| **Tests** | 716 passed, 0 failed |
| **Coverage** | 85.06% (≥81%) |
| **Lint** | 0 ruff Errors |
| **Typecheck** | 0 mypy Errors (91 source files) |
| **Security (Projekt)** | 0 Medium/High Bandit Findings |
| **Security (Vendor)** | 20 dokumentiert, report-only |

## Verification

```bash
make coverage-fast          # 716 passed
make security-project       # 0 Medium/High
make lint                   # 0 Errors
make typecheck              # 0 Errors
```

## Known Limitations

- **Alpha-Release** — keine Produktionsvalidierung
- **Chat-Modell: Gemma 4 OBLITERATED** via llama-server (Port 8081, ~3.8 GB VRAM) — stabiler als qwen3.5-Vorgänger
- **Embedding: nomic-embed-text** via Ollama (Port 11434)
- **ChromaDB 1.5.9** — `count()` gibt `-1` statt `0` bei fehlender DB (lokal abgefangen)
- **SSE blockiert Playwright** — `networkidle`-Wait hängt wegen SSE-Stream
- **SearXNG** benötigt lokalen Docker
- **Ollama nur noch für Embedding** (nomic-embed-text), Chat läuft eigenständig via llama.cpp
- **Report-Evaluation** ist heuristisch, keine Faktenverifikation

Siehe `docs/release/known-limitations.md` für Details.

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).
