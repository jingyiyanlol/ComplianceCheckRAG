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

Click **Reopen in Container**. The image builds once (~2 min), then `make setup` runs automatically inside it. This installs the pre-commit hook, creates `.env` from `.env.example`, and sets up all project dependencies.

**2. Configure environment (if needed)**

Edit `.env` if your Ollama URL or model name differs from the defaults.

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
make install-hooks   # one-time: install pre-commit hook from scripts/
make dev-shell       # builds the dev container image (with deps pre-installed) and drops into bash
```

Inside the container shell, everything is ready — Python 3.11 and npm dependencies are already installed in the image:

```bash
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

## Development Workflow

See [Complete Workflow & CI/CD Guide](docs/workflow-summary.md) for step-by-step instructions from local development through deployment.

Quick reference for common tasks (run inside the dev container):

### Environment setup

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
│   ├── config.py             # pydantic-settings — all config via env vars
│   ├── conversation.py       # conversation state + SQLite persistence
│   ├── pii.py                # Presidio PII masking
│   ├── llm.py                # async Ollama streaming client
│   ├── metrics.py            # ccrag_* Prometheus metrics
│   ├── rag/
│   │   ├── ingest.py         # PDF → chunks → ChromaDB → llms-txt
│   │   ├── chunking.py       # section-aware chunker
│   │   ├── rewrite.py        # multi-turn query rewriter
│   │   ├── retrieve.py       # async Chroma search with doc_filter
│   │   └── generate.py       # prompt assembly + SSE stream
│   └── telemetry/
│       ├── schema.py         # SQLAlchemy models (Postgres-ready)
│       ├── logger.py         # non-blocking async telemetry writes
│       └── feedback.py       # thumbs up/down recording
├── monitoring/
│   ├── prometheus.yml        # scrape config for backend + Pushgateway
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/  # Prometheus datasource provisioning
│   │   │   └── dashboards/   # dashboard provisioning config
│   │   └── dashboards/
│   │       ├── app-performance.json
│   │       └── model-quality.json
│   └── drift_job/
│       ├── run_drift.py              # CLI entrypoint: --trigger cron|ci|adhoc
│       ├── snapshot.py               # pre-deploy baseline snapshot
│       ├── retrieval_drift.py        # Evidently KS test on retrieval scores
│       ├── output_drift.py           # Evidently embedding drift + PSI on length
│       ├── quality_eval.py           # DeepEval faithfulness / relevance / precision
│       ├── feedback_analysis.py      # thumbs-down ratio trend
│       └── requirements.drift.txt   # pinned deps for the drift job container
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx        # main layout wrapper
│   │   │   ├── MessageList.tsx       # auto-scroll, aria-live
│   │   │   ├── MessageInput.tsx      # mobile-aware, safe-area-inset
│   │   │   ├── CitationCard.tsx      # expandable source citation
│   │   │   ├── FeedbackButtons.tsx   # thumbs up/down, optimistic UI
│   │   │   ├── DocumentBadge.tsx     # active scope badge in header
│   │   │   └── ScopeModal.tsx        # session scope selector (new conv only)
│   │   ├── hooks/
│   │   │   ├── useConversation.ts    # conversation state + localStorage
│   │   │   ├── useStreamingChat.ts   # SSE reader + abort controller
│   │   │   └── useLocalStorage.ts    # generic typed localStorage hook
│   │   ├── lib/
│   │   │   └── api.ts                # all fetch calls — never inline fetch
│   │   ├── types.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json     # lockfile — install with npm ci
│   ├── tsconfig.json
│   ├── vite.config.ts        # proxies /api/* to backend in dev
│   ├── tailwind.config.js
│   └── Dockerfile            # node:24-slim build + nginx runtime
├── tests/
│   ├── conftest.py
│   ├── test_pii.py
│   ├── test_rag_eval.py
│   ├── test_conversation.py
│   ├── test_telemetry.py
│   └── test_security.py
├── k8s/
│   ├── manifests.yaml        # Namespace, ConfigMap, Deployments, PVCs
│   └── cronjob-drift.yaml    # nightly drift job at 02:00
├── .devcontainer/
│   ├── Dockerfile            # python:3.11-slim + Node 24 + pip-tools
│   └── devcontainer.json     # VS Code / Codespaces; runs make setup on create
├── .claude/
│   ├── agents/               # Claude Code subagents
│   │   ├── code-reviewer.md
│   │   ├── dependency-reviewer.md
│   │   ├── drift-analyst.md
│   │   ├── mobile-tester.md
│   │   ├── rag-evaluator.md
│   │   └── security-scanner.md
│   └── commands/             # slash-command skills
│       ├── ingest.md
│       ├── scaffold.md
│       ├── drift-run.md
│       └── ship-check.md
├── .github/
│   └── workflows/
│       ├── backend-ci.yml    # ruff + pytest + Docker build/push to GHCR
│       └── frontend-ci.yml   # lint + build + bundle size check + push
├── docs/                     # Detailed documentation per topic
│   ├── architecture.md       # multi-turn pipeline, component responsibilities
│   ├── ingestion.md          # PDF → chunk → ChromaDB pipeline deep-dive
│   ├── monitoring.md         # Prometheus metrics, Grafana, drift detection
│   ├── testing.md            # test suite structure, fixtures, coverage gaps
│   ├── deployment.md         # Docker Compose, K8s, CI/CD, env vars
│   └── dependencies.md       # pip-tools + npm dependency workflow
├── data/                     # Drop PDFs here — gitignored (PDFs only)
│   ├── .gitkeep
│   └── README.md             # ingestion instructions
├── llms-txt/                 # Generated clean markdown per ingested doc
│   └── .gitkeep
├── docker-compose.yml
├── Dockerfile                # backend — python:3.11-slim, non-root
├── Dockerfile.drift          # drift job — slim Python, drift deps only
├── Makefile                  # dev workflow: setup, run, test, compile-deps
├── pyproject.toml            # requires-python, ruff config, pytest config
├── requirements.in           # direct deps — edit this, not requirements.txt
├── requirements.txt          # pip-compile output — fully pinned + annotated
├── .python-version           # pyenv pin: 3.11
├── .env.example
└── README.md
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

## CI/CD (GitHub Actions)

Two workflows automatically run on every push and PR to `main`:

### Backend CI (`.github/workflows/backend-ci.yml`)

**Lint & Test job:**
- Runs ruff linter (Python code quality)
- Runs pytest in Docker (ensures Python 3.11, all pinned deps, and greenlet compatibility)
- Tests run against the `test` stage of the Dockerfile (not production image)

**Build & Push job** (main branch only):
- Builds backend Docker image from `Dockerfile` (runtime stage)
- Pushes to GHCR as `ghcr.io/{repo}/backend:latest` and `ghcr.io/{repo}/backend:{sha}`

**Drift Check job** (main branch only, on RAG component changes):
- Triggers when `app/rag/`, `app/llm.py`, or `docker-compose.yml` changes
- Runs drift detection job to catch quality regressions
- Compares against baseline snapshot from pre-deploy

### Frontend CI (`.github/workflows/frontend-ci.yml`)

- Runs `npm run lint` on Node 24
- Runs `npm run build` (fails if bundle gzip > 200KB)
- Pushes frontend image to GHCR

### Local equivalent

Run before committing:
```bash
make check              # lint + tests (both in Docker)
npm run lint            # frontend
npm run build           # frontend
```

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
