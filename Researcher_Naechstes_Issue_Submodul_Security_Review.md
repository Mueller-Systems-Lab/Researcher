# Researcher — Nächstes Issue: Submodul-Security-Review für `gpt_researcher/`

## Rolle

Du bist ein Senior Python Security Engineer mit Fokus auf Vendor-/Fork-Code, sichere Netzwerkaufrufe und risikoarme Upstream-kompatible Patches.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Issues:

- #50: Walking-Skeleton/Repair
- #51: Lint-/CI-Gate, ruff 950 → 0
- #52: Bandit-/Security-Triage, 43 Findings triagiert

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die in #52 identifizierten Security-Findings im `gpt_researcher/`-Submodul/Fork gezielt zu prüfen und — nur wo sicher möglich — minimal zu beheben oder als Upstream-/Fork-Folgearbeit sauber zu dokumentieren.

---

# Ausgangslage

Issue #52 hat ergeben:

- 43 Bandit-Findings insgesamt
- 7 High, 18 Medium, 18 Low
- 0 High-Findings in projekt-eigenem produktivem Code
- 32 Findings im `gpt_researcher/`-Submodul/Vendor-Bereich
- Projekt-eigene Findings waren Low-Severity, Test-only oder akzeptiert
- `docs/security/bandit-triage.md` existiert

Offene Submodul-Schwerpunkte:

1. MD5 → SHA-256-Migration an ca. 6 Stellen
2. SSL-Verify-Prüfung an ca. 1 Stelle
3. Requests-Timeouts an ca. 8 Stellen
4. Klärung: Patch lokal im Fork oder Upstream-PR vorbereiten?

---

# Oberstes Ziel dieses Issues

Erstelle einen risikoarmen Submodul-Security-Review mit minimalen, nachvollziehbaren Änderungen.

Priorität:

1. Keine Massenänderungen im Submodul.
2. Nur echte, kleine Security-Hardening-Fixes.
3. Upstream-Kompatibilität erhalten.
4. Tests und Coverage stabil halten.
5. Alle Änderungen so dokumentieren, dass sie später als Upstream-PR oder Fork-Patch nachvollziehbar sind.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- Architektur ändern
- den gesamten `gpt_researcher/`-Code formatieren
- ruff-Regeln auf das ganze Submodul erzwingen
- großflächige Refactorings durchführen
- externe API-Provider aktivieren
- Cloud-/Remote-Funktionalität ändern
- Tests löschen
- Security-Findings pauschal mit `# nosec` verstecken
- ohne Begründung `verify=False` bestehen lassen
- ohne Datenflussprüfung Hashing ändern, wenn dadurch Persistenz/Cache-Kompatibilität bricht

---

# Wichtige Arbeitsregel: Vendor-Schutz

Behandle `gpt_researcher/` als Vendor-/Fork-Code.

Vor jeder Änderung im Submodul muss dokumentiert werden:

- warum die Änderung nötig ist
- ob sie upstream-kompatibel ist
- ob sie persistente IDs, Cache-Keys oder Dateinamen verändert
- ob Migrationsfolgen entstehen
- welche Tests die Änderung absichern

Wenn eine Änderung riskant ist:

- nicht direkt ändern
- Folge-Issue oder Upstream-PR-Plan dokumentieren

---

# Arbeitsreihenfolge

## 1. Ist-Zustand reproduzieren

Führe aus:

```bash
python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   -f json -o bandit-gpt-researcher-before.json

python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   -f txt -o bandit-gpt-researcher-before.txt
```

Zusätzlich prüfen:

```bash
grep -R "hashlib.md5\|verify=False\|requests\.get\|requests\.post\|requests\.request" -n gpt_researcher || true
```

Dokumentiere:

- genaue Dateien
- genaue Zeilen
- Bandit-Test-ID
- Severity
- Confidence
- produktiver Pfad oder Test/Vendor-Hilfscode
- mögliche Seiteneffekte bei Änderung

---

## 2. MD5-Findings prüfen

Für jede MD5-Stelle prüfen:

### Fragen

- Wird der Hash für Security verwendet?
- Wird der Hash nur für IDs, Cache-Keys, Dateinamen oder Deduplizierung genutzt?
- Gibt es persistente Daten, die durch Hash-Änderung inkompatibel würden?
- Gibt es Tests, die den exakten MD5-Wert erwarten?
- Ist SHA-256 ohne Migration möglich?

### Entscheidungsmöglichkeiten

#### A — Sicher migrieren

Wenn keine Persistenz-/Kompatibilitätsprobleme bestehen:

```python
hashlib.sha256(value.encode("utf-8")).hexdigest()
```

#### B — Nicht-sicherheitsrelevant markieren

Wenn der Hash bewusst nur für nicht-sicherheitsrelevante IDs verwendet wird und Kompatibilität wichtig ist:

```python
hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()
```

Zusätzlich Kommentar ergänzen:

```python
# MD5 is used only for non-security cache key compatibility.
```

#### C — Nicht ändern, Folge-Issue

Wenn Persistenz-/Cache-Kompatibilität unklar ist:

- keine Codeänderung
- in `docs/security/submodule-security-review.md` dokumentieren
- Migrationsplan als Folge-Issue vorschlagen

---

## 3. Requests ohne Timeout prüfen

Für jede `requests.*`-Stelle im Submodul:

### Fragen

- Ist der Call produktiv erreichbar?
- Ist die URL extern, lokal oder test-only?
- Gibt es bereits eine Timeout-Konfiguration?
- Gibt es Retry-/Session-Handling?
- Kann ein Timeout ohne API-Bruch ergänzt werden?

### Bevorzugter Fix

Wenn möglich:

```python
DEFAULT_REQUEST_TIMEOUT = (5, 30)
requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
```

