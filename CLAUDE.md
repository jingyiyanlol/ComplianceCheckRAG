# ComplianceCheckRAG

A self-hosted, multi-turn RAG application that lets bank employees ask compliance questions across regulatory documents and get cited answers via a mobile-friendly chat UI. Includes a full model-monitoring pipeline: app performance metrics, retrieval quality drift, output quality drift (LLM-as-judge via DeepEval), and user feedback signals — all using open-source tools, no paid services.

## Project goal

Demonstrate the full MLOps lifecycle for a RAG system: ingestion, serving, observability, drift detection, and continuous evaluation. Designed as an evolving portfolio project — the architecture must support adding enhancements (rerankers, hybrid search, agentic tools, A/B testing) without rewrites.

---

## Tech stack (do not deviate without asking)

### Backend
- **Language**: Python 3.11
- **Web framework**: FastAPI
- **LLM**: Gemma 3 1B via Ollama (`gemma3:1b`)
- **Embeddings**: `nomic-embed-text` via Ollama
- **Vector DB**: ChromaDB with metadata filtering
- **PII masking**: Microsoft Presidio
- **Telemetry store**: SQLite (local dev); Postgres-ready SQLAlchemy schema
- **Eval framework**: DeepEval (local Ollama judge, no API key)
- **Drift detection**: Evidently (distribution-level statistical tests)

### Frontend
- **Build tool**: Vite
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (copy-paste, no runtime dependency)
- **State**: `useState` / `useReducer` only — no Redux, no Zustand
- **Persistence**: `localStorage` for conversations; cross-device sync is a roadmap item
- **HTTP**: native `fetch` with `ReadableStream` for SSE streaming

### Infra
- **App metrics**: Prometheus + Grafana
- **Drift job scheduler**: K8s CronJob (nightly); GitHub Actions (post-deploy trigger); CLI for ad-hoc
- **CI/CD**: GitHub Actions → GitHub Container Registry (GHCR)
- **Deployment**: Docker Compose (local); Kubernetes manifests (VM/cluster)

Do not introduce LangChain, LlamaIndex, Redux, Arize Phoenix, or any paid service. Plain orchestration shows engineering judgement.

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

---

## Repository layout

```
ComplianceCheckRAG/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── conversation.py
│   ├── pii.py
│   ├── llm.py
│   ├── metrics.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   ├── chunking.py
│   │   ├── rewrite.py
│   │   ├── retrieve.py
│   │   └── generate.py
│   └── telemetry/
│       ├── __init__.py
│       ├── schema.py
│       ├── logger.py
│       └── feedback.py
├── monitoring/
│   ├── prometheus.yml
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   └── dashboards/
│   │   └── dashboards/
│   │       ├── app-performance.json
│   │       └── model-quality.json
│   └── drift_job/
│       ├── run_drift.py              # entrypoint: nightly, CI, or ad-hoc
│       ├── snapshot.py               # save pre-deploy baseline snapshot
│       ├── retrieval_drift.py        # Evidently KS test on retrieval scores
│       ├── output_drift.py           # Evidently embedding drift on responses
│       ├── quality_eval.py           # DeepEval: faithfulness, answer relevance, context precision
│       ├── feedback_analysis.py      # thumbs ratio trend
│       └── requirements.drift.txt   # pinned deps for the drift job container
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   ├── FeedbackButtons.tsx
│   │   │   ├── DocumentBadge.tsx
│   │   │   └── ScopeModal.tsx        # session scope selector
│   │   ├── hooks/
│   │   │   ├── useConversation.ts
│   │   │   ├── useStreamingChat.ts
│   │   │   └── useLocalStorage.ts
│   │   ├── lib/
│   │   │   └── api.ts
│   │   ├── types.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── data/                             # Drop PDFs here — any number
│   └── .gitkeep
├── llms-txt/                         # Generated per ingested doc
│   └── .gitkeep
├── tests/
│   ├── test_pii.py
│   ├── test_rag_eval.py
│   ├── test_conversation.py
│   ├── test_telemetry.py
│   └── test_security.py
├── k8s/
│   ├── manifests.yaml
│   └── cronjob-drift.yaml
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.drift
├── requirements.txt
└── README.md
```

