# Researcher — Nächstes Issue: Ollama Model-Name-Mismatch beheben und lokalen LLM-Summary-Pfad stabilisieren

## Rolle

Du bist ein Senior Local LLM Integration Engineer und Runtime Reliability Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-/Runtime-Chain:

- #50: Walking-Skeleton
- #51: ruff Lint 950 → 0
- #52: Bandit Triage
- #53: Submodul Security
- #54: CI Security Gate
- #55: mypy Boundary
- #56: Type Errors 33 → 0
- #57: Test Profiles
- #58: Fresh-Clone-Onboarding
- #59: Runtime Smoke
- #60: SearXNG Runtime stabilisiert
- #61: Minimal Research-Happy-Path

Dein Ziel ist NICHT, neue Research-Features zu bauen.

Dein Ziel ist, den im Happy-Path beobachteten Ollama-Model-Name-Mismatch sauber zu beheben, damit der lokale LLM-Summary-Schritt nicht nur graceful degradiert, sondern wirklich stabil funktioniert.

---

# Ausgangslage

Issue #61 hat bewiesen:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-happy-path
```

Ergebnis:

- Cloud-Blocker: ✅ keine Cloud aktiv
- Query-Safety: ✅ harmlose Query
- SearXNG: ✅ 5 results
- Ollama: ⚠️ Model-Name mismatch / 404 / graceful degradation
- Report: ✅ Markdown-Report erzeugt

Der lokale End-to-End-Wertpfad ist grundsätzlich vorhanden:

```text
Query → SearXNG → Ollama → Report
```

Aber der Ollama-Schritt ist noch nicht vollständig stabil, weil der konfigurierte Modellname nicht sauber mit den lokal verfügbaren Ollama-Modellen übereinstimmt.

---

# Oberstes Ziel dieses Issues

Stabilisiere den lokalen Ollama-Summary-Pfad:

1. Verfügbare Ollama-Modelle zuverlässig erkennen.
2. Konfigurierten Modellnamen prüfen.
3. Modellname aus `.env`, `.env.example` und Runtime-Doku konsistent machen.
4. Bei fehlendem Modell klare Handlungsempfehlung ausgeben.
5. Optional Fallback auf verfügbares lokales Modell erlauben, aber nur explizit und dokumentiert.
6. `make research-happy-path` soll mit vorhandenem lokalen Modell eine echte Summary erzeugen.
7. Keine Cloud-Fallbacks.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features implementieren
- Cloud-LLMs aktivieren
- externe API-Provider als Fallback nutzen
- große Prompt-/Report-Qualitätslogik einführen
- Ollama-Modelle automatisch ungefragt herunterladen
- GPU-/VRAM-Tuning als Hauptaufgabe behandeln
- Vendor-Code unnötig verändern
- Quality Gates lockern
- Coverage-Schwelle senken
- Tests löschen

---

# Sicherheits- und Local-First-Regeln

## Keine Cloud-Fallbacks

Wenn das Ollama-Modell fehlt, darf nicht auf OpenAI, Anthropic, Gemini, Tavily oder andere Cloud-Dienste gewechselt werden.

## Kein automatischer Modell-Download ohne explizite Zustimmung

Das Skript darf einen empfohlenen Befehl ausgeben, z. B.:

```bash
ollama pull <model>
```

Es soll ihn aber nicht automatisch ausführen.

## Explizite Modellwahl

Der verwendete Modellname muss aus klarer Konfiguration stammen:

- `.env`
- `.env.example`
- dokumentierte Default-Konstante
- CLI-Argument
- Environment Variable

Keine versteckten Hardcodings.

---

# Arbeitsreihenfolge

## 1. Aktuelle Modellkonfiguration analysieren

Lies:

```text
.env.example
README.md
docs/runtime/research-happy-path.md
docs/runtime/local-runtime-smoke.md
scripts/runtime_smoke.py
scripts/research_happy_path.py
config/
Makefile
```

Dokumentiere:

- welche Env-Variable für das Ollama-Modell verwendet wird
- welcher Default gesetzt ist
- welches Modell in `.env.example` steht
- welches Modell in Docs genannt wird
- welches Modell im Runtime-Smoke geprüft wird
- welches Modell im Happy-Path verwendet wird
- welche Ollama-API-Endpunkte genutzt werden

---

## 2. Lokalen Ollama-Zustand reproduzieren

Führe aus:

```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool || true
ollama list || true
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-happy-path
```

Dokumentiere:

- verfügbare Modellnamen exakt
- erwarteter Modellname
- tatsächlicher 404-Name
- ob Embed-Model und Generate-Model verwechselt werden
- ob `nomic-embed-text` als Summary-Modell falsch genutzt wird

Wichtig: Prüfe, ob `nomic-embed-text` nur ein Embedding-Modell ist und nicht für Textgenerierung/Summary genutzt werden sollte.

---

## 3. Modellrollen trennen

Falls noch nicht sauber getrennt, führe klare Rollen ein:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=<lokales Textgenerierungsmodell>
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
```

