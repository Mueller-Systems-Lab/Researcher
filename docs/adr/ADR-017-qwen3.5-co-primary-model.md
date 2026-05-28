# ADR-017: Qwen3.5-Uncensored-HauhauCS as Co-Primary Model

**Status:** Proposed  
**Date:** 2026-05-28  
**Deciders:** Architecture Review Agent  
**Extends:** [ADR-016](ADR-016-gemma4-chat-model.md)  
**Context:** Re-evaluation of Qwen3.5 after testing a different GGUF/llama-server runtime, not the deprecated Ollama qwen3.5 path

---

## Context

The Researcher project uses local LLMs for chat, summary, report generation, extraction, scraping support, and structured-output tasks. ADR-015 originally selected an Ollama-based local model policy with `qwen3.5-uncensored-no-thinking:latest` for Chat/Summary and `nomic-embed-text:latest` for embeddings.

ADR-016 superseded the Chat/Summary part of ADR-015 after production issues with the old Ollama-based qwen3.5 path:

1. **Runtime instability:** Ollama chat runs terminated with `llama runner process has terminated`, especially during longer generations.
2. **VRAM pressure:** The old qwen3.5 Ollama path consumed about 6.6 GB VRAM on the GTX 1070 with 8 GB VRAM.
3. **Slow startup:** Ollama model loading could block startup for 120 seconds or more.
4. **Backend coupling:** Chat and embedding both depended on Ollama, making Ollama a larger operational single point of failure.
5. **Pascal precision trap:** The previous configuration was associated with GTX 1070/Pascal precision issues and unstable output.

ADR-016 therefore accepted **Gemma 4 E4B OBLITERATED** via `llama.cpp`/`llama-server` as the primary Chat/Summary model. Gemma 4 runs independently from Ollama, exposes an OpenAI-compatible endpoint, and uses Pascal-safe flags in `serve_gemma4_obliterated_researcher.sh`, including FP32 KV-cache and disabled flash attention.

Since ADR-016, a different Qwen3.5 runtime has been tested. This is **not** the deprecated Ollama `qwen3.5:9b` path from ADR-016. It is a GGUF model served directly by `llama.cpp`/`llama-server`, using the same backend family that stabilized Gemma 4:

- **Model:** `Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`
- **Backend:** `llama.cpp` `llama-server`, not Ollama
- **Serve script:** `serve_qwen3.5_uncensored.sh`
- **Alias:** `qwen3.5-uncensored`
- **Measured performance:** about 45 tok/s on GTX 1070
- **Measured quality:** 0% degenerate output in the referenced tests, clean extraction, and no thought-chain leakage
- **VRAM:** about 5.3 GB

Gemma 4 remains operational and valuable, but observed comparison data shows different strengths:

- Gemma 4: about 24 tok/s, about 3.8 GB VRAM, more VRAM-efficient, but observed around 20% degenerate output and hallucination risk on creative texts.
- Qwen3.5-Uncensored-HauhauCS GGUF: about 45 tok/s, about 5.3 GB VRAM, cleaner extraction/structured output, but higher VRAM pressure.

There is one configuration discrepancy to resolve before acceptance: the requested target port for the new Qwen3.5 co-primary service is **8082**, while the currently read `serve_qwen3.5_uncensored.sh` uses **8086** and `.env.example` documents `http://127.0.0.1:8086/v1`. This ADR proposes the architecture and records that port reconciliation must happen during implementation/review.

## Decision

Adopt **Qwen3.5-9B-Uncensored-HauhauCS-Aggressive GGUF via llama-server** as a **co-primary local Chat/Summary model** alongside **Gemma 4 E4B OBLITERATED**.

The co-primary split is role-based:

| Role / Workload | Preferred model | Reason |
|---|---|---|
| Fast extraction | Qwen3.5-Uncensored-HauhauCS | Higher measured throughput and clean extraction behavior |
| Scraping support | Qwen3.5-Uncensored-HauhauCS | Better structured output and fewer degenerate generations in tests |
| Structured output | Qwen3.5-Uncensored-HauhauCS | No thought-chain leakage observed; reliable formatting |
| VRAM-constrained runs | Gemma 4 OBLITERATED | About 3.8 GB VRAM vs Qwen3.5's about 5.3 GB |
| General Chat/Summary when memory is available | Either, with Qwen preferred for deterministic extraction-heavy workflows | Both use local llama-server; selection depends on quality/VRAM needs |
| Creative or exploratory tasks | Gemma 4 only when it does not degenerate; otherwise Qwen | Gemma can be useful but has observed hallucination/degeneration risk |

