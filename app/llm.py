from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import ollama

from app.config import settings

logger = logging.getLogger(__name__)


async def stream_chat(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a chat completion from Ollama token by token.

    Args:
        messages: List of {"role": ..., "content": ...} dicts in OpenAI format.
        model: Model name override; defaults to settings.llm_model.

    Yields:
        Decoded text tokens as they arrive from the model.
    """
    _model = model or settings.llm_model
    client = ollama.AsyncClient(host=settings.ollama_base_url)

    async for chunk in await client.chat(
        model=_model,
        messages=messages,
        stream=True,
    ):
        token = chunk.message.content
        if token:
            yield token


async def generate_once(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> str:
    """Generate a complete (non-streaming) response from Ollama.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        model: Model name override; defaults to settings.llm_model.

    Returns:
        The full response text as a single string.
    """
    _model = model or settings.llm_model
    client = ollama.AsyncClient(host=settings.ollama_base_url)
    response = await client.chat(model=_model, messages=messages, stream=False)
    return response.message.content
