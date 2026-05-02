# Architecture

## Overview

ComplianceCheckRAG is a self-hosted, multi-turn RAG system. Every component runs on open-source tooling with no paid services or hosted APIs.

```
┌─────────────┐  session scope set once
│  React UI   │  per conversation (modal on new chat)
│  + doc scope│──fetch SSE──────────────────────────┐
└─────────────┘                                     │
                                                    ▼
                                      ┌─────────────────────────┐
                                      │  FastAPI /chat          │
                                      │  doc_filter: str[]|null │
                                      └─────────────────────────┘
                                                    │
                    ┌───────────────────────────────┼──────────────────┐
                    ▼                               ▼                  ▼
              ┌──────────┐                  ┌─────────────┐   ┌──────────────┐
              │  Query   │                  │  Retrieve   │   │  Generate    │
              │  Rewrite │────────────────> │  ChromaDB   │──>│  Ollama      │
              │  (LLM)   │                  │  + metadata │   │  (SSE stream)│
              └──────────┘                  │  filter     │   └──────────────┘
                                            └─────────────┘          │
                                                    │                 │
                                                    └────────┬────────┘
                                                             ▼
                                                 ┌─────────────────────┐
                                                 │  Telemetry logger   │
                                                 │  (non-blocking)     │
                                                 │  SQLite telemetry.db│
                                                 └─────────────────────┘
```

---

## Multi-turn pipeline (per `/chat` request)

### Step 1 — PII masking

Before any text reaches an LLM, the full conversation history and the new user message are passed through Microsoft Presidio. Detected entities (names, emails, phone numbers, IDs, etc.) are replaced with placeholders like `<PERSON>`. The list of detected entity types is recorded in telemetry.

This runs **before** query rewriting and **before** generation — Ollama never sees raw PII.

### Step 2 — Query rewrite (`app/rag/rewrite.py`)

The last N=4 turns of the masked conversation history plus the new message are sent to Ollama with the prompt:

> *"Given this conversation, write a self-contained search query for the latest question. Output only the query."*

This converts a follow-up like *"What about Tier 2?"* into a standalone query like *"Basel III Tier 2 capital requirements"* that can be embedded and searched without conversation context.

The rewritten query is stored in telemetry for drift analysis.

### Step 3 — Retrieve (`app/rag/retrieve.py`)

The rewritten query is embedded using `nomic-embed-text` via Ollama. ChromaDB returns the top-K=8 closest chunks by cosine similarity.

If the conversation has a `doc_filter` (set at conversation start via the Scope Modal), ChromaDB applies a metadata `where` filter on `doc_name` before scoring — restricting results to the selected documents.

The retrieve function is fully async. Both the Ollama embed call and the ChromaDB query are synchronous operations wrapped in `asyncio.get_running_loop().run_in_executor(None, ...)` to avoid blocking the event loop.

### Step 4 — Generate (`app/rag/generate.py`)

The prompt assembles:
1. A system prompt establishing the compliance assistant role
2. The retrieved chunks, each prefixed with `[Source: {doc_name} — {section}]`
3. The full masked conversation history
4. The current user message

This is sent to Ollama and the response is streamed back as SSE (`text/event-stream`). The frontend reads tokens using the native `fetch` + `ReadableStream` API.

### Step 5 — Telemetry (non-blocking)

After the full response is generated, `log_message()` is called. It schedules an `asyncio.create_task()` that writes the telemetry row to SQLite — including the rewritten query, retrieved chunks with scores, latencies, response embedding, and PII entities found.

The task is scheduled **before** the `event: done` SSE frame so telemetry is never dropped if the client disconnects after receiving the done signal.

---

## Document scoping

Each conversation has a fixed scope chosen once via the Scope Modal on first message:

- **All documents** (`doc_filter: null`) — ChromaDB searches across all ingested chunks
- **Selected documents** (`doc_filter: ["doc_a", "doc_b"]`) — ChromaDB filters by `doc_name` metadata

The scope is stored in `localStorage` alongside the conversation. Reloading the page resumes the same conversation with the same scope — the modal only appears on a genuinely new conversation.

---

## Key design decisions

**No LangChain / LlamaIndex** — orchestration is plain Python. Each pipeline stage is a small, testable function. The absence of framework abstractions makes the retrieval and generation logic transparent and easy to modify.

**Section-aware chunking over fixed-size** — splitting at section headings preserves semantic boundaries. A chunk is always a complete thought from the document, never a mid-sentence fragment. The trade-off is variable chunk sizes; very long sections are not further split (a roadmap item).

**Async with run_in_executor for sync deps** — Ollama's Python SDK and ChromaDB's client are synchronous. Rather than blocking the asyncio event loop, all sync I/O is wrapped in `run_in_executor`. This keeps the FastAPI server responsive under concurrent requests.

**SQLite for telemetry** — zero-infrastructure for local dev; the SQLAlchemy schema is fully Postgres-compatible via connection string change only. The `messages` table stores raw embeddings as BLOBs so the drift job can compute cosine similarity without re-embedding.

**PII masking before every LLM call** — Presidio runs on the user message, conversation history, and retrieved chunks before any text is sent to Ollama. This is a hard requirement for deployment in regulated environments.

---

## Component responsibilities

| Component | File(s) | Responsibility |
|---|---|---|
| API layer | `app/main.py` | Routing, CORS, Prometheus instrumentation, SSE streaming |
| Config | `app/config.py` | All settings via pydantic-settings + env vars |
| PII masking | `app/pii.py` | Presidio `mask(text) → (masked_text, entities)` |
| LLM client | `app/llm.py` | Async Ollama streaming wrapper |
| Query rewriter | `app/rag/rewrite.py` | Multi-turn → standalone query |
| Retrieval | `app/rag/retrieve.py` | Embed + ChromaDB search + doc_filter |
| Generation | `app/rag/generate.py` | Prompt assembly + SSE stream |
| Chunker | `app/rag/chunking.py` | PDF extraction + section-aware splitting |
| Ingestion | `app/rag/ingest.py` | Pipeline orchestrator + llms-txt writer |
| Telemetry | `app/telemetry/logger.py` | Non-blocking async SQLite writes |
| Feedback | `app/telemetry/feedback.py` | Thumbs up/down recording |
| Metrics | `app/metrics.py` | Prometheus metric definitions |
| Conversation | `app/conversation.py` | Session state + history retrieval |
