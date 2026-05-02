"""DeepEval quality evaluation using a local Ollama judge.

Samples up to 100 assistant messages from the last window_hours, runs
faithfulness, answer relevance, and context precision metrics, and writes
scores to the eval_results table.
"""

from __future__ import annotations

import json
import logging
import random
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SAMPLE_SIZE = 100
_THRESHOLD_FAITHFULNESS = 0.7
_THRESHOLD_ANSWER_RELEVANCE = 0.65
_THRESHOLD_CONTEXT_PRECISION = 0.6


def _load_messages(db_path: str, hours: int) -> list[dict]:
    """Load sampled assistant messages with their context for evaluation.

    Args:
        db_path: Path to the SQLite telemetry database.
        hours: Evaluation window in hours.

    Returns:
        List of message dicts with keys: id, content, rewritten_query, retrieved_chunks.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT id, content, rewritten_query, retrieved_chunks FROM messages "
        f"WHERE role='assistant' AND rewritten_query IS NOT NULL "
        f"AND created_at >= datetime('now', '-{hours} hours')"
    )
    rows = cur.fetchall()
    con.close()

    messages = [
        {
            "id": r[0],
            "content": r[1],
            "rewritten_query": r[2],
            "retrieved_chunks": json.loads(r[3]) if r[3] else [],
        }
        for r in rows
    ]
    if len(messages) > _SAMPLE_SIZE:
        messages = random.sample(messages, _SAMPLE_SIZE)
    return messages


def _write_eval_result(
    db_path: str,
    message_id: str,
    run_id: str,
    metric_name: str,
    score: float,
    reason: str | None,
) -> None:
    """Write a single eval result row to the database.

    Args:
        db_path: Path to the SQLite DB.
        message_id: The message being evaluated.
        run_id: UUID shared across all metrics in this drift run.
        metric_name: e.g. 'faithfulness', 'answer_relevance', 'context_precision'.
        score: Metric score in [0, 1].
        reason: Optional LLM judge reasoning text.
    """
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO eval_results (id, message_id, run_id, metric_name, score, reason, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            message_id,
            run_id,
            metric_name,
            score,
            reason,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    con.commit()
    con.close()


def run(triggered_by: str, pipeline_version: str | None, window_hours: int) -> bool:
    """Sample messages and run DeepEval quality metrics with a local Ollama judge.

    Args:
        triggered_by: 'cron' | 'ci' | 'adhoc'.
        pipeline_version: Git SHA or None.
        window_hours: Evaluation window in hours.

    Returns:
        True if mean faithfulness or answer relevance breached thresholds.
    """
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        FaithfulnessMetric,
    )
    from deepeval.models import OllamaModel
    from deepeval.test_case import LLMTestCase

    db_path = "telemetry.db"
    if not Path(db_path).exists():
        logger.warning("No telemetry.db — skipping quality eval.")
        return False

    messages = _load_messages(db_path, window_hours)
    if not messages:
        logger.info("No messages to evaluate in the window.")
        return False

    logger.info("Running DeepEval on %d sampled messages...", len(messages))
    run_id = str(uuid.uuid4())

    judge_model = OllamaModel(model="gemma3:1b")
    faithfulness_metric = FaithfulnessMetric(
        threshold=_THRESHOLD_FAITHFULNESS, model=judge_model, include_reason=True
    )
    relevance_metric = AnswerRelevancyMetric(
        threshold=_THRESHOLD_ANSWER_RELEVANCE, model=judge_model
    )
    precision_metric = ContextualPrecisionMetric(
        threshold=_THRESHOLD_CONTEXT_PRECISION, model=judge_model
    )

    scores: dict[str, list[float]] = {
        "faithfulness": [],
        "answer_relevance": [],
        "context_precision": [],
    }

    for msg in messages:
        context = [c.get("chunk_id", "") for c in msg["retrieved_chunks"]]
        test_case = LLMTestCase(
            input=msg["rewritten_query"],
            actual_output=msg["content"],
            retrieval_context=context,
            expected_output=None,
        )
        try:
            faithfulness_metric.measure(test_case)
            _write_eval_result(
                db_path, msg["id"], run_id, "faithfulness",
                faithfulness_metric.score, getattr(faithfulness_metric, "reason", None),
            )
            scores["faithfulness"].append(faithfulness_metric.score)

            relevance_metric.measure(test_case)
            _write_eval_result(
                db_path, msg["id"], run_id, "answer_relevance",
                relevance_metric.score, None,
            )
            scores["answer_relevance"].append(relevance_metric.score)

            precision_metric.measure(test_case)
            _write_eval_result(
                db_path, msg["id"], run_id, "context_precision",
                precision_metric.score, None,
            )
            scores["context_precision"].append(precision_metric.score)

        except Exception:
            logger.exception("DeepEval failed for message %s — skipping", msg["id"])

    breached = False
    for metric, values in scores.items():
        if not values:
            continue
        mean = sum(values) / len(values)
        threshold = {
            "faithfulness": _THRESHOLD_FAITHFULNESS,
            "answer_relevance": _THRESHOLD_ANSWER_RELEVANCE,
            "context_precision": _THRESHOLD_CONTEXT_PRECISION,
        }[metric]
        is_breached = mean < threshold
        logger.info("Quality eval — %s mean=%.3f threshold=%.2f breached=%s", metric, mean, threshold, is_breached)
        if is_breached:
            logger.warning("QUALITY BREACH: %s mean=%.3f < threshold=%.2f", metric, mean, threshold)
            breached = True

    return breached
