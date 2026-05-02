---
description: Run the drift detection job — ad-hoc, post-deploy, or force a full quality eval
---

Trigger the drift detection pipeline outside of the nightly cron schedule.

## Usage

```bash
# Ad-hoc: analyse the last 24 hours
python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 24

# Post-deploy: compare post-deploy window against pre-deploy baseline
python monitoring/drift_job/run_drift.py --trigger ci --pipeline-version <git-sha>

# Force full quality eval (DeepEval) even if sample size is low
python monitoring/drift_job/run_drift.py --trigger adhoc --force-eval
```

## What the job does

1. Pull comparison window from `messages` table (last `--window-hours` hours)
2. Pull reference window (7 days prior to comparison window)
3. Check minimum sample size — warn if < 50, skip statistical tests if < 10
4. Run `retrieval_drift.py` — Evidently KS test on retrieval scores
5. Run `output_drift.py` — Evidently embedding drift + PSI on response length
6. Run `quality_eval.py` — DeepEval sample (up to 100 messages, deterministic seed)
7. Run `feedback_analysis.py` — thumbs ratio trend
8. Write results to `drift_runs` table
9. Push `ccrag_drift_breach` gauge to Prometheus Pushgateway for each breached metric
10. Print breach summary to stdout for CI log visibility

## Invoke this command when

- You've changed any of: embedding model, chunking strategy, prompt template, reranker, top-K
- You want to verify quality before a demo
- Grafana shows a sudden change in retrieval latency or feedback ratio
- After running `/ingest` with a new or updated document

## After running

Invoke the `drift-analyst` agent to interpret the results and recommend next steps.
