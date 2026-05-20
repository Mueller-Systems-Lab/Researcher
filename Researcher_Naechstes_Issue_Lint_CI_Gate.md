# Researcher — Nächstes Reparatur-Issue: Lint-/CI-Gate fokussiert entblocken

## Rolle

Du bist ein Senior Python Maintainability Engineer und CI-Stabilitäts-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis des abgeschlossenen Repair-Laufs zu Issue #50.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, das nächste klar abgegrenzte CI-/Qualitätsproblem zu reduzieren: `ruff` meldet nach dem Repair noch ca. 950 Fehler, überwiegend `E501` Line-Length, besonders im `gpt_researcher/`-Submodul. Gleichzeitig existiert noch ein mypy-Fehler im Submodulbereich `gpt_researcher/ports`.

---

# Ausgangslage

Der vorherige Repair-Lauf hat erreicht:

- Dependencies installierbar
- `make test` grün: 207 passed, 17 skipped
- `make security` ausführbar: Bandit 1.9.4, Findings dokumentiert
- E2E-Pipeline stabil: 3/3 E2E grün
- Coverage: 78.99% bei Required 78.0%
- mypy Duplicate-conftest für `tests/playwright` und `tests/benchmarks` behoben
- SQLite-Benchmarks stabil: 9/9
- ruff reduziert: 1345 → 950 Fehler
- GitHub-Kommentar zu Issue #50 geschrieben

Bewusst offen geblieben:

1. `ruff`: ca. 950 Errors, überwiegend `E501` Line-Length, viele davon im `gpt_researcher/`-Submodul.
2. `mypy`: ein verbleibender Fehler im `gpt_researcher/ports`-Submodulbereich.
3. `make test` inkludiert Benchmarks und dauert dadurch lange.
4. Bandit-Findings sind dokumentiert, aber noch nicht triagiert.

---

# Oberstes Ziel dieses Issues

Reduziere das `ruff`-Rauschen so, dass die CI-Qualität steigt, ohne das `gpt_researcher/`-Submodul großflächig zu verändern.

Priorität:

1. Projekt-eigene Dateien reparieren.
2. Submodul-Dateien nicht massenhaft formatieren.
3. Falls Submodul-Fehler CI blockieren, `ruff`-Konfiguration sauber trennen statt fremden Code umzuschreiben.
4. Keine produktive Logik verändern.
5. Keine neuen Features.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- den GPT-Researcher-Submodulcode großflächig refactoren
- `ruff --unsafe-fixes` blind auf das gesamte Repository anwenden
- Coverage-Schwellen senken
- Tests löschen
- Bandit-Findings pauschal ignorieren
- Architektur ändern
- Dependencies upgraden, außer es ist für ruff-Konfiguration zwingend nötig

---

# Arbeitsreihenfolge

## 1. Ist-Zustand reproduzieren

Führe aus:

```bash
python3 -m ruff check . --line-length=88
python3 -m ruff check . --statistics --line-length=88
python3 -m ruff check . --output-format=concise --line-length=88 > /tmp/ruff-current.txt
```

Dokumentiere:

- Gesamtzahl Fehler
- Fehlerarten nach Häufigkeit
- wie viele Fehler in projekt-eigenen Dateien liegen
- wie viele Fehler im `gpt_researcher/`-Submodul liegen
- ob `E501` dominiert
- ob echte Fehlerklassen neben Style-Rauschen existieren

## 2. Projekt-eigene Dateien identifizieren

Projekt-eigene Bereiche sind typischerweise:

- `config/`
- `crawlers/`
- `darknet_search/`
- `search/`
- `dashboard/`
- `vectordb/`
- `mcp_tools/`
- `onion_discovery/`
- `tests/`
- `scripts/`
- eigene Root-Dateien

Submodul-/Vendor-Bereich:

- `gpt_researcher/`

Behandle `gpt_researcher/` zunächst als Vendor/Submodule-Bereich, auch wenn dort lokale Adapter liegen.

## 3. Kleine sichere ruff-Fixes durchführen