---

## Document scoping UX

**Session scope is set once per conversation and never reset mid-session.**

On "New conversation," before any message is sent, show `ScopeModal`:
- Header: "Which documents should I search?"
- Option A: **All documents** (default) — global search across everything ingested
- Option B: **Select documents** — multi-select list of ingested doc names with checkboxes
- A "Start" button confirms the choice and dismisses the modal
- The chosen scope is displayed as a persistent badge in the chat header throughout the session

The scope is stored in conversation state (`doc_filter: string[] | null`) and sent with every `/chat` request. `null` = global. The backend passes it as a ChromaDB `where` metadata filter on `doc_name`.

The scope modal only re-appears on a genuinely new conversation (new `conversation_id`). It does not re-appear if the user reloads the page and resumes an existing conversation — the scope is persisted in `localStorage` with the conversation.

---

## Multi-turn pipeline

The `/chat` endpoint accepts `{conversation_id, history: Message[], message: string, doc_filter: string[] | null}`.

1. **Query rewrite**: send last N=4 turns + new message to Ollama with prompt: *"Given this conversation, write a self-contained search query for the latest question. Output only the query."* Store rewritten query in telemetry.
2. **Retrieve**: embed the rewritten query, search ChromaDB with optional `doc_filter`, get top-K=8.
3. **Generate**: assemble system prompt + retrieved chunks + full conversation history + user message. Stream SSE response.
4. **Log**: write telemetry row non-blocking after streaming completes.

---

## Multi-document ingestion

`data/` may hold any number of PDFs. The ingestion pipeline:

1. For each PDF: extract text with PyMuPDF, generate `llms-txt/<name>.md` (section-aware clean markdown with metadata header).
2. Chunk by section (not fixed-size). Each chunk carries metadata: `{doc_name, doc_title, section, section_path, chunk_index, ingested_at, content_hash}`.
3. Upsert into ChromaDB. Re-ingestion is idempotent — keyed on `(doc_name, chunk_index, content_hash)`.
4. **Pre-deploy baseline snapshot**: before ingesting documents that change the pipeline, call `monitoring/drift_job/snapshot.py` to capture a reference window of retrieval scores and response embeddings. This snapshot is the baseline for the next drift run.

---

## Telemetry schema

SQLite (Postgres-ready via SQLAlchemy). Never aggregate at write time — always log raw events.

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    doc_filter JSON,                     -- null = global, else list of doc names
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,                  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    rewritten_query TEXT,
    retrieved_chunks JSON,               -- [{chunk_id, score, doc_name, section}]
    retrieval_latency_ms INTEGER,
    llm_latency_ms INTEGER,
    response_length INTEGER,
    response_embedding BLOB,             -- float32 array for output drift
    query_embedding BLOB,                -- for query distribution drift
    pii_entities_found JSON,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id),
    rating INTEGER NOT NULL,             -- 1 = thumbs up, -1 = thumbs down
    comment TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE eval_results (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id),
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,           -- 'faithfulness' | 'answer_relevance' | 'context_precision'
    score REAL NOT NULL,
    reason TEXT,                         -- LLM judge's reasoning
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE drift_runs (
    id TEXT PRIMARY KEY,
    triggered_by TEXT NOT NULL,          -- 'cron' | 'ci' | 'adhoc'
    pipeline_version TEXT,               -- git SHA of the deploy that triggered it
    run_at TIMESTAMP NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    threshold REAL NOT NULL,
    breached BOOLEAN NOT NULL,
    details JSON
);