oder verwende bestehende Namen, falls bereits vorhanden.

Wichtig:

- Embedding-Modell und Chat-/Summary-Modell nicht vermischen.
- `.env.example`, Docs und Skripte müssen dieselben Variablen verwenden.
- Defaults müssen realistisch sein und lokal prüfbar bleiben.

---

## 4. Modellauflösung verbessern

Implementiere eine kleine Funktion, z. B.:

```python
def resolve_ollama_model(
    available_models: list[str],
    requested_model: str,
    allow_fallback: bool = False,
) -> ModelResolution:
    ...
```

Sie soll unterscheiden:

- `OK`
- `MODEL_MISSING`
- `NO_MODELS_AVAILABLE`
- `FALLBACK_SELECTED`
- `CONFIG_ERROR`

Falls Fallback erlaubt ist:

- nur auf lokal vorhandenes Textgenerierungsmodell
- nicht auf Embedding-Modell
- Warnung ausgeben
- im Report dokumentieren

Fallback standardmäßig deaktiviert oder explizit per Env/CLI:

```bash
ALLOW_OLLAMA_MODEL_FALLBACK=true
```

---

## 5. Happy-Path anpassen

`scripts/research_happy_path.py` soll:

1. Ollama-Modelle laden
2. Chat-/Summary-Modell auflösen
3. bei fehlendem Modell klar abbrechen oder graceful degrade, je nach Modus
4. in Standardmodus weiterhin Report mit Warnung erzeugen dürfen
5. in Strict-Modus bei fehlendem Summary-Modell fehlschlagen
6. im Report dokumentieren:
   - gewünschtes Modell
   - verwendetes Modell
   - ob Fallback/Degradation aktiv war

---

## 6. Runtime-Smoke anpassen

`scripts/runtime_smoke.py` soll getrennt prüfen:

- Ollama API erreichbar
- Embedding-Modell vorhanden
- Chat-/Summary-Modell vorhanden

Beispielausgabe:

```text
Ollama API: ✅ erreichbar
Ollama embed model: ✅ nomic-embed-text:latest
Ollama chat model: ❌ qwen3.5-... fehlt
Hint:
  ollama list
  ollama pull <model>
  or set OLLAMA_CHAT_MODEL=<existing-model>
```

---

## 7. Tests ergänzen

Gemockte Tests für:

- Modell vorhanden → OK
- Modell fehlt → klare Fehlermeldung
- keine Modelle verfügbar
- Embedding-Modell wird nicht als Chat-Modell akzeptiert
- Fallback deaktiviert → kein Fallback
- Fallback aktiviert → lokales Chat-Modell gewählt
- Strict-Modus schlägt bei fehlendem Chat-Modell fehl
- Standardmodus erzeugt Report mit Warnung
- `.env.example`/Konfigurationsnamen werden dokumentiert oder geprüft, falls sinnvoll

