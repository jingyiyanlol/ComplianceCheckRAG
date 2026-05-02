from __future__ import annotations

import pytest
from app.telemetry.logger import log_message


@pytest.mark.asyncio
async def test_log_message_returns_id():
    mid = log_message(
        conversation_id="conv-1",
        role="assistant",
        content="Test response",
    )
    assert isinstance(mid, str)
    assert len(mid) > 0


@pytest.mark.asyncio
async def test_log_message_accepts_optional_fields():
    mid = log_message(
        conversation_id="conv-2",
        role="user",
        content="What is Basel III?",
        rewritten_query="Basel III requirements",
        retrieved_chunks=[{"chunk_id": "abc", "score": 0.9, "doc_name": "doc1", "section": "Intro"}],
        retrieval_latency_ms=120,
        llm_latency_ms=800,
        pii_entities=[],
    )
    assert mid is not None