This ADR **does not supersede ADR-016**. ADR-016 remains accepted for the migration away from the unstable Ollama qwen3.5 path and for establishing Gemma 4 via llama-server as a primary VRAM-efficient model. ADR-017 extends ADR-016 by distinguishing the deprecated Ollama qwen3.5 path from the newly tested Qwen3.5-Uncensored-HauhauCS GGUF served through llama-server.

Ollama remains recommended only for embeddings (`nomic-embed-text:latest`) and as an explicitly documented fallback path where configured. The co-primary chat models should be exposed through local OpenAI-compatible llama-server endpoints and must not introduce cloud fallback by default.

## Model Comparison

| Characteristic | Qwen3.5-Uncensored-HauhauCS GGUF | Gemma 4 E4B OBLITERATED | Old Ollama qwen3.5 path |
|---|---:|---:|---:|
| Status after this ADR | Proposed co-primary | Accepted primary / co-primary | Deprecated |
| Backend | llama.cpp `llama-server` | llama.cpp `llama-server` | Ollama chat path |
| Model file / alias | `Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` / `qwen3.5-uncensored` | `gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf` / `gemma4-obliterated` | `qwen3.5:9b` or old local Ollama model |
| Serve script | `serve_qwen3.5_uncensored.sh` | `serve_gemma4_obliterated_researcher.sh` | Ollama service |
| Port | Target: 8082; current script/docs observed: 8086 | 8081 | 11434 via Ollama |
| Throughput on GTX 1070 | ~45 tok/s | ~24 tok/s | Startup/runtime instability observed |
| VRAM | ~5.3 GB | ~3.8 GB | ~6.6 GB |
| Output quality observed | 0% degenerate output; clean extraction; no thought chains | ~20% degenerate output; hallucination risk on creative texts | Unstable; deprecated by ADR-016 |
| Primary use cases | Extraction, scraping, structured output, high-throughput local generation | VRAM-efficient local chat/summary and fallback when VRAM is tight | Fallback/reference only, not active primary |
| Main limitation | Higher VRAM; may limit concurrent GPU use | Slower; quality degeneration observed | Ollama crashes, slow load, Pascal issues |

## Alternatives Considered

### Alternative A: Keep Gemma 4 as the only primary chat model

- **Pros:** Simpler operations; one llama-server chat endpoint; lower VRAM footprint; already accepted by ADR-016.
- **Cons:** Leaves measured Qwen3.5 throughput and extraction quality unused; keeps known Gemma 4 degeneration/hallucination risks as the only primary path.
- **Decision:** Rejected. Gemma 4 remains primary for VRAM-constrained scenarios, but not sufficient as the only primary for extraction-heavy workflows.

### Alternative B: Replace Gemma 4 with Qwen3.5-Uncensored-HauhauCS

- **Pros:** Fastest measured local generation; cleaner extraction and structured output; one active chat model.
- **Cons:** Increases baseline VRAM from about 3.8 GB to about 5.3 GB; weakens the project’s low-VRAM operating mode; contradicts ADR-016's still-valid Gemma 4 acceptance.
- **Decision:** Rejected. Qwen3.5 should be co-primary, not sole primary.

### Alternative C: Co-primary Qwen3.5-Uncensored-HauhauCS and Gemma 4

- **Pros:** Matches observed strengths; preserves Gemma 4's VRAM-efficient path; adds faster and cleaner extraction path; both use the stable llama-server backend; avoids returning to Ollama for chat.
- **Cons:** More operational complexity; two model endpoints to document; possible VRAM contention if both are started simultaneously on an 8 GB GTX 1070.
- **Decision:** Chosen. This gives the best balance between quality, performance, maintainability, and hardware constraints.

### Alternative D: Use a cloud LLM for extraction/structured output

- **Pros:** Potentially higher quality and availability; removes local VRAM constraints.
- **Cons:** Violates the local-first default; introduces data leakage, cost, provider coupling, secret management, and compliance risks.
- **Decision:** Rejected as default. Cloud remains disallowed unless explicitly enabled by project policy.

## Consequences

### Positive