Keine echten Ollama-Netzwerkaufrufe in Unit-Tests.

---

# Dokumentation

Aktualisiere:

```text
.env.example
docs/runtime/local-runtime-smoke.md
docs/runtime/research-happy-path.md
README.md
```

Optional neu:

```text
docs/runtime/ollama-model-configuration.md
```

Pflichtinhalt:

```markdown
# Ollama Model Configuration

## Rollen

| Variable | Zweck | Beispiel |
|---|---|---|
| OLLAMA_BASE_URL | Ollama API | http://localhost:11434 |
| OLLAMA_CHAT_MODEL | Textgenerierung/Summary | <dein lokales Chatmodell> |
| OLLAMA_EMBED_MODEL | Embeddings | nomic-embed-text:latest |

## Modelle anzeigen

```bash
ollama list
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

## Fehlendes Modell beheben

```bash
ollama pull <model>
```

## Happy-Path prüfen

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-happy-path
```

## Strict Mode

```bash
make research-happy-path-strict
```

## Kein Cloud-Fallback
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# Runtime
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-happy-path

# wenn lokales Chatmodell korrekt gesetzt ist
make research-happy-path-strict

# neue Tests
python3 -m pytest tests/ -q -k "ollama or runtime_smoke or research_happy_path"
```

Wenn kein passendes Chatmodell lokal vorhanden ist:

- Standardmodus darf Report mit Warnung erzeugen
- Strict-Modus muss klar fehlschlagen
- Doku muss exakten Fix-Befehl nennen

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Ursache des Model-Name-Mismatch dokumentiert ist
- Embedding- und Chat-/Summary-Modell getrennt sind
- `.env.example` konsistente Variablen enthält
- Runtime-Smoke prüft beide Modellrollen
- Happy-Path nutzt das Chat-/Summary-Modell korrekt
- fehlendes Modell führt zu klarer Diagnose
- Strict-Modus schlägt bei fehlendem Chatmodell korrekt fehl
- Standardmodus degradiert kontrolliert oder nutzt korrektes Modell
- Unit-Tests vorhanden sind
- Doku aktualisiert ist
- bestehende Gates bleiben grün
- keine Cloud-Fallbacks eingeführt wurden
- keine neuen Research-Features gebaut wurden
- GitHub-Kommentar mit Ergebnis geschrieben wurde

Minimal akzeptabel:

- Model-Mismatch wird klar diagnostiziert
- `.env.example` und Doku konsistent
- Standardmodus bleibt stabil
- Strict-Modus prüft korrekt

Gut:

- Happy-Path erzeugt echte lokale Ollama-Summary
- Embedding/Chat-Rollen sauber getrennt
- Tests decken Fallback/Strict ab

Sehr gut:

- Nutzer kann mit `ollama list` und einem dokumentierten Env-Wert sofort den Happy-Path reparieren
- Report dokumentiert gewünschtes/verwendetes Modell und Degradationsstatus

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Ollama Model-Konfiguration Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Model-Name-Mismatch reproduziert | |
| Ursache dokumentiert | |
| Embed-/Chat-Modell getrennt | |
| `.env.example` aktualisiert | |
| Runtime-Smoke angepasst | |
| Happy-Path angepasst | |
| Strict-Modus korrekt | |
| Standardmodus stabil | |
| Unit-Tests ergänzt | |
| Doku aktualisiert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine Cloud-Fallbacks | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Ollama-Modellstatus

| Rolle | Erwartet | Gefunden | Ergebnis |
|---|---|---|---|
| Embed | | | |
| Chat/Summary | | | |

## Live-Ergebnis

| Befehl | Ergebnis |
|---|---|
| runtime-smoke | |
| research-happy-path | |
| research-happy-path-strict | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Research Report Quality Evaluation: Quellen, Halluzinationen, Evidenz`
2. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
3. `Playwright-CI-Strategie definieren`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
