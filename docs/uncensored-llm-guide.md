# Unzensierte LLM-Integration — Guide

## Zusammenfassung

Unser Research-System nutzt zwei unzensierte Modelle mit Thinking/Reasoning-Modus.
Beide schreiben die Antwort in ein separates Feld, nicht in `message.content`.

| Modell | Server | Endpoint | Antwort-Feld | Deaktivierbar? |
|--------|--------|----------|-------------|----------------|
| Qwen3.5 Uncensored | Ollama :11434 | `/api/chat` | `message.thinking` | ✅ `"think": false` |
| Gemma4 Obliterated | llama.cpp :8085 | `/v1/chat/completions` | `message.reasoning_content` | ✅ `--reasoning off` |

## 1. Ollama Thinking-Modus

### Problem
Der Parameter `think` steuert Thinking: `/api/chat` mit `"think": false` deaktiviert es.
Es gibt KEINEN Modelfile-PARAMETER zum globalen Deaktivieren.

### Solution A: Clientseitig deaktivieren (via Wrapper)
```python
payload = {
    "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
    "messages": [{"role": "user", "content": prompt}],
    "stream": False,
    "think": False,  # <-- Thinking deaktivieren
}
```

### Solution B: Fallback-Extraktion (aktueller Wrapper)
```python
msg = data.get("message", {})
answer = msg.get("content") or msg.get("thinking") or ""
```

### Lösung: B im Wrapper, A als Option

## 2. llama.cpp Reasoning-Modus

### Problem
Gemma4 wird mit `--jinja` gestartet, was den Reasoning-Modus aktiviert.
Der `deepseek`-Format extrahiert Gedanken nach `reasoning_content`.

### Solution A: Reasoning serverseitig deaktivieren
```bash
llama-server ... --reasoning off
```

### Solution B: Reasoning-Format auf "none" (Gedanken bleiben in content)
```bash
llama-server ... --reasoning-format none
```

### Solution C: Fallback-Extraktion (aktueller Wrapper)
```python
msg = data["choices"][0]["message"]
answer = msg.get("content") or msg.get("reasoning_content") or ""
```

### Empfehlung: C (kein Server-Neustart nötig) + A im Serve-Script ergänzen

## 3. Optimale Research-Prompts

### System-Prompt
```
Du bist ein Research-Assistent. Antworte sachlich und faktenbasiert.
Nenne Quellen wo möglich (Studien, Autoren, Jahre).
Keine Bewertung. Keine Ausflüchte. Antwort auf Deutsch.
```

### User-Prompts

#### Deep Summary
```
Fasse den Forschungsstand zu {THEMA} in 5-8 Absätzen zusammen.
Nenne konkrete Studien, Autoren und Jahreszahlen. Nur Fakten.
Thema: {THEMA}
```

#### Study Review
```
Welche klinischen Studien existieren zu {THEMA}?
Liste: Name, Autoren, Jahr, Design, Teilnehmerzahl, Ergebnisse.
Thema: {THEMA}
```

#### Pro/Contra
```
Liste ALLE Pro-Argumente und ALLE Contra-Argumente zu {THEMA}.
Nummeriere jedes Argument. Bleibe neutral.
Thema: {THEMA}
```

### Sampling-Einstellungen für faktenbasierte Recherche
- temperature: 0.1–0.3 (niedrig = faktennah)
- top_p: 0.9
- repeat_penalty: 1.1 (gegen Wiederholungen)
- max_tokens: 800–1500

## 4. GPT Researcher Integration

### Problem
GPT Researcher `GenericLLMProvider.get_chat_response()` liest NUR `output.content`.
Kein Hook für benutzerdefinierte Response-Extraktion.

### Lösung: Eigener LangChain-LLM-Wrapper
```python
from langchain_core.language_models.llms import LLM
from langchain_ollama import ChatOllama
from typing import Any

class UncensoredOllama(ChatOllama):
    """Ollama-Wrapper, der thinking nach content umleitet."""
    
    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)
        for generation in result.generations[0]:
            if not generation.text:
                # Versuche thinking aus der internen Response
                generation.text = generation.message.additional_kwargs.get("thinking", "")
        return result
```

## 5. Bekannte Einschränkungen

- **Obliterated Models + bestimmte Topics:** Gemma4 Obliterated produziert `***` bei stark zensierten Themen. Kein Workaround bekannt.
- **VRAM-Limit GTX 1070:** Max. 1 Modell gleichzeitig.
- **Thinking-Prompt-Qualität:** Reine "Keine Selbstzensur"-Befehle sind weniger wirksam als präzise Prompt-Constraints.
- **Ollama Temperature:** Unter 0.1 kann das Modell in Repetition verfallen.

## Quellen
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama Modelfile: https://github.com/ollama/ollama/blob/main/docs/modelfile.mdx  
- llama.cpp Server: https://github.com/ggml-org/llama.cpp/tree/master/tools/server
- Research-Agent Analyse 2026-05-16
