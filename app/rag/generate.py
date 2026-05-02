from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from app.llm import stream_chat
from app.pii import mask

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a compliance assistant for a financial institution. Answer questions \
accurately and concisely using only the provided regulatory document excerpts. \
If the answer cannot be found in the excerpts, say so clearly — do not speculate. \
Always cite the document name and section when referencing a specific rule or requirement.\
"""


def _format_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block.

    Args:
        chunks: List of chunk dicts from retrieve().

    Returns:
        A formatted string ready to include in the LLM prompt.
    """
    lines: list[str] = ["--- Retrieved document excerpts ---"]
    for i, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] {chunk['doc_name']} — {chunk['section']}\n{chunk['text']}"
        )
    lines.append("--- End of excerpts ---")
    return "\n\n".join(lines)


async def generate_response(
    query: str,
    chunks: list[dict],
    history: list[dict[str, str]],
) -> AsyncGenerator[str, None]:
    """Assemble the prompt and stream the LLM response token by token.

    PII is masked in the query, retrieved chunk text, and all history turns
    before any content is sent to the LLM.

    Args:
        query: The (rewritten) user query, pre-PII-masked.
        chunks: Retrieved context chunks from retrieve().
        history: Full conversation history as role/content dicts.

    Yields:
        Decoded text tokens from the LLM stream.
    """
    # Mask PII in chunks
    masked_chunks = []
    for chunk in chunks:
        masked_text, _ = mask(chunk["text"])
        masked_chunks.append({**chunk, "text": masked_text})

    # Mask PII in history
    masked_history: list[dict[str, str]] = []
    for turn in history:
        masked_content, _ = mask(turn["content"])
        masked_history.append({"role": turn["role"], "content": masked_content})

    context_block = _format_chunks(masked_chunks)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": f"{_SYSTEM_PROMPT}\n\n{context_block}"},
        *masked_history,
        {"role": "user", "content": query},
    ]

    async for token in stream_chat(messages):
        yield token
