"""Capture a pre-deploy baseline snapshot of pipeline quality metrics.

Run this BEFORE deploying any change to the RAG pipeline so the post-deploy
drift job has a reference window to compare against.

Usage:
    python monitoring/drift_job/snapshot.py --pipeline-version $(git rev-parse --short HEAD)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MARKER_PATH = Path("monitoring/drift_job/last_snapshot.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list; defaults to sys.argv.

    Returns:
        Parsed namespace with pipeline_version and window_hours.
    """
    parser = argparse.ArgumentParser(description="Capture a baseline quality snapshot.")
    parser.add_argument(
        "--pipeline-version",
        required=True,
        help="Git SHA or tag to label this snapshot.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=168,
        help="How many hours of history to include in the snapshot (default: 168 = 7 days).",
    )
    return parser.parse_args(argv)


def _compute_snapshot(pipeline_version: str, window_hours: int) -> dict:
    """Query the telemetry DB and compute summary stats for the snapshot.

    Args:
        pipeline_version: Label for this snapshot.
        window_hours: Window of recent messages to include.

    Returns:
        Dict matching the baseline_snapshots table schema.
    """
    import sqlite3
    from pathlib import Path

    db_path = Path("telemetry.db")
    if not db_path.exists():
        logger.warning("No telemetry.db found — snapshot will have null metric values.")
        return {
            "id": str(uuid.uuid4()),
            "pipeline_version": pipeline_version,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "retrieval_score_p50": None,
            "retrieval_score_p95": None,
            "response_length_p50": None,
            "faithfulness_mean": None,
            "answer_relevance_mean": None,
            "context_precision_mean": None,
            "feedback_thumbsdown_ratio": None,
            "sample_size": 0,
        }

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cutoff = f"datetime('now', '-{window_hours} hours')"

    # Retrieval scores (top-1 from each message's retrieved_chunks JSON)
    cur.execute(
        f"SELECT retrieved_chunks FROM messages WHERE role='assistant' AND created_at >= {cutoff}"
    )
    scores: list[float] = []
    lengths: list[int] = []
    for (chunks_json,) in cur.fetchall():
        if chunks_json:
            try:
                chunks = json.loads(chunks_json)
                if chunks:
                    scores.append(float(chunks[0].get("score", 0)))
            except (json.JSONDecodeError, KeyError):
                pass

    cur.execute(
        f"SELECT response_length FROM messages WHERE role='assistant' AND created_at >= {cutoff}"
    )
    lengths = [r[0] for r in cur.fetchall() if r[0] is not None]

    # DeepEval means from eval_results
    def _mean(metric: str) -> float | None:
        cur.execute(
            "SELECT AVG(score) FROM eval_results WHERE metric_name=? "
            f"AND created_at >= {cutoff}",
            (metric,),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None

    # Feedback thumbs-down ratio
    cur.execute(
        f"SELECT COUNT(*) FROM feedback WHERE rating=-1 AND created_at >= {cutoff}"
    )
    downs = cur.fetchone()[0] or 0
    cur.execute(f"SELECT COUNT(*) FROM feedback WHERE created_at >= {cutoff}")
    total_fb = cur.fetchone()[0] or 0
    thumbsdown_ratio = downs / total_fb if total_fb > 0 else None

    con.close()

    def _percentile(data: list[float], p: float) -> float | None:
        if not data:
            return None
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    return {
        "id": str(uuid.uuid4()),
        "pipeline_version": pipeline_version,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_score_p50": _percentile(scores, 50),
        "retrieval_score_p95": _percentile(scores, 95),
        "response_length_p50": _percentile(lengths, 50),  # type: ignore[arg-type]
        "faithfulness_mean": _mean("faithfulness"),
        "answer_relevance_mean": _mean("answer_relevance"),
        "context_precision_mean": _mean("context_precision"),
        "feedback_thumbsdown_ratio": thumbsdown_ratio,
        "sample_size": len(scores),
    }


def main(argv: list[str] | None = None) -> int:
    """Capture and persist a baseline snapshot.

    Args:
        argv: Optional argument list for testing.

    Returns:
        0 on success.
    """
    logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)

    snapshot = _compute_snapshot(args.pipeline_version, args.window_hours)

    # Write to DB
    try:
        import sqlite3

        con = sqlite3.connect("telemetry.db")
        con.execute(
            """
            INSERT OR REPLACE INTO baseline_snapshots
            (id, pipeline_version, captured_at, retrieval_score_p50, retrieval_score_p95,
             response_length_p50, faithfulness_mean, answer_relevance_mean,
             context_precision_mean, feedback_thumbsdown_ratio, sample_size)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                snapshot["id"],
                snapshot["pipeline_version"],
                snapshot["captured_at"],
                snapshot["retrieval_score_p50"],
                snapshot["retrieval_score_p95"],
                snapshot["response_length_p50"],
                snapshot["faithfulness_mean"],
                snapshot["answer_relevance_mean"],
                snapshot["context_precision_mean"],
                snapshot["feedback_thumbsdown_ratio"],
                snapshot["sample_size"],
            ),
        )
        con.commit()
        con.close()
    except Exception:
        logger.exception("Failed to write snapshot to DB")

    # Write marker file so the drift job knows a baseline exists
    _MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MARKER_PATH.write_text(json.dumps(snapshot, indent=2))
    logger.info(
        "Baseline snapshot captured: version=%s sample_size=%d",
        args.pipeline_version,
        snapshot["sample_size"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
