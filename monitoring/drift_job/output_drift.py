"""Embedding cosine drift and PSI on response length distribution.

Compares response embeddings from the last window_hours against a 7-day
reference. Alerts if mean pairwise cosine similarity drops by more than 0.05.
Also computes PSI on response_length distribution.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_THRESHOLD_COSINE_DROP = 0.05
_REFERENCE_HOURS = 168


def _load_embeddings(db_path: str, hours: int) -> list[list[float]]:
    """Load response embeddings from messages in the last N hours.

    Args:
        db_path: Path to the SQLite telemetry database.
        hours: How many hours back to query.

    Returns:
        List of float vectors decoded from BLOB columns.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT response_embedding FROM messages WHERE role='assistant' "
        f"AND response_embedding IS NOT NULL "
        f"AND created_at >= datetime('now', '-{hours} hours')"
    )
    vecs: list[list[float]] = []
    for (blob,) in cur.fetchall():
        if blob:
            n = len(blob) // 4
            vecs.append(list(struct.unpack(f"{n}f", blob)))
    con.close()
    return vecs


def _load_lengths(db_path: str, hours: int) -> list[int]:
    """Load response lengths from the last N hours.

    Args:
        db_path: Path to the SQLite database.
        hours: How many hours back to query.

    Returns:
        List of response_length integers.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        f"SELECT response_length FROM messages WHERE role='assistant' "
        f"AND response_length IS NOT NULL "
        f"AND created_at >= datetime('now', '-{hours} hours')"
    )
    lengths = [r[0] for r in cur.fetchall()]
    con.close()
    return lengths


def _mean_cosine_similarity(ref: list[list[float]], cur: list[list[float]]) -> float:
    """Compute mean pairwise cosine similarity between two sets of vectors.

    Samples min(len(ref), len(cur), 200) pairs to keep it tractable.

    Args:
        ref: Reference embedding vectors.
        cur: Current window embedding vectors.

    Returns:
        Mean cosine similarity as a float in [-1, 1].
    """
    import random

    import numpy as np

    n = min(len(ref), len(cur), 200)
    ref_sample = random.sample(ref, n)
    cur_sample = random.sample(cur, n)

    ref_arr = np.array(ref_sample, dtype=np.float32)
    cur_arr = np.array(cur_sample, dtype=np.float32)

    # Normalise
    ref_norms = np.linalg.norm(ref_arr, axis=1, keepdims=True) + 1e-9
    cur_norms = np.linalg.norm(cur_arr, axis=1, keepdims=True) + 1e-9
    sims = np.sum((ref_arr / ref_norms) * (cur_arr / cur_norms), axis=1)
    return float(np.mean(sims))


def _psi(reference: list[int], current: list[int], bins: int = 10) -> float:
    """Compute Population Stability Index between two distributions.

    Args:
        reference: Reference distribution samples.
        current: Current distribution samples.
        bins: Number of histogram bins.

    Returns:
        PSI value (0 = identical, > 0.2 = significant shift).
    """
    import numpy as np

    all_vals = reference + current
    bin_edges = np.histogram_bin_edges(all_vals, bins=bins)

    ref_hist, _ = np.histogram(reference, bins=bin_edges)
    cur_hist, _ = np.histogram(current, bins=bin_edges)

    ref_pct = (ref_hist + 1e-6) / (sum(ref_hist) + 1e-6 * bins)
    cur_pct = (cur_hist + 1e-6) / (sum(cur_hist) + 1e-6 * bins)

    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def _write_drift_run(
    db_path: str,
    triggered_by: str,
    pipeline_version: str | None,
    window_hours: int,
    metric_name: str,
    metric_value: float,
    threshold: float,
    breached: bool,
    details: dict,
) -> None:
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
            metric_name,
            metric_value,
            threshold,
            int(breached),
            json.dumps(details),
        ),
    )
    con.commit()
    con.close()


def run(triggered_by: str, pipeline_version: str | None, window_hours: int) -> bool:
    """Run output embedding drift and response length PSI checks.

    Args:
        triggered_by: 'cron' | 'ci' | 'adhoc'.
        pipeline_version: Git SHA or None.
        window_hours: Current evaluation window in hours.

    Returns:
        True if any breach was detected, False otherwise.
    """
    db_path = "telemetry.db"
    if not Path(db_path).exists():
        logger.warning("No telemetry.db — skipping output drift check.")
        return False

    breached = False

    # 1. Cosine similarity drift on response embeddings
    ref_embeddings = _load_embeddings(db_path, _REFERENCE_HOURS)
    cur_embeddings = _load_embeddings(db_path, window_hours)

    if len(ref_embeddings) >= 10 and len(cur_embeddings) >= 10:
        sim = _mean_cosine_similarity(ref_embeddings, cur_embeddings)
        ref_sim = _mean_cosine_similarity(ref_embeddings, ref_embeddings[:len(ref_embeddings)//2])
        drop = ref_sim - sim
        cosine_breached = drop > _THRESHOLD_COSINE_DROP

        logger.info(
            "Output drift — cosine similarity=%.4f drop=%.4f threshold=%.2f breached=%s",
            sim, drop, _THRESHOLD_COSINE_DROP, cosine_breached,
        )
        _write_drift_run(
            db_path, triggered_by, pipeline_version, window_hours,
            "output_cosine_similarity_drop", drop, _THRESHOLD_COSINE_DROP, cosine_breached,
            {"mean_similarity": sim, "ref_self_similarity": ref_sim},
        )
        if cosine_breached:
            logger.warning("OUTPUT DRIFT BREACH: cosine drop=%.4f", drop)
            breached = True
    else:
        logger.info("Insufficient embeddings for cosine drift check — skipping.")

    # 2. PSI on response length
    ref_lengths = _load_lengths(db_path, _REFERENCE_HOURS)
    cur_lengths = _load_lengths(db_path, window_hours)

    if len(ref_lengths) >= 10 and len(cur_lengths) >= 10:
        psi_val = _psi(ref_lengths, cur_lengths)
        psi_breached = psi_val > 0.2
        logger.info(
            "Response length PSI=%.4f threshold=0.2 breached=%s", psi_val, psi_breached
        )
        _write_drift_run(
            db_path, triggered_by, pipeline_version, window_hours,
            "response_length_psi", psi_val, 0.2, psi_breached,
            {"ref_n": len(ref_lengths), "cur_n": len(cur_lengths)},
        )
        if psi_breached:
            logger.warning("RESPONSE LENGTH DRIFT: PSI=%.4f", psi_val)
            breached = True

    return breached
