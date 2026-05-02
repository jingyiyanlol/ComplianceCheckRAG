# ComplianceCheckRAG

A self-hosted, multi-turn RAG application for highly secure teams to check on compliance against a knowledge-base, e.g. for bank compliance teams. Users can ask questions across regulatory documents and get cited, streamed answers via a mobile-friendly chat UI — with a full MLOps monitoring pipeline built in.

Current stack: No LangChain. No LlamaIndex. Plain Python orchestration.

---

## What it does

- **Multi-turn Q&A** over regulatory PDFs with automatic query rewriting for context-aware retrieval
- **Document scoping** — scope each conversation to all documents or a selected subset
- **Cited answers** — every response links back to the source chunk, section, and document
- **PII masking** — Microsoft Presidio masks sensitive entities before any LLM call
- **Streaming responses** — SSE token-by-token via native `fetch` + `ReadableStream`
- **User feedback** — thumbs up/down on every answer, fed into the monitoring pipeline
- **Three-layer observability** — real-time Prometheus metrics, per-request telemetry in SQLite, and a nightly drift detection job using Evidently + DeepEval

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, aiosqlite |
| LLM | Gemma 3 4B QAT (`gemma3:4b-q4_0`) via Ollama |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector DB | ChromaDB with metadata filtering |
| PII masking | Microsoft Presidio |
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS |
| Metrics | Prometheus + Grafana (2 dashboards) |
| Eval | DeepEval with local Ollama judge (no API key) |
| Drift detection | Evidently (KS test, PSI, embedding cosine drift) |
| CI/CD | GitHub Actions → GHCR |
| Deployment | Docker Compose (local), Kubernetes (production) |

---

## Architecture

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
                                                             │
                         ┌───────────────────────────────────┤
                         ▼                                   ▼
                  ┌────────────┐                  ┌────────────────────┐
                  │ Prometheus │                  │  Drift job         │
                  │ /metrics   │                  │  (nightly cron     │
                  └────────────┘                  │  + CI trigger      │
                         │                        │  + ad-hoc CLI)     │
                         ▼                        │                    │
                   ┌──────────┐                   │ DeepEval judge     │
                   │ Grafana  │<──drift metrics────│ Evidently stats    │
                   │ 2 boards │                   └────────────────────┘
                   └──────────┘
