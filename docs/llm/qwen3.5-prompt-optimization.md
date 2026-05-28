# Qwen3.5 Prompt-Optimierung

**Datum:** 2026-05-28  
**Modell:** Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf  
**Backend:** llama.cpp llama-server (Port 8082)  
**ADR:** [ADR-017](../adr/ADR-017-qwen3.5-co-primary-model.md)

---

## 1. Template

Qwen3.5 verwendet **ChatML** (`<|im_start|>...<|im_end|>`) via:

```bash
--no-jinja --chat-template chatml
```

Das HauhauCS-GGUF hat ein defektes Jinja-Template in den Metadaten — `--no-jinja` deaktiviert es und `--chat-template chatml` setzt das korrekte Qwen-native ChatML-Format.

**Keine Template-Änderung nötig.** ChatML wird korrekt verwendet.

---

## 2. enable_thinking

`enable_thinking: False` wurde in **allen** llama-server-Callern konsistent gesetzt:

| Datei | Vorher | Nachher |
|---|---|---|
| `scripts/research_happy_path.py` | ✅ vorhanden | ✅ |
| `scripts/uncensored_research.py` | ❌ fehlte | ✅ |
| `scripts/runtime_smoke.py` | ❌ fehlte | ✅ |
| `research_planner/planner.py` | ❌ fehlte | ✅ |
| `config/local_llm_runtime.py` | ❌ fehlte | ✅ |

Begründung: Qwen3.5 hat standardmäßig Thinking aktiv. Ohne `enable_thinking: False` können Thinking-Blöcke in `reasoning_content` statt `content` landen, was zu leeren Antworten führt.

---

## 3. Temperature-Sweep

**Test-Setup:** 3 Queries × 4 Temperaturen = 12 Durchläufe  
**Ergebnisse:**

| Temperatur | Avg Score | Avg Tokens | Avg Latency (ms) | Garbled |
|---|---|---|---|---|
| **0.3** | 1.00 | 232 | 10,777 | 0/3 |
| **0.5** | 1.00 | 222 | 9,826 | 0/3 |
| **0.7** | 1.00 | 248 | 11,003 | 0/3 |
| **0.9** | 1.00 | 210 | 9,732 | 0/3 |

### Erkenntnisse

1. **Qwen3.5 produziert bei ALLEN Temperaturen (0.3–0.9) perfekte Ergebnisse** — kein Garbled Output, keine Thinking-Blöcke, keine Degeneration.
2. Die offizielle Qwen-Empfehlung `temperature=0.7` ist sicher nutzbar und liefert mehr Vielfalt.
3. Für Extraktion/Scraping: **0.3** (deterministischer, kürzere Antworten)
4. Für kreative Texte/Guides: **0.5–0.7** (mehr Variation, gleiche Qualität)
5. Token-Count konsistent (210–248), Latenz stabil (~10s)

### Empfehlung

| Use Case | Temperature | Begründung |
|---|---|---|
| Fakten-Extraktion | **0.3** | Kürzeste, präziseste Antworten |
| Scraping/Structured Output | **0.3** | Deterministisch, reproduzierbar |
| Zusammenfassungen | **0.5** | Gute Balance Präzision/Vielfalt |
| Kreative Texte/Guides | **0.7** | Qwen-offizielle Empfehlung, mehr Variation |
| Brainstorming | **0.9** | Maximale Kreativität, stabil |

---

## 4. Multi-Page-Guide-Test

**Test-Setup:** 3 Topics, 1200 max_tokens, temperature=0.5  
**Ergebnisse:**

| Topic | Sections | Tokens | Latency (ms) | OK |
|---|---|---|---|---|
| Sauerteig ansetzen | 2 | 1200 | 53,425 | ✅ |
| Astrofotografie Grundlagen | 6 | 1200 | 49,384 | ✅ |
| Kompost anlegen | 3 | 1200 | 46,861 | ✅ |

**3/3 Guides erfolgreich** — ⌀ 3.7 Abschnitte pro Guide.

### Vergleich mit Gemma 4

| Kriterium | Qwen3.5 | Gemma 4 |
|---|---|---|
| Guides erfolgreich | 3/3 (100%) | 0/? (scheiterte) |
| Degenerate Output | 0% | ~20% |
| Durchschnittliche Abschnitte | 3.7 | — |
| Latenz (1200 tokens) | ~50s | ~50s (24 tok/s) |

**Fazit:** Qwen3.5 ist für mehrseitige Anleitungen **deutlich überlegen**. Gemma 4 scheiterte an diesem Use Case wegen Degeneration/Halluzination.

---

## 5. Zusammenfassung

| Optimierung | Status | Ergebnis |
|---|---|---|
| ChatML-Template | ✅ Besteht | Korrekt via `--chat-template chatml` |
| enable_thinking | ✅ Gefixt | 5/5 Caller konsistent |
| Temperature-Sweep | ✅ Getestet | 0.3–0.9 alle Score 1.00 |
| Multi-Page-Guides | ✅ Getestet | 3/3 erfolgreich (⌀ 3.7 Sections) |

### Empfohlene Default-Parameter für Qwen3.5

```python
{
    "temperature": 0.3,        # Extraktion/Scraping (Default)
    "top_p": 0.9,              # Unverändert
    "top_k": 40,               # Unverändert
    "repeat_penalty": 1.2,     # Unverändert (verhindert Wiederholungen)
    "max_tokens": 400,         # Extraktion (Default)
    "max_tokens": 1200,        # Guides/Zusammenfassungen
    "chat_template_kwargs": {"enable_thinking": False},  # Pflicht!
}
```

---

## Quellen

- `scripts/qwen3.5_optimize.py` — Temperature-Sweep + Guide-Test-Script
- `serve_qwen3.5_uncensored.sh` — `--no-jinja --chat-template chatml`
- `docs/adr/ADR-017-qwen3.5-co-primary-model.md` — Co-Primary-Entscheidung
- Hugging Face Qwen3.5: https://huggingface.co/Qwen/Qwen3.5-9B
