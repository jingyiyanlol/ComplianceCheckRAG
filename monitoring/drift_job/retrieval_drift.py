"""Evidently KS test on retrieval score distributions.

Compares top-1 retrieval scores from the last window_hours against a 7-day
reference window. Alerts if Kolmogorov-Smirnov p-value < 0.01.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_THRESHOLD_PVALUE = 0.01
_REFERENCE_HOURS = 168  # 7 days


def _load_scores(db_path: str, hours: int) -> list[float]:
    """Load top-1 retrieval scores from messages in the last N hours.

    Args:
        db_path: Path to the SQLite telemetry database.
        hours: How many hours back to query.

    Returns:
        List of top-1 retrieval score floats.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT retrieved_chunks FROM messages WHERE role='assistant' "
        f"AND created_at >= datetime('now', '-{hours} hours')"
    )
    scores: list[float] = []
    for (chunks_json,) in cur.fetchall():
        if chunks_json:
            try:
                chunks = json.loads(chunks_json)
                if chunks:
                    scores.append(float(chunks[0].get("score", 0)))
            except (json.JSONDecodeError, KeyError):
                pass
    con.close()
    return scores


def _write_drift_run(
    db_path: str,
    triggered_by: str,
    pipeline_version: str | None,
    window_hours: int,
    metric_value: float,
    breached: bool,
    details: dict,
) -> None:
    """Persist a drift_runs row.

    Args:
        db_path: Path to telemetry SQLite DB.
        triggered_by: 'cron' | 'ci' | 'adhoc'.
        pipeline_version: Git SHA or None.
        window_hours: Current window size.
        metric_value: KS p-value.
        breached: Whether the threshold was exceeded.
        details: Extra detail dict (stored as JSON).
    """
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
            "retrieval_ks_pvalue",
            metric_value,
            _THRESHOLD_PVALUE,
            int(breached),
            json.dumps(details),
        ),
    )
    con.commit()
    con.close()


def run(triggered_by: str, pipeline_version: str | None, window_hours: int) -> bool:
    """Run Evidently-style KS test on retrieval score distributions.

    Args:
        triggered_by: 'cron' | 'ci' | 'adhoc'.
        pipeline_version: Git SHA or None.
        window_hours: Size of the current evaluation window in hours.

    Returns:
        True if a drift breach was detected, False otherwise.
    """
    from scipy import stats

    db_path = "telemetry.db"
    if not Path(db_path).exists():
        logger.warning("No telemetry.db — skipping retrieval drift check.")
        return False

    current = _load_scores(db_path, window_hours)
    reference = _load_scores(db_path, _REFERENCE_HOURS)

    if len(current) < 10 or len(reference) < 10:
        logger.info(
            "Insufficient data for KS test (current=%d, reference=%d) — skipping.",
            len(current),
            len(reference),
        )
        return False

    stat, pvalue = stats.ks_2samp(reference, current)
    breached = pvalue < _THRESHOLD_PVALUE

    logger.info(
        "Retrieval drift — KS stat=%.4f p=%.4f threshold=%.2f breached=%s",
        stat, pvalue, _THRESHOLD_PVALUE, breached,
    )

    _write_drift_run(
        db_path,
        triggered_by,
        pipeline_version,
        window_hours,
        metric_value=pvalue,
        breached=breached,
        details={"ks_statistic": stat, "current_n": len(current), "reference_n": len(reference)},
    )

    if breached:
        logger.warning(
            "RETRIEVAL DRIFT BREACH: KS p=%.4f < threshold=%.2f", pvalue, _THRESHOLD_PVALUE
        )

    return breached