Oder wenn vorhandene Config existiert:

```python
requests.get(url, timeout=config.request_timeout)
```

Keine neuen globalen Defaults erfinden, wenn bereits Projekt-/Submodul-Konfiguration existiert.

### Test

Mindestens ein Test oder Mock sollte prüfen, dass `timeout` weitergegeben wird, falls der Codepfad lokal testbar ist.

---

## 4. SSL-Verify-Finding prüfen

Für `verify=False`:

### Fragen

- Ist der Code produktiv erreichbar?
- Betrifft es externe PDF-/Webquellen?
- Ist `verify=False` historisch nötig?
- Gibt es eine Konfiguration?
- Kann Default sicher auf `verify=True` gesetzt werden?
- Wird lokaler Test-/Onion-/Sonderfall dadurch gebrochen?

### Bevorzugter Fix

Sicherer Default:

```python
verify=True
```

Oder Parameter entfernen, weil Requests standardmäßig TLS-Zertifikate prüft.

Wenn eine Ausnahme zwingend nötig ist:

- Config-Flag mit sicherem Default
- Warnung im Code
- Dokumentation in Security-Policy
- möglichst enger Scope

Nicht erlaubt:

```python
requests.get(url, verify=False)
```

ohne Begründung.

---

## 5. Dokumentation erstellen

Erstelle oder aktualisiere:

```text
docs/security/submodule-security-review.md
```

Pflichtinhalt:

```markdown
# Submodule Security Review — gpt_researcher

## Stand

## Scope

## Ausgeführte Befehle

## Findings Summary

| Kategorie | Anzahl | Entscheidung |
|---|---:|---|

## MD5/SHA Findings

| Datei | Zeile | Entscheidung | Begründung | Risiko |
|---|---:|---|---|---|

## Requests Timeout Findings

| Datei | Zeile | Entscheidung | Begründung | Risiko |
|---|---:|---|---|---|

## SSL Verify Findings

| Datei | Zeile | Entscheidung | Begründung | Risiko |
|---|---:|---|---|---|

## Geänderte Stellen

## Nicht geänderte Stellen

## Upstream-/Fork-Empfehlung

## Folge-Issues
```

---

## 6. Validierung

Nach Änderungen ausführen:

```bash
# Submodul-Bandit erneut
python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   -f json -o bandit-gpt-researcher-after.json

python3 -m bandit -r gpt_researcher   --skip B101,B311,B404,B603   -f txt -o bandit-gpt-researcher-after.txt

# Gesamt-Security
make security

# Lint muss grün bleiben
python3 -m ruff check . --line-length=88

# Tests
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py -q

# Coverage
python3 -m pytest tests/ --ignore=tests/benchmarks --ignore=tests/e2e   --ignore=tests/playwright/test_dashboard_accessibility.py   --ignore=tests/playwright/test_dashboard_visual_regression.py   --cov --cov-report=term -q

# E2E quick repeat
python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q
```

Optional:

```bash
python3 -m mypy . --ignore-missing-imports
```

Der bekannte `gpt_researcher/ports`-mypy-Fehler ist nur zu dokumentieren, nicht in diesem Issue zu lösen.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- alle Submodul-Bandit-Findings aus #52 erneut lokalisiert wurden
- MD5/SHA-Findings einzeln bewertet wurden
- Requests-Timeout-Findings einzeln bewertet wurden
- SSL-Verify-Finding einzeln bewertet wurde
- sichere Low-Risk-Fixes umgesetzt wurden
- riskante Änderungen nicht blind umgesetzt wurden
- `docs/security/submodule-security-review.md` existiert
- ruff weiterhin grün bleibt
- Tests weiterhin grün bleiben
- Coverage weiterhin >=78% bleibt
- `make security` weiterhin ausführbar bleibt
- GitHub-Kommentar mit Vorher/Nachher-Zahlen geschrieben wurde

Minimal akzeptabel:

- vollständige Review-Dokumentation
- keine Regression
- klare Upstream-/Fork-Empfehlung

Gut:

- Requests-Timeouts sicher ergänzt
- MD5 entweder auf SHA-256 migriert oder mit `usedforsecurity=False` begründet
- SSL-Verify sicherer Default oder dokumentierte Ausnahme

Sehr gut:

- Submodul-Findings deutlich reduziert
- Änderung ist als Upstream-PR geeignet

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Submodul-Security-Review Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Submodul-Bandit-Ausgangswert dokumentiert | |
| Submodul-Bandit-Endwert dokumentiert | |
| MD5/SHA-Findings geprüft | |
| Requests-Timeout-Findings geprüft | |
| SSL-Verify-Finding geprüft | |
| Low-Risk-Fixes umgesetzt | |
| Riskante Änderungen dokumentiert statt blind umgesetzt | |
| Security-Review-Doku erstellt | |
| Tests weiterhin grün | |
| Coverage weiterhin >=78% | |
| ruff weiterhin grün | |
| make security ausführbar | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Submodul-Bandit Vorher/Nachher

| Severity | Vorher | Nachher | Behoben | Akzeptiert | Follow-up |
|---|---:|---:|---:|---:|---:|
| High | | | | | |
| Medium | | | | | |
| Low | | | | | |
| Gesamt | | | | | |

## Entscheidungen nach Kategorie

| Kategorie | Entscheidung | Anzahl |
|---|---|---:|
| MD5/SHA | | |
| Requests Timeout | | |
| SSL Verify | | |
| Sonstige | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Behobene Risiken

## Akzeptierte Risiken mit Begründung

## Upstream-/Fork-Empfehlung

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `mypy vendor/submodule boundary cleanup`
2. `make test in schnelle und langsame Testprofile trennen`
3. `Playwright-CI-Strategie definieren`
4. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