CREATE TABLE baseline_snapshots (
    id TEXT PRIMARY KEY,
    pipeline_version TEXT NOT NULL,      -- git SHA
    captured_at TIMESTAMP NOT NULL,
    retrieval_score_p50 REAL,
    retrieval_score_p95 REAL,
    response_length_p50 REAL,
    faithfulness_mean REAL,
    answer_relevance_mean REAL,
    context_precision_mean REAL,
    feedback_thumbsdown_ratio REAL,
    sample_size INTEGER
);
```

---

## Drift monitoring — three layers

### Layer 1: App performance (Prometheus, real-time)

Metrics exposed at `/metrics` — standard FastAPI instrumentation plus custom:
- `ccrag_query_total` (counter, label: status)
- `ccrag_query_latency_seconds` (histogram)
- `ccrag_retrieval_latency_seconds` (histogram)
- `ccrag_llm_latency_seconds` (histogram)
- `ccrag_chunks_retrieved` (histogram)
- `ccrag_pii_hits_total` (counter, label: entity_type)
- `ccrag_conversation_turns` (histogram)
- `ccrag_feedback_total` (counter, label: rating)
- `ccrag_drift_breach` (gauge, label: metric_name) — set by drift job via Prometheus Pushgateway

### Layer 2: Per-event telemetry (SQLite, every request)

Everything in the `messages` table. The raw retrieval scores, response embeddings, and query embeddings are the source of truth for all statistical drift analysis. Written non-blocking after streaming completes.

### Layer 3: Drift detection job

**Scheduling — three modes:**

```
# Nightly (K8s CronJob, also docker-compose profile)
0 2 * * * python monitoring/drift_job/run_drift.py --trigger cron

# Post-deploy (GitHub Actions, after any RAG component change)
python monitoring/drift_job/run_drift.py --trigger ci --pipeline-version $GITHUB_SHA

# Ad-hoc (CLI)
python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 24
```

The CI trigger runs automatically when any of these paths change: `app/rag/`, `app/llm.py`, `docker-compose.yml` (model version change). It captures a baseline snapshot *before* the deploy, then runs drift comparison *after*.

**What each sub-job computes:**

`retrieval_drift.py` (Evidently):
- Pull retrieval top-1 scores from last 24h vs 7-day reference window
- Kolmogorov-Smirnov test on score distributions
- Alert threshold: p-value < 0.01

`output_drift.py` (Evidently):
- Pull response embeddings from last 24h vs reference
- Mean pairwise cosine similarity between windows
- Alert threshold: mean similarity drop > 0.05
- PSI on response length distribution

`quality_eval.py` (DeepEval with local Ollama judge):
- Sample up to 100 messages from the last 24h (not every message — too slow)
- For each sampled message, run DeepEval metrics using Gemma via Ollama as the judge:
  - **Faithfulness**: is the response grounded in the retrieved chunks? (no hallucination)
  - **Answer relevance**: does the response actually address the query?
  - **Context precision**: of retrieved chunks, how many contributed to the response?
- Write scores to `eval_results` table
- Alert if mean faithfulness drops below 0.7 or answer relevance below 0.65

`feedback_analysis.py`:
- Thumbs-down ratio for last 24h vs 7-day baseline
- Alert if ratio doubles
- Surface top 5 most recent negative feedback comments for human review

All results write to `drift_runs` table and push breach gauges to Prometheus Pushgateway → Grafana.

**DeepEval configuration (local, no API key):**

```python
# In quality_eval.py
from deepeval.models import OllamaModel
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualPrecisionMetric

judge_model = OllamaModel(model="gemma3:1b")

