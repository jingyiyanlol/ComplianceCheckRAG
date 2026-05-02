from __future__ import annotations

"""Feedback thumbs-down ratio trend analysis.

Compares the thumbs-down ratio from the last window_hours against the 7-day
baseline. Alerts if the ratio doubles.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_REFERENCE_HOURS = 168  # 7 days


def _load_ratio(db_path: str, hours: int) -> tuple[float | None, int]:
    """Compute thumbs-down ratio over a time window.

    Args:
        db_path: Path to the SQLite telemetry database.
        hours: How many hours back to query.

    Returns:
        Tuple of (ratio, total_count). ratio is None if no feedback exists.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT COUNT(*) FROM feedback WHERE rating=-1 "
        f"AND created_at >= datetime('now', '-{hours} hours')"
    )
    downs = cur.fetchone()[0] or 0
    cur.execute(
        f"SELECT COUNT(*) FROM feedback WHERE created_at >= datetime('now', '-{hours} hours')"
    )
    total = cur.fetchone()[0] or 0
    con.close()
    ratio = downs / total if total > 0 else None
    return ratio, total


def _load_negative_comments(db_path: str, hours: int, limit: int = 5) -> list[dict]:
    """Load the most recent negative feedback comments.

    Args:
        db_path: Path to the SQLite telemetry database.
        hours: How many hours back to query.
        limit: Maximum number of comments to return.

    Returns:
        List of dicts with keys: message_id, comment, created_at.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT message_id, comment, created_at FROM feedback "
        f"WHERE rating=-1 AND comment IS NOT NULL "
        f"AND created_at >= datetime('now', '-{hours} hours') "
        f"ORDER BY created_at DESC LIMIT {limit}"
    )
    rows = cur.fetchall()
    con.close()
    return [{"message_id": r[0], "comment": r[1], "created_at": r[2]} for r in rows]


def run(triggered_by: str, pipeline_version: str | None, window_hours: int) -> bool:
    """Analyse feedback thumbs-down ratio trend.

    Args:
        triggered_by: 'cron' | 'ci' | 'adhoc'.
        pipeline_version: Git SHA or None.
        window_hours: Evaluation window in hours.

    Returns:
        True if the thumbs-down ratio has doubled versus baseline.
    """
    db_path = "telemetry.db"
    if not Path(db_path).exists():
        logger.warning("No telemetry.db — skipping feedback analysis.")
        return False

    current_ratio, current_total = _load_ratio(db_path, window_hours)
    baseline_ratio, baseline_total = _load_ratio(db_path, _REFERENCE_HOURS)

    if current_ratio is None or baseline_ratio is None:
        logger.info(
            "Insufficient feedback data (current_n=%d, baseline_n=%d) — skipping.",
            current_total, baseline_total,
        )
        return False

    breached = baseline_ratio > 0 and current_ratio >= baseline_ratio * 2

    logger.info(
        "Feedback analysis — current_ratio=%.3f baseline_ratio=%.3f breached=%s",
        current_ratio, baseline_ratio, breached,
    )

    # Persist result
    con = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        """
        INSERT INTO drift_runs
        (id, triggered_by, pipeline_version, run_at, window_start, window_end,
         metric_name, metric_value, threshold, breached, details)
        VALUES (?,?,?,?,datetime('now',?),?,?,?,?,?,?)
        """,
        (
            str(uuid.uuid4()),
            triggered_by,
            pipeline_version,
            now,
            f"-{window_hours} hours",
            now,
            "feedback_thumbsdown_ratio",
            current_ratio,
            baseline_ratio * 2 if baseline_ratio else 0,
            int(breached),
            json.dumps({
                "current_total": current_total,
                "baseline_total": baseline_total,
                "baseline_ratio": baseline_ratio,
            }),
        ),
    )
    con.commit()
    con.close()

    if breached:
        logger.warning(
            "FEEDBACK BREACH: thumbs-down ratio doubled (%.3f vs baseline %.3f)",
            current_ratio, baseline_ratio,
        )
        comments = _load_negative_comments(db_path, window_hours)
        if comments:
            logger.warning("Top negative comments:")
            for c in comments:
                logger.warning("  [%s] %s", c["created_at"], c["comment"])

    return breached
