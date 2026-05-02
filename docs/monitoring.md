# Monitoring

The monitoring stack has three layers: real-time Prometheus metrics, per-request SQLite telemetry, and a scheduled drift detection job.

---

## Layer 1 — App performance (Prometheus + Grafana)

### Metrics endpoint

`GET /metrics` exposes all Prometheus metrics. Scraped by Prometheus every 15 seconds.

### Custom metrics (`app/metrics.py`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `ccrag_query_total` | Counter | `status` | Total chat requests by outcome (`success`, `error`) |
| `ccrag_query_latency_seconds` | Histogram | — | End-to-end request latency |
| `ccrag_retrieval_latency_seconds` | Histogram | — | ChromaDB query latency |
| `ccrag_llm_latency_seconds` | Histogram | — | Ollama generation latency |
| `ccrag_chunks_retrieved` | Histogram | — | Number of chunks returned per query |
| `ccrag_pii_hits_total` | Counter | `entity_type` | PII detections by Presidio entity type |
| `ccrag_conversation_turns` | Histogram | — | Number of turns per conversation at log time |
| `ccrag_feedback_total` | Counter | `rating` | Thumbs up/down counts |
| `ccrag_drift_breach` | Gauge | `metric_name` | Set to 1 by drift job when a threshold is breached |

### Grafana dashboards

Access Grafana at http://localhost:3000 (admin / admin for local dev).

**App Performance dashboard** — real-time operational health:
- Request rate and error rate
- Latency histograms: retrieval, LLM, total
- PII hit counter by entity type
- Conversation turn distribution

**Model Quality dashboard** — RAG quality signals:
- Faithfulness / answer relevance / context precision trends (from `eval_results` table)
- Feedback thumbs-down ratio over time
- Retrieval score distribution
- Drift breach gauge (sourced from `ccrag_drift_breach` pushed by the drift job)

---

## Layer 2 — Per-request telemetry (SQLite)

Every `/chat` request writes one row to the `messages` table after streaming completes. The write is **non-blocking** — scheduled via `asyncio.create_task()` so it never adds latency to the response.

Key columns logged:

| Column | What it captures |
|---|---|
| `rewritten_query` | Output of the multi-turn query rewriter |
| `retrieved_chunks` | JSON array of `{chunk_id, score, doc_name, section}` |
| `retrieval_latency_ms` | ChromaDB query time |
| `llm_latency_ms` | Ollama streaming time |
| `response_embedding` | float32 BLOB — used by `output_drift.py` |
| `query_embedding` | float32 BLOB — used for query distribution drift |
| `pii_entities_found` | JSON array of detected entity types |

Raw events only — nothing is pre-aggregated at write time.

---

## Layer 3 — Drift detection job

### Trigger modes

```bash
# Ad-hoc (any time)
python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 24

# Nightly (K8s CronJob at 02:00, or Docker Compose profile)
python monitoring/drift_job/run_drift.py --trigger cron
docker compose --profile drift run drift-job

# Post-deploy CI (after RAG path changes)
python monitoring/drift_job/run_drift.py --trigger ci --pipeline-version $GITHUB_SHA
```

### Sub-jobs

#### `retrieval_drift.py` — retrieval score distribution
- Pulls top-1 retrieval scores from the last 24h vs a 7-day reference window
- Runs Kolmogorov-Smirnov test (Evidently) on the two distributions
- **Alert threshold**: p-value < 0.01
- **Triggered by**: embedding model change, chunking strategy change, top-K change

#### `output_drift.py` — response embedding drift
- Pulls `response_embedding` BLOBs from the last 24h vs reference window
- Computes mean pairwise cosine similarity between windows
- Also runs PSI (Population Stability Index) on response length distribution
- **Alert threshold**: mean similarity drop > 0.05
- **Triggered by**: LLM model change, prompt template change

#### `quality_eval.py` — LLM-as-judge evaluation
- Samples up to 100 messages from the last 24h
- For each, runs three DeepEval metrics using `gemma3:1b` as the local judge (no API key):
  - **Faithfulness**: is the response grounded in the retrieved chunks?
  - **Answer relevance**: does the response address the rewritten query?
  - **Context precision**: of retrieved chunks, how many contributed to the response?
- Writes scores to the `eval_results` table
- **Alert thresholds**: faithfulness < 0.7 or answer relevance < 0.65
- **Triggered by**: any change to generation prompt, LLM model, or retrieval strategy

#### `feedback_analysis.py` — user feedback signals
- Computes thumbs-down ratio for the last 24h vs 7-day baseline
- Surfaces the 5 most recent negative comments for human review
- **Alert threshold**: ratio doubles between windows

### Results and alerting

All sub-jobs write to the `drift_runs` table:

```sql
drift_runs(id, triggered_by, pipeline_version, run_at,
           window_start, window_end, metric_name,
           metric_value, threshold, breached, details)
```

On breach, they push `ccrag_drift_breach{metric_name=...} = 1` to Prometheus Pushgateway. Grafana's Model Quality dashboard surfaces this as a gauge panel.

### Pre-deploy baseline snapshot

Before deploying a pipeline change (new embedding model, different chunking, reranker), capture a reference window:

```bash
python monitoring/drift_job/snapshot.py --pipeline-version $(git rev-parse HEAD)
```

This writes to `baseline_snapshots` and is used by the post-deploy CI drift run to compare against. The CI workflow does this automatically when `app/rag/`, `app/llm.py`, or `docker-compose.yml` changes.

---

## Which metric catches which change

| Pipeline change | Primary signals | Detection method |
|---|---|---|
| Embedding model swapped | Retrieval score distribution | Evidently KS test |
| Chunking strategy changed | Context precision, retrieval score variance | DeepEval + Evidently |
| Top-K changed | Context precision, response length | DeepEval |
| Prompt template changed | Faithfulness, answer relevance | DeepEval |
| LLM model changed | All generation metrics | Full DeepEval suite |
| Bad data ingested | Retrieval scores drop, user thumbs-down spikes | KS test + feedback ratio |