faithfulness = FaithfulnessMetric(threshold=0.7, model=judge_model, include_reason=True)
answer_relevancy = AnswerRelevancyMetric(threshold=0.65, model=judge_model)
context_precision = ContextualPrecisionMetric(threshold=0.6, model=judge_model)
```

**Which pipeline change triggers which metric alert:**

| Component changed | Primary metrics | Method |
|---|---|---|
| Embedding model | Retrieval score distribution, query-chunk similarity | Evidently KS test |
| Chunking strategy | Context precision, retrieval score variance | Evidently + DeepEval |
| Reranker added/changed | Top-1 score distribution, context precision | Evidently + DeepEval |
| Top-K changed | Context precision, response length | DeepEval |
| Prompt template changed | Faithfulness, answer relevance | DeepEval |
| LLM model changed | All generation metrics | Full DeepEval suite |

---

## User feedback flow

Each assistant message has thumbs up / thumbs down buttons in the UI. On click:
1. Frontend POSTs `{message_id, rating, comment?}` to `/feedback`
2. Backend writes to `feedback` table
3. UI shows acknowledged state (no re-render, optimistic update)
4. Feedback ratio feeds into nightly drift job as a direct human quality signal

Feedback is treated as a first-class quality signal — it is the only signal that doesn't require an LLM judge to interpret.

---

## Backend coding rules

- Type-hint everything. `from __future__ import annotations` at top of every module.
- No `print` — use `logging`, configured once in `main.py`.
- All config via `config.py` (pydantic-settings). Never hardcode model names, hosts, ports.
- Functions ≤ 40 lines. Docstrings with Args/Returns on all public functions.
- Pydantic models on every endpoint. Reject queries > 1000 chars.
- `/chat` must support SSE streaming.
- CORS restricted to configured frontend origin.
- **Telemetry writes are non-blocking** — `asyncio.create_task()`, never awaited in the request path.
- **PII masking runs before every LLM call**, including retrieved context and conversation history.

## Frontend coding rules

- TypeScript strict mode. No `any` without a justification comment.
- Functional components only.
- Custom hooks for non-trivial state.
- All API calls via `lib/api.ts` — never inline `fetch`.
- Mobile-first Tailwind. Tap targets ≥ 44x44px.
- `react-markdown` for rendering — never `dangerouslySetInnerHTML`.
- `ScopeModal` shown on new conversation only; scope persisted in localStorage with conversation.

## Mobile and browser support

- Chrome, Firefox, Safari, Edge (current + one version back)
- iOS Safari 16+, Chrome Android 10+
- Viewport meta with `viewport-fit=cover`
- Chat input clear of iOS keyboard (`env(safe-area-inset-bottom)`)
- Auto-scroll to latest message; pause on manual scroll-up
- No horizontal overflow at 375px width

## Security guardrails

- PII mask before every LLM call — including retrieved chunks and conversation history
- No raw query/response logging at INFO level
- All versions pinned in both `requirements.txt` and `package.json` (no `^` or `~`)
- Non-root in both Dockerfiles
- No secrets in code — `.env.example` with placeholders
- Pydantic validation on all endpoints; input length enforced
- `react-markdown` default settings; no `rehypeRaw`
- CSP headers on nginx: `default-src 'self'` minimum
- Conversation IDs generated via `crypto.randomUUID()`, never in URLs

## Definition of done for any task

1. `docker compose up` succeeds end-to-end
2. `/chat` handles multi-turn correctly across ≥ 2 documents
3. Telemetry row written for every interaction
4. Drift job runs without error: `python monitoring/drift_job/run_drift.py --trigger adhoc`
5. New code has at least one test
6. `code-reviewer` and `security-scanner` agents have reviewed
7. `ruff check .` and `pytest` pass
8. `npm run lint` and `npm run build` pass
9. Mobile emulation passes at 375px

## Roadmap (post-MVP, architecture must support these without rewrites)

- Cross-encoder reranker (`bge-reranker-v2-m3` via Ollama)
- Hybrid search (BM25 + vector)
- Context recall metric (requires golden answer set)
- Agentic tools: `search_regulations`, `summarise_section`, `compare_clauses`
- A/B testing harness: two prompt variants in parallel, compared via feedback
- RAGAS-based eval in CI (runs on PRs that touch RAG components)
- User auth via JWT
- Postgres migration path (SQLAlchemy schema is already Postgres-compatible)
