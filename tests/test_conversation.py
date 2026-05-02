from __future__ import annotations

import pytest
from app.telemetry.logger import init_db
from app.conversation import get_or_create_conversation, get_conversation_history


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    """Point telemetry DB to a temp file and initialise it."""
    db = str(tmp_path / "test.db")
    monkeypatch.setattr("app.telemetry.logger._engine", None)

    import sqlalchemy.ext.asyncio as sa
    from app.telemetry import logger as tl
    from app.telemetry.schema import Base

    engine = sa.create_async_engine(f"sqlite+aiosqlite:///{db}", echo=False)
    session_factory = sa.async_sessionmaker(engine, expire_on_commit=False)
    tl._engine = engine
    tl._session_factory = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


@pytest.mark.asyncio
async def test_create_conversation():
    cid = "test-conv-1"
    result = await get_or_create_conversation(cid, doc_filter=None)
    assert result == cid


@pytest.mark.asyncio
async def test_get_empty_history():
    cid = "test-conv-2"
    await get_or_create_conversation(cid)
    history = await get_conversation_history(cid)
    assert history == []
