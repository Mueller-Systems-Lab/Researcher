# OpenCode Local Offline Stack Blueprint

## Objective

Build a fully local AI engineering stack using:

- local MCP servers
- local inference
- offline RAG
- deterministic workflows
- reproducible builds

---

# Requirements

The system MUST operate without cloud APIs.

---

# Recommended Stack

## Inference

- llama.cpp
- Ollama
- vLLM

## Models

- Gemma
- Qwen
- DeepSeek
- Mistral

## Embeddings

- bge-small
- nomic-embed
- e5-small

---

# Architecture

```text
OpenCode
    ↓
Local MCP Layer
    ↓
Python Orchestrator
    ↓
Local Workers
    ↓
llama-server
```

---

# MCP Requirements

## Required

- filesystem
- terminal
- docker
- git
- github
- sqlite
- local-rag
- markdown-export

---

# Offline RAG Rules

The system MUST:

- support chunk deduplication
- support metadata filtering
- support embedding versioning
- support source attribution

---

# Reliability Rules

The system MUST:

- retry failed generations
- cache outputs
- validate schemas
- validate tool outputs
- preserve logs

---

# Resource Optimization

For 8 GB VRAM:

- prefer 7B-12B models
- use Q4 quantization
- offload layers carefully
- avoid oversized context windows
- externalize memory into RAG

---

# Acceptance Criteria

The local stack is considered stable only if:

- all workflows operate offline
- structured outputs remain stable
- hallucination rate remains controlled
- tool calling remains deterministic