Erlaubt:

```bash
python3 -m ruff check config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery tests scripts --fix
```

Nur wenn diese Pfade existieren.

Danach manuell prüfen:

```bash
git diff
```

Nicht erlaubt:

```bash
python3 -m ruff check . --fix --unsafe-fixes
```

außer nach ausdrücklicher Begründung und nur auf eingegrenzten Projektpfaden.

## 4. E501 gezielt behandeln

Für projekt-eigene Dateien:

- lange Strings sinnvoll umbrechen
- lange Assertions lesbar umbrechen
- lange Testdaten ggf. mit Variablen strukturieren
- URLs/Onion-Beispiele nicht künstlich unlesbar machen
- keine semantischen Änderungen

Für `gpt_researcher/`:

Entscheide zwischen:

### Option A — Submodul aus ruff ausschließen

Wenn fast alle verbleibenden `E501` im Submodul liegen:

```toml
[tool.ruff]
exclude = [
  "gpt_researcher/**",
]
```

oder projektspezifisch vorsichtiger:

```toml
[tool.ruff.lint.per-file-ignores]
"gpt_researcher/**/*.py" = ["E501"]
```

### Option B — Nur lokale Adapter im Submodul behandeln

Nur wenn klar ist, dass einzelne Dateien tatsächlich projekt-eigener Code sind und nicht durch Submodul-Updates überschrieben werden.

Bevorzugt ist Option A oder per-file-ignore, wenn `gpt_researcher/` als Submodul/Vendor-Code gilt.

## 5. mypy-Submodulfehler nicht in diesem Issue reparieren

Falls `python3 -m mypy . --ignore-missing-imports` weiterhin nur im `gpt_researcher/ports`-Bereich fehlschlägt:

- nicht in diesem Issue lösen
- dokumentieren
- Folge-Issue vorschlagen: `mypy vendor/submodule boundary cleanup`

Nur wenn eine kleine Konfigurationsänderung ohne Nebenwirkung möglich ist, darf sie vorgeschlagen, aber nicht ungeprüft umgesetzt werden.

## 6. Validierung

Nach jeder relevanten Änderung ausführen:

```bash
python3 -m ruff check . --line-length=88
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q
python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q
```

Optional, falls Zeit:

```bash
make security
python3 -m mypy . --ignore-missing-imports
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- ruff-Fehler deutlich reduziert sind
- projekt-eigene Dateien möglichst ruff-clean sind
- `gpt_researcher/` nicht blind massenformatiert wurde
- Submodul-/Vendor-Grenze dokumentiert ist
- Tests weiterhin grün sind
- Coverage weiterhin >=78% bleibt
- keine produktive Logik geändert wurde
- README oder docs aktualisiert wurden, falls ruff-Konfiguration geändert wurde
- GitHub-Kommentar mit Vorher/Nachher-Zahlen geschrieben wurde

Minimal akzeptabel:

- ruff sinkt von ca. 950 auf unter 300 Fehler

Gut:

- ruff sinkt auf unter 100 Fehler

Sehr gut:

- `ruff check .` läuft grün oder verbleibende Fehler sind bewusst per Vendor-Konfiguration ausgeschlossen

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Lint-/CI-Gate Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| ruff Ausgangswert dokumentiert | |
| ruff Endwert dokumentiert | |
| Projekt-eigene Dateien bereinigt | |
| Submodul nicht blind massenformatiert | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| Keine produktive Logik geändert | |
| Vendor-/Submodul-Grenze dokumentiert | |
| GitHub-Kommentar geschrieben | |

## Ruff Vorher/Nachher

| Bereich | Vorher | Nachher |
|---|---:|---:|
| Gesamt | | |
| Projekt-eigene Dateien | | |
| gpt_researcher/Submodul | | |

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

1. `Bandit-Findings triagieren und Policy definieren`
2. `mypy vendor/submodule boundary cleanup`
3. `make test in schnelle und langsame Testprofile trennen`
4. `Playwright-CI-Strategie definieren`
