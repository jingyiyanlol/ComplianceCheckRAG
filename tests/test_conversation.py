from __future__ import annotations

import pytest
import sqlalchemy.ext.asyncio as sa

from app.conversation import get_conversation_history, get_or_create_conversation
from app.telemetry import logger as tl
from app.telemetry.schema import Base


@pytest.fixture(autouse=True)
async def isolated_db(tmp_path):
    """Redirect all DB access to a temporary SQLite file for each test.

    Patches tl._session_factory in place so that both conversation.py
    (which accesses _tl._session_factory at call time) and logger.py pick
    up the test engine.
    """
    db = str(tmp_path / "test_conv.db")
    engine = sa.create_async_engine(f"sqlite+aiosqlite:///{db}", echo=False)
    session_factory = sa.async_sessionmaker(engine, expire_on_commit=False)

    original_engine = tl._engine
    original_factory = tl._session_factory
    tl._engine = engine
    tl._session_factory = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    tl._engine = original_engine
    tl._session_factory = original_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_conversation():
    cid = "test-conv-1"
    result = await get_or_create_conversation(cid, doc_filter=None)
    assert result == cid


@pytest.mark.asyncio
async def test_create_conversation_with_doc_filter():
    cid = "test-conv-scoped"
    await get_or_create_conversation(cid, doc_filter=["doc_a", "doc_b"])
    # Second call should be a no-op and not raise
    result = await get_or_create_conversation(cid, doc_filter=["doc_a", "doc_b"])
    assert result == cid


@pytest.mark.asyncio
async def test_get_empty_history():
    cid = "test-conv-2"
    await get_or_create_conversation(cid)
    history = await get_conversation_history(cid)
    assert history == []
