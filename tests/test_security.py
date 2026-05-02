from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_chat_rejects_long_message(client):
    resp = await client.post("/chat", json={
        "conversation_id": "test-conv",
        "history": [],
        "message": "x" * 1001,
        "doc_filter": None,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_feedback_rejects_invalid_rating(client):
    resp = await client.post("/feedback", json={
        "message_id": "some-id",
        "rating": 5,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cors_not_allowed_from_unknown_origin(client):
    resp = await client.get(
        "/health",
        headers={"Origin": "http://evil.example.com"},
    )
    # Should not echo back an ACAO header for unknown origins
    assert "access-control-allow-origin" not in resp.headers or \
           resp.headers.get("access-control-allow-origin") != "http://evil.example.com"