```

### Multi-turn pipeline (per request)

1. **Query rewrite** — last 4 turns + new message → Ollama → standalone search query
2. **Retrieve** — embed rewritten query → ChromaDB top-K=8 with optional `doc_filter`
3. **Generate** — system prompt + chunks + full history + user message → Ollama SSE stream
4. **Log** — telemetry row written non-blocking via `asyncio.create_task()`

---

## Quickstart

### Prerequisites

- Docker & Docker Compose
- Ollama running locally with `gemma3:4b-q4_0` and `nomic-embed-text` pulled

```bash
ollama pull gemma3:4b-q4_0
ollama pull nomic-embed-text
```

### 1. Clone and configure

```bash
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
cd ComplianceCheckRAG
cp .env.example .env
# Edit .env if needed — defaults work for local Docker Compose
```

### 2. Add your PDFs

```bash
cp your-regulatory-docs/*.pdf data/
```

### 3. Start services

```bash
docker compose up -d
```

Services started:
- `backend` → http://localhost:8000
- `frontend` → http://localhost:5173
- `chromadb` → http://localhost:8001
- `prometheus` → http://localhost:9090
- `grafana` → http://localhost:3000 (admin/admin)
- `pushgateway` → http://localhost:9091

### 4. Ingest documents

```bash
docker compose exec backend python -m app.rag.ingest
```

This extracts text, chunks by section, embeds with `nomic-embed-text`, upserts into ChromaDB, and generates `llms-txt/` artifacts. Re-ingestion is idempotent.

### 5. Open the UI

Navigate to http://localhost:5173. On first conversation, choose which documents to search (or search all). Ask away.

---

## Document scoping

Each conversation has a fixed scope chosen at start via the **Scope Modal**:

- **All documents** (default) — searches across everything ingested
- **Select documents** — multi-select list of ingested doc names

The chosen scope is shown as a persistent badge in the chat header and stored in `localStorage` with the conversation. It is sent as `doc_filter: string[] | null` with every `/chat` request and applied as a ChromaDB metadata filter.

---

## Monitoring

### Grafana dashboards

| Dashboard | Panels |
|---|---|
| App Performance | Request rate, latency histograms (retrieval + LLM + total), error rate, PII hit counter, conversation turn distribution |
| Model Quality | Faithfulness / answer relevance / context precision trends, feedback thumbs-down ratio, retrieval score distribution, drift breach gauge |

### Drift detection job — three modes

```bash
# Ad-hoc
python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 24

# Nightly (K8s CronJob at 02:00)
python monitoring/drift_job/run_drift.py --trigger cron

# Post-deploy CI (after RAG path changes)
python monitoring/drift_job/run_drift.py --trigger ci --pipeline-version $GITHUB_SHA
```

With Docker Compose:
```bash
docker compose --profile drift run drift-job
```

### What the drift job checks

| Sub-job | Method | Alert threshold |
|---|---|---|
| `retrieval_drift.py` | Evidently KS test on top-1 retrieval scores (24h vs 7-day baseline) | p-value < 0.01 |
| `output_drift.py` | Mean pairwise cosine similarity on response embeddings + PSI on response length | similarity drop > 0.05 |
| `quality_eval.py` | DeepEval faithfulness, answer relevance, context precision (sample ≤ 100 msgs, Gemma judge) | faithfulness < 0.7 or answer relevance < 0.65 |
| `feedback_analysis.py` | Thumbs-down ratio trend (24h vs 7-day) | ratio doubles |

Breach events write to the `drift_runs` table and push a gauge to Prometheus Pushgateway, which Grafana surfaces on the Model Quality board.

### Pre-deploy baseline snapshot

Before deploying a pipeline change, capture a reference window:

```bash
python monitoring/drift_job/snapshot.py --pipeline-version $(git rev-parse HEAD)
```

The post-deploy drift run compares against this snapshot.

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | SSE streaming chat. Body: `{conversation_id, history, message, doc_filter}` |
| `POST` | `/feedback` | Record thumbs up/down. Body: `{message_id, rating, comment?}` |
| `GET` | `/conversations/{id}` | Retrieve conversation history |
| `POST` | `/admin/ingest` | Trigger ingestion pipeline |
| `GET` | `/admin/documents` | List ingested documents |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

---

## Configuration

All settings are read from environment variables via `app/config.py` (pydantic-settings). Copy `.env.example` and adjust:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `LLM_MODEL` | `gemma3:4b-q4_0` | Model for generation and rewriting |
| `EMBED_MODEL` | `nomic-embed-text` | Model for embeddings |
| `CHROMA_HOST` | `chromadb` | ChromaDB host |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `CHROMA_AUTH_TOKEN` | _(empty)_ | Optional auth token |
| `TELEMETRY_DB_PATH` | `telemetry.db` | SQLite telemetry database path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allowed origin |

For local dev with a smaller model, set `LLM_MODEL=gemma3:1b`.

---

## Development

### Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # proxies /api/* to backend at localhost:8000
```

### Tests

```bash
# Backend
ruff check .
pytest

# Frontend
cd frontend
npm run lint
npm run build
```

---

## Repository layout

```
ComplianceCheckRAG/
├── app/
│   ├── main.py               # FastAPI app, CORS, Prometheus, routes
│   ├── config.py             # pydantic-settings
│   ├── conversation.py       # conversation state + SQLite persistence
│   ├── pii.py                # Presidio masking
│   ├── llm.py                # async Ollama streaming client
│   ├── metrics.py            # ccrag_* Prometheus metrics
│   ├── rag/
│   │   ├── ingest.py         # PDF → chunks → ChromaDB → llms-txt
│   │   ├── chunking.py       # section-aware chunker
│   │   ├── rewrite.py        # multi-turn query rewriter
│   │   ├── retrieve.py       # Chroma search + doc_filter
│   │   └── generate.py       # prompt assembly + SSE stream
│   └── telemetry/
│       ├── schema.py         # SQLAlchemy models
│       ├── logger.py         # non-blocking async telemetry writes
│       └── feedback.py       # feedback recording
├── monitoring/
│   ├── prometheus.yml
│   ├── grafana/
│   └── drift_job/
│       ├── run_drift.py      # CLI entrypoint
│       ├── snapshot.py       # pre-deploy baseline capture
│       ├── retrieval_drift.py
│       ├── output_drift.py
│       ├── quality_eval.py
│       ├── feedback_analysis.py
│       └── requirements.drift.txt
├── frontend/src/
│   ├── components/           # ChatWindow, MessageList, MessageInput,
│   │                         # CitationCard, FeedbackButtons, DocumentBadge, ScopeModal
│   ├── hooks/                # useConversation, useStreamingChat, useLocalStorage
│   ├── lib/api.ts            # all fetch calls
│   └── types.ts
├── data/                     # Drop PDFs here — gitignored
├── llms-txt/                 # Generated markdown artifacts per ingested doc
├── tests/
├── k8s/
├── .github/workflows/
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.drift
└── .env.example
```

---

## Telemetry schema (SQLite, Postgres-ready)

Raw events only — never aggregate at write time.

| Table | Purpose |
|---|---|
| `conversations` | Conversation + doc_filter |
| `messages` | Every turn: rewritten query, retrieved chunks, latencies, embeddings, PII found |
| `feedback` | Thumbs up/down with optional comment |
| `eval_results` | DeepEval metric scores per message per run |
| `drift_runs` | Drift job results: metric value, threshold, breach flag |
| `baseline_snapshots` | Pre-deploy reference metrics keyed by git SHA |

---

## Kubernetes deployment

```bash
kubectl apply -f k8s/manifests.yaml
kubectl apply -f k8s/cronjob-drift.yaml   # nightly drift at 02:00
```

The drift CronJob mounts the telemetry PVC read-only and pushes breach gauges to Pushgateway.

---

## Roadmap

Architecture is explicitly designed to support these without rewrites:

- Cross-encoder reranker (`bge-reranker-v2-m3` via Ollama)
- Hybrid search (BM25 + dense vector)
- Context recall metric (requires golden answer set)
- Agentic tools: `search_regulations`, `summarise_section`, `compare_clauses`
- A/B testing harness: two prompt variants compared via live feedback
- RAGAS-based eval on RAG-touching PRs in CI
- User auth via JWT
- Postgres migration (SQLAlchemy schema is already compatible)

---

## Security

- PII masked before every LLM call, including retrieved chunks and conversation history
- All dependency versions pinned (no `^` or `~`)
- Non-root users in all Docker images
- No secrets in code — use `.env` (see `.env.example`)
- CORS restricted to configured `FRONTEND_ORIGIN`
- CSP headers on nginx: `default-src 'self'`
- Conversation IDs via `crypto.randomUUID()`, never exposed in URLs
- Input length enforced at API layer (max 1000 chars per query)