1. **Faster extraction:** Qwen3.5-Uncensored-HauhauCS provides about 45 tok/s on GTX 1070 in the referenced tests.
2. **Cleaner structured output:** The new GGUF/llama-server path showed clean extraction, no thought-chain leakage, and no degenerate output in the referenced test set.
3. **Stable backend reuse:** Both co-primary models use `llama.cpp`/`llama-server`, avoiding the Ollama chat instability that ADR-016 deprecated.
4. **Better workload fit:** Model selection can be based on workload: Qwen for extraction/scraping/structured outputs; Gemma for lower-VRAM operation.
5. **Local-first preserved:** No cloud dependency or external provider is introduced.

### Negative

1. **Higher VRAM for Qwen:** Qwen3.5-Uncensored-HauhauCS uses about 5.3 GB VRAM, reducing headroom compared with Gemma 4.
2. **Two llama-server endpoints:** Operators must know which endpoint/model alias is active and configure `OPENAI_BASE_URL`/LLM variables accordingly.
3. **Potential GPU contention:** Running both models concurrently may exceed the practical GTX 1070 VRAM budget, especially alongside other GPU workloads.
4. **Configuration drift risk:** The task target says port 8082, while the current serve script and `.env.example` document 8086.
5. **Community-model risk:** The uncensored HauhauCS variant carries provenance, safety, and compliance risks that must remain explicit.

### Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Port mismatch between ADR target and script | Operators use wrong endpoint | Reconcile `serve_qwen3.5_uncensored.sh`, `.env.example`, and model docs before accepting this ADR |
| VRAM exhaustion when both models run | OOM, slowdowns, failed requests | Default to one active GPU model on GTX 1070 unless explicitly testing parallel operation |
| Model-selection ambiguity | Wrong model for extraction or VRAM-constrained runs | Document workload-based routing and aliases in runbooks/config docs |
| Community uncensored model behavior | Safety/compliance concerns | Keep local-only boundary; document provenance; avoid automatic cloud or public exposure |
| Regression in output quality | Broken extraction/report workflows | Add smoke/regression prompts for extraction, structured JSON, and no-thought-chain behavior |

## Relationship to ADR-016

ADR-017 extends ADR-016; it does not supersede it.

ADR-016 remains correct for these decisions:

- The old Ollama-based qwen3.5 chat path is deprecated.
- Gemma 4 E4B OBLITERATED via llama-server remains accepted.
- Chat should be decoupled from Ollama embeddings.
- llama-server is the preferred local chat backend.
- Gemma 4 remains the primary choice when VRAM is constrained.

ADR-017 adds this clarification:

- The newly tested Qwen3.5-Uncensored-HauhauCS GGUF via llama-server is a different operational path from the deprecated Ollama qwen3.5 path.
- Because it uses the same stable backend class as Gemma 4 and has better measured extraction performance, it should be treated as co-primary for extraction, scraping, and structured-output tasks.

## Architecture Review Checklist

- [x] New dependency justified? **No new dependency; this reuses the existing llama.cpp/llama-server backend already accepted by ADR-016.**
- [x] Module coupling acceptable? **Acceptable if routing stays configuration-based by endpoint/model alias and does not hard-code model choice throughout application modules.**
- [x] Data flow documented and secure? **Local input → local llama-server endpoint → local reports/outputs; no cloud fallback by default.**
- [x] Error handling strategy consistent? **Serve scripts should fail clearly on missing GGUF/server binaries; smoke tests should detect unavailable endpoints and wrong ports.**
- [x] Scaling bottlenecks identified? **GTX 1070 8 GB VRAM is the limiting resource; concurrent model serving is not the default operating mode.**
- [x] Security boundaries clearly defined? **Both chat models stay bound to local llama-server endpoints; uncensored community-model risks are documented; no public exposure assumed.**
- [x] Testing strategy adequate? **Before acceptance, run endpoint smoke checks plus regression prompts for extraction, structured output, no thought chains, and degenerate-output detection.**

## References

- `docs/adr/ADR-016-gemma4-chat-model.md` — accepted Gemma 4 migration and old qwen3.5 deprecation
- `docs/adr/ADR-015-local-llm-model-policy.md` — superseded Chat/Summary role and active embedding role
- `serve_qwen3.5_uncensored.sh` — Qwen3.5 GGUF llama-server script; currently observed on port 8086
- `serve_gemma4_obliterated_researcher.sh` — Gemma 4 llama-server script on port 8081
- `config/ollama_models.py` — Ollama fallback/deprecation logic
- `.env.example` — current FAST_LLM/OPENAI_BASE_URL and Qwen/Gemma endpoint comments
