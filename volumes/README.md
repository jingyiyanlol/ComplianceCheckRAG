# Persistent Volumes

This directory contains local persistent volumes for Docker Compose services. Data in these directories persists across `docker compose down` and `docker compose up` cycles.

## Structure

| Directory | Service | Content | Purpose |
|-----------|---------|---------|---------|
| `ollama/` | Ollama | Downloaded LLM models | Model weights (gemma3:1b, nomic-embed-text) |
| `chromadb/` | ChromaDB | Vector database | Ingested document embeddings and metadata |
| `telemetry/` | Backend | SQLite database | Conversation history, feedback, eval results, drift metrics |
| `prometheus/` | Prometheus | Time-series metrics | Performance metrics, latency, error rates |
| `grafana/` | Grafana | Dashboard config | Saved dashboards, panel layouts, user preferences |

## Backup

To backup all persistent data:

```bash
tar -czf ccrag-data-$(date +%Y%m%d-%H%M%S).tar.gz volumes/
```

To restore from backup:

```bash
tar -xzf ccrag-data-*.tar.gz
docker compose up -d
```

## Cleanup

To reset all data and start fresh:

```bash
docker compose down -v
rm -rf volumes/*
docker compose up -d
```

This will:
1. Stop and remove all containers
2. Delete the data directories
3. Re-download Ollama models on next startup
4. Re-initialize ChromaDB
5. Fresh telemetry and monitoring data

## Size

Monitor disk usage with:

```bash
du -sh volumes/*/
```

Typical sizes:
- ollama: 1-2 GB (model weights)
- chromadb: varies (depends on ingested documents)
- telemetry: grows over time (depends on usage)
- prometheus: grows over time (depends on retention)
- grafana: small (< 100 MB)
