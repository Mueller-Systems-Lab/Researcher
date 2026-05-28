# UX-Heuristik-Prüfung — GPU-Dashboard

**Datum:** 2026-05-28  
**Scope:** `dashboard/static/index.html`, `dashboard/server.py`, `dashboard/gpu_monitor.py`  
**Basis:** Nielsen-Norman 10 UX-Heuristiken  

---

## Ergebnisübersicht

| Heuristik | Status | Anmerkung |
|---|---|---|
| 1. Visibility of system status | ✅ | Status-Dot, Connection-Text, Live-Timestamp |
| 2. Match system & real world | ✅ | %, °C, MiB — alle Einheiten korrekt |
| 3. User control & freedom | 🟡 | N/A (Read-only Dashboard) |
| 4. Consistency & standards | ✅ | Einheitliche Farbcodierung + Legende |
| 5. Error prevention | ✅ | Read-only, keine Benutzereingaben |
| 6. Recognition rather than recall | ✅ | Metriken direkt sichtbar, kein Menü |
| 7. Flexibility & efficiency | ✅ | Auto-Update via SSE, kein Reload nötig |
| 8. Aesthetic & minimalist design | ✅ | 4 Karten, keine Überfrachtung |
| 9. Help users recognize errors | ✅ | Error-State mit Klartext + Aktion |
| 10. Help & documentation | 🟡 | Nischentool, selbsterklärend |

---

## Detailprüfung

### 1. Visibility of system status (Systemstatus sichtbar)

| State | Implementierung | Status |
|---|---|---|
| **Loading** | Skeleton-Shimmer-Animation + "GPU-Daten werden geladen..." | ✅ |
| **Connected** | Grüner Dot + "✅ Verbunden" | ✅ |
| **Disconnected** | Roter Dot + "⚠ Verbindung unterbrochen" + Reconnect-Zähler | ✅ |
| **Reconnecting** | Gelber Dot + "🔄 Erneute Verbindung (Versuch N)..." | ✅ |
| **Error** | Rote Fehlermeldung im Alert-Banner | ✅ |
| **Degraded** | Warn-/Kritisch-Markierung bei VRAM > 70%/90% | ✅ |
| **Timestamp** | "Letzte Aktualisierung: HH:MM:SS" | ✅ |
| **Legende** | Status-Dot-Erklärung unterhalb des Dashboards | ✅ |

### 2. Match between system and real world

- GPU-Auslastung in % ✅
- Temperatur in °C ✅
- VRAM in MiB ✅
- Warnschwellen (70%/90%) entsprechen üblichen GPU-Grenzwerten ✅

### 3. User control and freedom

Nicht zutreffend — Dashboard ist rein read-only, keine Benutzerinteraktion.

### 4. Consistency and standards

- Einheitliche Card-Struktur (Label + Value + Bar) über alle Metriken ✅
- Farbcodierung: Grün=OK, Gelb=Warnung, Rot=Kritisch, Grau=Fehler ✅
- Legende dokumentiert die Farben ✅
- Dark Theme konsistent (GitHub-Stil) ✅

### 5. Error prevention

Keine Benutzereingaben → kein Fehlerrisiko durch Nutzer.

### 6. Recognition rather than recall

- Alle 4 Hauptmetriken sofort sichtbar ✅
- Keine verschachtelten Menüs oder Tabs ✅
- GPU-Prozessliste direkt unter Metriken ✅

### 7. Flexibility and efficiency of use

- Live-Update via SSE (kein manuelles Reload) ✅
- Automatische Wiederverbindung bei Verbindungsabbruch ✅
- Keine Konfiguration nötig ✅

### 8. Aesthetic and minimalist design

- 4 Karten, keine Überfrachtung ✅
- Klare Typografie-Hierarchie (Label → Value → Unit) ✅
- Fortschrittsbalken als visuelle Ergänzung ✅

### 9. Help users recognize, diagnose, and recover from errors

| Fehlerszenario | Meldung | Recovery |
|---|---|---|
| Kein nvidia-smi | "nvidia-smi nicht gefunden — keine NVIDIA-GPU?" | — |
| SSE-Verbindungsabbruch | "⚠ Verbindung zum GPU-Monitor unterbrochen. Versuche erneut zu verbinden..." | Automatischer Reconnect mit Backoff |
| nvidia-smi Timeout | "nvidia-smi timeout (10s)" | Nächster Update-Zyklus |
| GPU nicht verfügbar | "Keine GPU-Daten" | Nächster Update-Zyklus |
| VRAM > 90% | Rote Schrift + Puls-Animation | Automatische Entwarnung |

### 10. Help and documentation

Dashboard ist selbsterklärend. Keine separate Hilfeseite nötig.

---

## UX-Probleme (vor dieser Prüfung)

Die im Issue #44 beschriebenen Probleme wurden bereits adressiert:

| Beschriebenes Problem | Status | Gelöst in |
|---|---|---|
| Loading State fehlt (`--` als Platzhalter) | ✅ Skeleton-Shimmer vorhanden | Ursprüngliche Implementierung |
| Empty State fehlt (keine GPU) | ✅ "nvidia-smi nicht gefunden — keine NVIDIA-GPU?" | `gpu_monitor.py` Zeile 106 |
| Error Recovery unsichtbar | ✅ Reconnect-Counter + sichtbare Meldung | `index.html` Zeilen 219-239 |
| Status-Dot-Legende fehlt | ✅ Legende unter Dashboard | Diese Prüfung |

---

## Empfehlungen (optional)

1. **GPU-Last-Farbverlauf**: Aktuelle einfarbige Balken könnten durch Verlaufsfarben ersetzt werden
2. **Letzte Aktualisierung alsrelative Zeit**: "vor 2s" statt absolutem Timestamp
3. **GPU-Temperatur-Farbverlauf**: Blau (kalt) → Gelb (warm) → Rot (heiß) für Temperatur-Balken
4. **Process-Sortierung**: GPU-Prozesse nach VRAM sortieren (absteigend)

---

## Quellen

- Nielsen Norman Group: [10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
- Dashboard-Code: `dashboard/static/index.html`, `dashboard/server.py`, `dashboard/gpu_monitor.py`
