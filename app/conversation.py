from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.telemetry import logger as _tl
from app.telemetry.schema import Conversation, Message

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    conversation_id: str,
    doc_filter: list[str] | None = None,
) -> str:
    """Ensure a conversation row exists in the database.

    Args:
        conversation_id: Client-provided UUID for the conversation.
        doc_filter: Document scope for this conversation; None = global.

    Returns:
        The conversation_id (unchanged).
    """
    now = datetime.now(timezone.utc)
    async with _tl._session_factory() as session:
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            conv = Conversation(
                id=conversation_id,
                doc_filter=json.dumps(doc_filter) if doc_filter is not None else None,
                created_at=now,
                updated_at=now,
            )
            session.add(conv)
            await session.commit()
    return conversation_id


async def get_conversation_history(conversation_id: str) -> list[dict]:
    """Load all messages for a conversation ordered by creation time.

    Args:
        conversation_id: UUID of the conversation to load.

    Returns:
        List of dicts with keys: id, role, content, created_at (ISO string).
    """
    async with _tl._session_factory() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
