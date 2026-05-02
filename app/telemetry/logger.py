from __future__ import annotations

import asyncio
import json
import logging
import struct
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.telemetry.schema import Base, Conversation, Message

logger = logging.getLogger(__name__)

_engine = create_async_engine(f"sqlite+aiosqlite:///{settings.telemetry_db_path}", echo=False)
_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist. Called once at app startup.

    Returns:
        None
    """
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _pack_embedding(vec: list[float] | None) -> bytes | None:
    """Pack a float list into a compact binary blob.

    Args:
        vec: List of float32 values, or None.

    Returns:
        Packed bytes or None.
    """
    if vec is None:
        return None
    return struct.pack(f"{len(vec)}f", *vec)


async def _write_message(
    *,
    message_id: str,
    conversation_id: str,
    role: str,
    content: str,
    rewritten_query: str | None,
    retrieved_chunks: list[dict] | None,
    retrieval_latency_ms: int | None,
    llm_latency_ms: int | None,
    response_embedding: list[float] | None,
    query_embedding: list[float] | None,
    pii_entities: list[dict] | None,
) -> None:
    """Internal coroutine that writes a message row to SQLite.

    Args:
        message_id: UUID for the new message row.
        conversation_id: Parent conversation UUID.
        role: 'user' or 'assistant'.
        content: The message text (post-PII masking).
        rewritten_query: Standalone query produced by the rewriter, if any.
        retrieved_chunks: List of chunk metadata dicts, if any.
        retrieval_latency_ms: Retrieval duration in milliseconds.
        llm_latency_ms: LLM generation duration in milliseconds.
        response_embedding: Float vector of the response embedding.
        query_embedding: Float vector of the query embedding.
        pii_entities: List of detected PII entity dicts.

    Returns:
        None
    """
    now = datetime.now(timezone.utc)
    async with _session_factory() as session:
        # Upsert conversation row
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            conv = Conversation(
                id=conversation_id,
                doc_filter=None,
                created_at=now,
                updated_at=now,
            )
            session.add(conv)
        else:
            conv.updated_at = now

        msg = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            rewritten_query=rewritten_query,
            retrieved_chunks=json.dumps(retrieved_chunks) if retrieved_chunks else None,
            retrieval_latency_ms=retrieval_latency_ms,
            llm_latency_ms=llm_latency_ms,
            response_length=len(content),
            response_embedding=_pack_embedding(response_embedding),
            query_embedding=_pack_embedding(query_embedding),
            pii_entities_found=json.dumps(pii_entities) if pii_entities else None,
            created_at=now,
        )
        session.add(msg)
        await session.commit()


def log_message(
    *,
    message_id: str | None = None,
    conversation_id: str,
    role: str,
    content: str,
    rewritten_query: str | None = None,
    retrieved_chunks: list[dict] | None = None,
    retrieval_latency_ms: int | None = None,
    llm_latency_ms: int | None = None,
    response_embedding: list[float] | None = None,
    query_embedding: list[float] | None = None,
    pii_entities: list[dict] | None = None,
) -> str:
    """Schedule a non-blocking telemetry write and return the message ID.

    This fires a background task via asyncio.create_task() and returns
    immediately — it is never awaited in the request path.

    Args:
        message_id: Optional pre-generated UUID; generated if omitted.
        conversation_id: Parent conversation UUID.
        role: 'user' or 'assistant'.
        content: The message text.
        rewritten_query: Standalone search query from the rewriter.
        retrieved_chunks: Retrieved chunk metadata dicts.
        retrieval_latency_ms: Retrieval duration in milliseconds.
        llm_latency_ms: LLM duration in milliseconds.
        response_embedding: Response embedding float vector.
        query_embedding: Query embedding float vector.
        pii_entities: Detected PII entity dicts.

    Returns:
        The message_id used for this row (for linking feedback later).
    """
    mid = message_id or str(uuid.uuid4())
    asyncio.create_task(
        _write_message(
            message_id=mid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            rewritten_query=rewritten_query,
            retrieved_chunks=retrieved_chunks,
            retrieval_latency_ms=retrieval_latency_ms,
            llm_latency_ms=llm_latency_ms,
            response_embedding=response_embedding,
            query_embedding=query_embedding,
            pii_entities=pii_entities,
        )
    )
    return mid
