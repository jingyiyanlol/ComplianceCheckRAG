[![Backend CI](https://github.com/jingyiyanlol/ComplianceCheckRAG/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/jingyiyanlol/ComplianceCheckRAG/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/jingyiyanlol/ComplianceCheckRAG/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/jingyiyanlol/ComplianceCheckRAG/actions/workflows/frontend-ci.yml)

# ComplianceCheckRAG

A self-hosted, multi-turn RAG application for highly secure teams to check on compliance against a knowledge-base, e.g. for bank compliance teams. Users can ask questions across regulatory documents and get cited, streamed answers via a mobile-friendly chat UI — with a full MLOps monitoring pipeline built in.

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
| LLM | Gemma 3 1B (`gemma3:1b`) via Ollama |
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
                  ┌────────────┐                   ┌────────────────────┐
                  │ Prometheus │                   │  Drift job         │
                  │ /metrics   │                   │  (nightly cron     │
                  └────────────┘                   │  + CI trigger      │
                         │                         │  + ad-hoc CLI)     │
                         ▼                         │                    │
                   ┌──────────┐                    │ DeepEval judge     │
                   │ Grafana  │<──drift metrics────│ Evidently stats    │
                   │ 2 boards │                    └────────────────────┘
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

| Requirement | Purpose |
|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2) | Dev container, app services, drift job |
| [Ollama](https://ollama.com) running on the host | LLM inference and embeddings |
| [VS Code](https://code.visualstudio.com) + [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) | Recommended dev workflow (optional — see CLI alternative below) |

Pull the required Ollama models once:

```bash
ollama pull gemma3:1b         # generation + query rewriting
ollama pull nomic-embed-text  # embeddings
```

---

### Option A — VS Code Dev Container (recommended)

The dev container ships **Python 3.11 + Node 24** on a Debian Linux base. No local Python or Node install needed.

**1. Clone and open**

```bash
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
code ComplianceCheckRAG
```

VS Code will detect `.devcontainer/devcontainer.json` and prompt:
> "Folder contains a Dev Container configuration file. Reopen in Container?"

Click **Reopen in Container**. The image builds once (~2 min), then `make setup` runs automatically inside it.

**2. Configure environment**

The setup step creates `.env` from `.env.example` if it doesn't exist. Edit it if your Ollama URL or model name differs from the defaults.

**3. Add your PDFs**

```bash
cp your-regulatory-docs/*.pdf data/
```

**4. Ingest documents**

Open a terminal inside the container (VS Code terminal is already inside it):

```bash
make ingest
```

**5. Start the app**

```bash
make backend    # terminal 1 — FastAPI at http://localhost:8000
make frontend   # terminal 2 — Vite dev server at http://localhost:5173
```

Port forwarding is configured automatically. Open http://localhost:5173 in your host browser.

---

### Option B — CLI dev container (no VS Code)

```bash
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
cd ComplianceCheckRAG
make dev-shell        # builds the dev container image and drops into bash
```

Inside the container shell:

```bash
make setup            # creates .venv, installs Python + npm deps, downloads spacy model
cp .env.example .env  # edit as needed
cp your-docs/*.pdf data/
make ingest
make backend &        # background or split a second shell with: docker exec -it <container> bash
make frontend
```

---

### Option C — Full Docker Compose stack (production-like)

Runs all services (backend, frontend, ChromaDB, Prometheus, Grafana, Pushgateway) as containers. No dev container needed.

```bash
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
cd ComplianceCheckRAG
cp .env.example .env  # edit if needed — defaults work for local Compose
docker compose up -d
docker compose exec backend python -m app.rag.ingest
```

Services started:
- `backend` → http://localhost:8000
- `frontend` → http://localhost:5173
- `chromadb` → http://localhost:8001
- `prometheus` → http://localhost:9090
- `grafana` → http://localhost:3000 (admin/admin)
- `pushgateway` → http://localhost:9091

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

All settings are read from environment variables via `app/config.py` (pydantic-settings).

### Setup

```bash
cp .env.example .env
# Edit .env to match your local setup
```

### `.env` format

```dotenv
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gemma3:1b
EMBED_MODEL=nomic-embed-text

# ChromaDB
# "local" = PersistentClient on disk (no Docker needed for dev)
# "http"  = connects to a running ChromaDB server (Docker / K8s)
CHROMA_MODE=local
CHROMA_LOCAL_PATH=.chroma          # only used when CHROMA_MODE=local
CHROMA_HOST=localhost              # only used when CHROMA_MODE=http
CHROMA_PORT=8001                   # only used when CHROMA_MODE=http
CHROMA_AUTH_TOKEN=                 # optional bearer token for ChromaDB
CHROMA_COLLECTION=compliance_docs

# Telemetry
TELEMETRY_DB_PATH=telemetry.db

# App
LOG_LEVEL=INFO
FRONTEND_ORIGIN=http://localhost:5173
```

### Variable reference

| Variable | Local default | Production default | Description |
|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` | Ollama service URL |
| `LLM_MODEL` | `gemma3:1b` | `gemma3:1b` | Model for generation and query rewriting |
| `EMBED_MODEL` | `nomic-embed-text` | `nomic-embed-text` | Model for embeddings |
| `CHROMA_MODE` | `local` | `http` | `local` = PersistentClient; `http` = server |
| `CHROMA_LOCAL_PATH` | `.chroma` | — | On-disk path for local ChromaDB |
| `CHROMA_HOST` | `localhost` | `chromadb` | ChromaDB host (http mode only) |
| `CHROMA_PORT` | `8001` | `8000` | ChromaDB port (http mode only) |
| `CHROMA_AUTH_TOKEN` | _(empty)_ | _(empty)_ | Optional ChromaDB bearer token |
| `CHROMA_COLLECTION` | `compliance_docs` | `compliance_docs` | ChromaDB collection name |
| `TELEMETRY_DB_PATH` | `telemetry.db` | `/telemetry/telemetry.db` | SQLite telemetry DB path |
| `LOG_LEVEL` | `INFO` | `INFO` | Python logging level |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | your domain | CORS allowed origin |

---

## Development

The dev environment is containerised. All `make` targets below are meant to be run **inside the dev container** (VS Code terminal or `make dev-shell`).

### Environment setup

```bash
make setup          # first-time: creates .venv, installs all deps, downloads spacy model
                    # (runs automatically in VS Code Dev Containers via postCreateCommand)
```

### Running the app

```bash
make backend        # FastAPI with --reload at http://localhost:8000
make frontend       # Vite dev server at http://localhost:5173 (proxies /api/* to backend)
```

### Ingestion

```bash
cp your-docs/*.pdf data/
make ingest         # extract → chunk → embed → upsert ChromaDB → generate llms-txt/
```

Re-ingestion is idempotent — keyed on `(doc_name, chunk_index, content_hash)`.

### Tests and lint

```bash
make check          # ruff lint + pytest in one shot

make lint           # ruff check only
make lint-fix       # ruff --fix
make test           # pytest -v
```

Frontend checks (run from the repo root inside the container):

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

### Makefile reference

```
make help           # full target list with descriptions
make setup          # install all deps (backend + frontend)
make setup-backend  # Python venv + pip + spacy model only
make setup-frontend # npm ci only
make dev-shell      # build dev container image and open a bash shell (no VS Code needed)
make backend        # start FastAPI
make frontend       # start Vite
make ingest         # run ingestion pipeline
make test           # pytest
make lint           # ruff
make check          # lint + test
make clean          # remove .chroma/, telemetry.db, llms-txt/*.md, caches
make clean-all      # clean + remove .venv and node_modules
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
├── .devcontainer/
│   ├── Dockerfile            # python:3.11-slim + Node 24 — canonical dev environment
│   └── devcontainer.json     # VS Code / Codespaces config; runs make setup on create
├── data/                     # Drop PDFs here — gitignored
├── llms-txt/                 # Generated markdown artifacts per ingested doc
├── tests/
├── k8s/
├── .github/workflows/
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.drift
├── Makefile
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
