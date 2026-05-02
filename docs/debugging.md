# Debugging

Two common scenarios: debugging the **full stack** running under `docker compose`, and debugging **individual components** via Makefile targets before committing.

---

## Docker Compose stack

### Start the stack

```bash
docker compose up -d          # start all services in the background
docker compose up             # start with logs streaming to terminal (Ctrl-C stops all)
```

### View logs

```bash
# All services
docker compose logs -f

# Specific service only
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f chromadb
docker compose logs -f ollama
docker compose logs -f prometheus
docker compose logs -f grafana

# Last 100 lines then stream
docker compose logs --tail=100 -f backend
```

Services: `ollama`, `chromadb`, `backend`, `frontend`, `prometheus`, `grafana`, `pushgateway`.  
The `drift-job` service only starts when you run: `docker compose --profile drift run drift-job`.

### Check service health

```bash
docker compose ps          # shows Status (running / healthy / exiting)

# Manual health probes (same checks the containers run internally)
curl -f http://localhost:8000/health         # backend
curl -f http://localhost:8001/api/v1/heartbeat  # chromadb
curl -f http://localhost:11434/api/tags      # ollama
```

### Shell into a running container

```bash
# Backend (FastAPI / Python)
docker compose exec backend bash

# ChromaDB
docker compose exec chromadb bash

# Ollama
docker compose exec ollama bash

# Grafana
docker compose exec grafana bash
```

Once inside the backend container you can run Python interactively:

```bash
PYTHONPATH=/app python3
>>> from app.config import settings
>>> print(settings.model_dump())
```

Or inspect the SQLite telemetry database:

```bash
# Inside the backend container — telemetry volume is mounted at /app/telemetry
sqlite3 /app/telemetry/telemetry.db

sqlite> .tables
sqlite> SELECT * FROM messages ORDER BY created_at DESC LIMIT 5;
sqlite> SELECT metric_name, metric_value, breached FROM drift_runs ORDER BY run_at DESC LIMIT 10;
```

### Inspect volumes directly (without entering the container)

```bash
# Find the volume mount path on the host
docker volume inspect compliancecheckrag_telemetry_data

# One-liner to query the DB from the host (no shell needed)
docker compose exec backend sqlite3 /app/telemetry/telemetry.db \
  "SELECT role, substr(content,1,80) FROM messages ORDER BY created_at DESC LIMIT 5;"
```

### Restart a single service

```bash
docker compose restart backend

# Or rebuild and restart after a code change
docker compose up -d --build backend
```

### Tear down and clean up

```bash
docker compose down           # stop and remove containers (volumes preserved)
docker compose down -v        # also delete named volumes (wipes all data)
```

---

## Prometheus and Grafana

Prometheus scrapes the backend `/metrics` endpoint every 15s.

| URL | What it shows |
|---|---|
| `http://localhost:9090` | Prometheus query UI |
| `http://localhost:3000` | Grafana dashboards (admin / admin) |
| `http://localhost:9091` | Pushgateway — drift breach gauges |
| `http://localhost:8000/metrics` | Raw Prometheus exposition |

Useful PromQL queries for debugging:

```promql
# Request rate
rate(ccrag_query_total[5m])

# Error rate
rate(ccrag_query_total{status="error"}[5m])

# P95 retrieval latency
histogram_quantile(0.95, rate(ccrag_retrieval_latency_seconds_bucket[5m]))

# Active drift breaches
ccrag_drift_breach
```

---

## Makefile / local development

### Run lint before committing

```bash
make lint          # ruff check — prints offending lines with rule codes
make lint-fix      # ruff check --fix — auto-corrects safe violations
```

To check a specific file only:

```bash
.venv/bin/ruff check app/rag/retrieve.py
```

### Run tests before committing

```bash
make test          # Docker-based — guaranteed Python 3.11, matches CI exactly
make test-local    # Local venv — faster iteration, requires Python 3.11
```

Run a single test file or test function:

```bash
# Local venv
PYTHONPATH=. .venv/bin/pytest tests/test_telemetry.py -v

# Single test
PYTHONPATH=. .venv/bin/pytest tests/test_security.py::test_health_endpoint -v

# Show stdout (useful for print debugging during development)
PYTHONPATH=. .venv/bin/pytest tests/ -v -s

# Stop after first failure
PYTHONPATH=. .venv/bin/pytest tests/ -x
```

### Interactive Python REPL with app context

```bash
PYTHONPATH=. .venv/bin/python

>>> from app.config import settings
>>> from app.pii import mask
>>> mask("My email is alice@example.com")
```

### Run the backend manually (hot-reload)

```bash
make backend
# → uvicorn app.main:app --reload --port 8000
```

Then test endpoints with curl:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test-1","history":[],"message":"What is KYC?","doc_filter":null}'

# Inspect raw SSE stream
curl -N http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test-1","history":[],"message":"What is KYC?","doc_filter":null}'
```

### Run the ingestion pipeline manually

```bash
make ingest
# Runs: PYTHONPATH=. python -m app.rag.ingest
# Reads PDFs from data/, upserts into ChromaDB, generates llms-txt/
```

### Frontend checks

```bash
cd frontend && npm run lint      # ESLint (flat config, max-warnings 0)
cd frontend && npm run build     # Vite build — fails if gzip bundle > 200KB
cd frontend && npm run dev       # Dev server on http://localhost:5173
```

---

## Common failure patterns

### Backend container exits immediately

```bash
docker compose logs backend
```

Likely causes:
- **Missing `.env`** — copy from `.env.example` and fill in secrets
- **ChromaDB not ready** — backend starts before ChromaDB is healthy; add `depends_on` wait or rerun `docker compose up -d`
- **Ollama model not pulled** — `docker compose exec ollama ollama pull gemma3:1b`

### `greenlet` import error in tests

```
ModuleNotFoundError: No module named 'greenlet'
```

greenlet must be compiled against the exact Python version used. Run `make test` (Docker) instead of `make test-local`, or reinstall the venv:

```bash
make setup-backend
```

### ChromaDB connection refused

If the backend logs show `Connection refused` to ChromaDB:

```bash
# Check if chroma is actually healthy
docker compose ps chromadb
curl -f http://localhost:8001/api/v1/heartbeat
```

If running locally (not via Docker Compose), set `CHROMA_MODE=local` in `.env` so ChromaDB runs embedded.

### Ollama model not found

```bash
# List models currently loaded in the Ollama container
docker compose exec ollama ollama list

# Pull the required models
docker compose exec ollama ollama pull gemma3:1b
docker compose exec ollama ollama pull nomic-embed-text
```

### Ruff reports E402 (module import not at top)

Ensure module docstrings appear **before** `from __future__ import annotations`:

```python
# Correct order
"""Module docstring."""
from __future__ import annotations
import json
```

### Pre-commit hook fails on `requirements.in` change

The hook runs `make compile-deps` inside the dev container (requires Docker):

```bash
# See the full pip-compile error
make compile-deps

# Fix the constraint in requirements.in, then re-stage
git add requirements.in
git commit -m "Fix version constraint"
```

See [pre-commit-hook.md](pre-commit-hook.md) for detailed troubleshooting.
