from __future__ import annotations

import logging

from app.config import settings
from app.llm import generate_once

logger = logging.getLogger(__name__)

_REWRITE_PROMPT = (
    "Given the conversation below, write a single self-contained search query "
    "that captures the user's latest question. Output only the query, no preamble."
)


async def rewrite_query(
    history: list[dict[str, str]],
    new_message: str,
) -> str:
    """Rewrite a multi-turn question into a standalone search query.

    Sends the last N turns + the new message to the LLM and returns a
    standalone query suitable for embedding and vector search.

    Args:
        history: Prior conversation turns as [{"role": ..., "content": ...}].
        new_message: The latest user message.

    Returns:
        A rewritten standalone query string. Falls back to new_message on error.
    """
    n = settings.query_rewrite_turns
    recent = history[-(n * 2):]  # keep last N user+assistant pairs

    context_lines = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in recent
    )
    prompt = (
        f"{_REWRITE_PROMPT}\n\n"
        f"Conversation:\n{context_lines}\n"
        f"User: {new_message}\n\n"
        "Search query:"
    )

    try:
        rewritten = await generate_once([{"role": "user", "content": prompt}])
        result = rewritten.strip().strip('"').strip("'")
        logger.debug("Rewritten query: %s", result)
        return result or new_message
    except Exception:
        logger.exception("Query rewrite failed; using original message")
        return new_message
