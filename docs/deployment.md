# Deployment

## Local development (dev container)

The recommended local setup uses a Docker dev container so the Python and Node versions are pinned and identical across all machines. See the main [README](../README.md#quickstart) for the three setup options (VS Code, CLI, Docker Compose).

---

## Docker Compose — full local stack

Starts all services including ChromaDB, Prometheus, Grafana, and Pushgateway.

```bash
cp .env.example .env   # edit if needed
docker compose up -d
docker compose exec backend python -m app.rag.ingest
```

Services:

| Service | URL | Notes |
|---|---|---|
| backend | http://localhost:8000 | FastAPI, hot-reload not available in Compose |
| frontend | http://localhost:5173 | Nginx serving the built React app |
| chromadb | http://localhost:8001 | Vector DB |
| prometheus | http://localhost:9090 | Scrapes `/metrics` every 15s |
| grafana | http://localhost:3000 | admin / admin — dashboards auto-provisioned |
| pushgateway | http://localhost:9091 | Receives drift breach gauges from the drift job |

### Running the drift job

```bash
# One-off run against the Compose stack
docker compose --profile drift run drift-job

# Or directly with the drift container image
docker compose run --rm drift-job python monitoring/drift_job/run_drift.py \
  --trigger adhoc --window-hours 24
```

---

## Environment variables

All settings are read from `.env` via `app/config.py` (pydantic-settings). Copy `.env.example` and edit as needed.

| Variable | Local default | Docker/K8s default | Description |
|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` | Ollama server URL |
| `LLM_MODEL` | `gemma3:1b` | `gemma3:1b` | Model for generation and query rewriting |
| `EMBED_MODEL` | `nomic-embed-text` | `nomic-embed-text` | Embedding model |
| `CHROMA_MODE` | `local` | `http` | `local` = on-disk PersistentClient; `http` = server |
| `CHROMA_LOCAL_PATH` | `.chroma` | — | On-disk ChromaDB path (local mode only) |
| `CHROMA_HOST` | `localhost` | `chromadb` | ChromaDB host (http mode only) |
| `CHROMA_PORT` | `8001` | `8000` | ChromaDB port (http mode only) |
| `CHROMA_AUTH_TOKEN` | _(empty)_ | _(empty)_ | Optional bearer token for ChromaDB |
| `CHROMA_COLLECTION` | `compliance_docs` | `compliance_docs` | Collection name |
| `TELEMETRY_DB_PATH` | `telemetry.db` | `/telemetry/telemetry.db` | SQLite path (K8s uses a PVC) |
| `LOG_LEVEL` | `INFO` | `INFO` | Python logging level |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | your domain | CORS allowed origin |

---

## Kubernetes

Manifests are in `k8s/`. They assume a namespace `ccrag` and a container registry at GHCR (images built and pushed by GitHub Actions CI).

```bash
# Deploy all services
kubectl apply -f k8s/manifests.yaml

# Deploy nightly drift CronJob (runs at 02:00)
kubectl apply -f k8s/cronjob-drift.yaml
```

### What the manifests include

- `Namespace` — `ccrag`
- `ConfigMap` — non-secret environment variables
- `Secret` — `CHROMA_AUTH_TOKEN` and any other secrets (fill in before applying)
- `Deployment` + `Service` for: backend, frontend, chromadb, ollama, prometheus, grafana, pushgateway
- `PersistentVolumeClaim` for: Ollama model weights, ChromaDB data, Prometheus data, Grafana data, telemetry SQLite

### Drift CronJob

`k8s/cronjob-drift.yaml` runs `run_drift.py --trigger cron` nightly at 02:00. It mounts the telemetry PVC **read-only** to query the SQLite database, and pushes breach gauges to Pushgateway (read-write access not required).

---

## CI/CD (GitHub Actions)

### Backend CI (`.github/workflows/backend-ci.yml`)

Triggers on push and PR to `main`.

1. **lint-test**: ruff check + pytest on Python 3.11
2. **build-push**: builds `Dockerfile`, pushes to GHCR as `ghcr.io/<repo>/backend:latest` and `:<sha>`
3. **drift-check**: runs automatically when `app/rag/`, `app/llm.py`, or `docker-compose.yml` changes — captures a baseline snapshot before the build and runs a post-deploy drift comparison after

### Frontend CI (`.github/workflows/frontend-ci.yml`)

Triggers on push and PR to `main`.

1. **lint-build**: `npm run lint` + `npm run build` on Node 24
2. **Bundle size check**: gzipped JS must be under 200KB
3. **build-push**: builds `frontend/Dockerfile`, pushes to GHCR

Both workflows set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to opt into Node 24 for GitHub-managed action runners ahead of the June 2026 forced migration.

---

## Docker images

| Image | Base | Purpose |
|---|---|---|
| `Dockerfile` | `python:3.11-slim` | Backend — non-root `raguser`, uvicorn entrypoint |
| `frontend/Dockerfile` | `node:24-slim` build → `nginx:1.27-alpine` runtime | Frontend — CSP headers, no server-side code |
| `Dockerfile.drift` | `python:3.11-slim` | Drift job — drift deps only, no app code |
| `.devcontainer/Dockerfile` | `python:3.11-slim` | Dev environment — Node 24, pip-tools, non-root `dev` user |

All production images run as non-root users.
