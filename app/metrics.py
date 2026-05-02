from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

ccrag_query_total = Counter(
    "ccrag_query_total",
    "Total number of chat queries",
    ["status"],
)

ccrag_query_latency_seconds = Histogram(
    "ccrag_query_latency_seconds",
    "End-to-end query latency in seconds",
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

ccrag_retrieval_latency_seconds = Histogram(
    "ccrag_retrieval_latency_seconds",
    "ChromaDB retrieval latency in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2],
)

ccrag_llm_latency_seconds = Histogram(
    "ccrag_llm_latency_seconds",
    "Time to first token + full stream latency in seconds",
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

ccrag_chunks_retrieved = Histogram(
    "ccrag_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=[1, 2, 4, 6, 8, 10, 12],
)

ccrag_pii_hits_total = Counter(
    "ccrag_pii_hits_total",
    "Total PII entities detected and masked",
    ["entity_type"],
)

ccrag_conversation_turns = Histogram(
    "ccrag_conversation_turns",
    "Number of turns per conversation",
    buckets=[1, 2, 4, 8, 16, 32],
)

ccrag_feedback_total = Counter(
    "ccrag_feedback_total",
    "Total feedback submissions",
    ["rating"],
)

ccrag_drift_breach = Gauge(
    "ccrag_drift_breach",
    "1 if the named drift metric breached its threshold, 0 otherwise",
    ["metric_name"],
)
