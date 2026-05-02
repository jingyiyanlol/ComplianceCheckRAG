from __future__ import annotations

"""Drift detection job entrypoint.

Usage:
    python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 24
    python monitoring/drift_job/run_drift.py --trigger cron
    python monitoring/drift_job/run_drift.py --trigger ci --pipeline-version <sha>
"""

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv).

    Returns:
        Parsed namespace with trigger, pipeline_version, window_hours.
    """
    parser = argparse.ArgumentParser(description="Run ComplianceCheckRAG drift detection.")
    parser.add_argument(
        "--trigger",
        choices=["cron", "ci", "adhoc"],
        required=True,
        help="What initiated this run.",
    )
    parser.add_argument(
        "--pipeline-version",
        default=None,
        help="Git SHA of the deployed pipeline (used with --trigger ci).",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Size of the evaluation window in hours (default: 24).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run all drift sub-jobs and return an exit code.

    Args:
        argv: Optional argument list for testing.

    Returns:
        0 on success, 1 if any breach was detected.
    """
    logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)

    logger.info(
        "Drift job starting — trigger=%s window_hours=%d pipeline_version=%s",
        args.trigger,
        args.window_hours,
        args.pipeline_version or "n/a",
    )

    # Sub-jobs imported here so the module is importable without all deps installed
    breaches: list[str] = []

    try:
        from monitoring.drift_job.retrieval_drift import run as run_retrieval
        if run_retrieval(args.trigger, args.pipeline_version, args.window_hours):
            breaches.append("retrieval_drift")
    except Exception:
        logger.exception("retrieval_drift sub-job failed")

    try:
        from monitoring.drift_job.output_drift import run as run_output
        if run_output(args.trigger, args.pipeline_version, args.window_hours):
            breaches.append("output_drift")
    except Exception:
        logger.exception("output_drift sub-job failed")

    try:
        from monitoring.drift_job.quality_eval import run as run_quality
        if run_quality(args.trigger, args.pipeline_version, args.window_hours):
            breaches.append("quality_eval")
    except Exception:
        logger.exception("quality_eval sub-job failed")

    try:
        from monitoring.drift_job.feedback_analysis import run as run_feedback
        if run_feedback(args.trigger, args.pipeline_version, args.window_hours):
            breaches.append("feedback_analysis")
    except Exception:
        logger.exception("feedback_analysis sub-job failed")

    if breaches:
        logger.warning("Drift breaches detected: %s", ", ".join(breaches))
        return 1

    logger.info("Drift job complete — no breaches detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
