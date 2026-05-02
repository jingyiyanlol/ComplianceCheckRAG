from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.conversation import get_conversation_history, get_or_create_conversation
from app.metrics import (
    ccrag_chunks_retrieved,
    ccrag_feedback_total,
    ccrag_llm_latency_seconds,
    ccrag_pii_hits_total,
    ccrag_query_latency_seconds,
    ccrag_query_total,
    ccrag_retrieval_latency_seconds,
)
from app.pii import mask
from app.rag.generate import generate_response
from app.rag.retrieve import retrieve
from app.rag.rewrite import rewrite_query
from app.telemetry.feedback import record_feedback
from app.telemetry.logger import init_db, log_message

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise database tables on startup."""
    await init_db()
    yield


app = FastAPI(title="ComplianceCheckRAG", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

Instrumentator().instrument(app).expose(app)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: str
    history: list[HistoryMessage] = Field(default_factory=list)
    message: str
    doc_filter: list[str] | None = None

    @field_validator("message")
    @classmethod
    def message_length(cls, v: str) -> str:
        if len(v) > settings.max_query_length:
            raise ValueError(f"Message exceeds {settings.max_query_length} characters")
        return v


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("rating must be 1 or -1")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Liveness check."""
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """Multi-turn RAG chat endpoint. Streams SSE tokens.

    Args:
        req: ChatRequest with conversation_id, history, message, doc_filter.

    Returns:
        StreamingResponse of text/event-stream SSE events.
    """
    await get_or_create_conversation(req.conversation_id, req.doc_filter)

    masked_query, pii_entities = mask(req.message)
    for entity in pii_entities:
        ccrag_pii_hits_total.labels(entity_type=entity["entity_type"]).inc()

    history = [{"role": m.role, "content": m.content} for m in req.history]
    message_id = str(uuid.uuid4())

    async def event_stream() -> AsyncGenerator[str, None]:
        query_start = time.monotonic()
        rewritten = await rewrite_query(history, masked_query)

        retrieval_start = time.monotonic()
        chunks, query_embedding = retrieve(rewritten, doc_filter=req.doc_filter)
        retrieval_ms = int((time.monotonic() - retrieval_start) * 1000)

        ccrag_retrieval_latency_seconds.observe(retrieval_ms / 1000)
        ccrag_chunks_retrieved.observe(len(chunks))

        # Emit citations as first SSE event so the UI can render them immediately
        citations = [
            {
                "chunk_id": c["chunk_id"],
                "doc_name": c["doc_name"],
                "doc_title": c["doc_title"],
                "section": c["section"],
                "score": c["score"],
            }
            for c in chunks
        ]
        yield f"event: citations\ndata: {json.dumps(citations)}\n\n"

        llm_start = time.monotonic()
        full_response: list[str] = []

        async for token in generate_response(masked_query, chunks, history):
            full_response.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        llm_ms = int((time.monotonic() - llm_start) * 1000)
        total_ms = int((time.monotonic() - query_start) * 1000)

        ccrag_llm_latency_seconds.observe(llm_ms / 1000)
        ccrag_query_latency_seconds.observe(total_ms / 1000)
        ccrag_query_total.labels(status="success").inc()

        yield "event: done\ndata: {}\n\n"

        response_text = "".join(full_response)

        # Non-blocking telemetry — fire-and-forget
        log_message(
            message_id=message_id,
            conversation_id=req.conversation_id,
            role="assistant",
            content=response_text,
            rewritten_query=rewritten,
            retrieved_chunks=[
                {
                    "chunk_id": c["chunk_id"],
                    "score": c["score"],
                    "doc_name": c["doc_name"],
                    "section": c["section"],
                }
                for c in chunks
            ],
            retrieval_latency_ms=retrieval_ms,
            llm_latency_ms=llm_ms,
            query_embedding=query_embedding,
            pii_entities=pii_entities,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Message-Id": message_id,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/feedback")
async def feedback(req: FeedbackRequest) -> dict:
    """Record user thumbs up/down for an assistant message.

    Args:
        req: FeedbackRequest with message_id, rating, optional comment.

    Returns:
        Dict with the new feedback row ID.
    """
    feedback_id = await record_feedback(
        message_id=req.message_id,
        rating=req.rating,
        comment=req.comment,
    )
    ccrag_feedback_total.labels(rating=str(req.rating)).inc()
    return {"feedback_id": feedback_id}


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """Return the full message history for a conversation.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Dict with conversation_id and messages list.
    """
    messages = await get_conversation_history(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@app.get("/admin/documents")
async def list_documents() -> dict:
    """List all document names currently indexed in ChromaDB.

    Returns:
        Dict with a 'documents' list of unique doc_name strings.
    """
    from app.rag.ingest import _chroma_client, _get_collection

    client = _chroma_client()
    collection = _get_collection(client)
    result = collection.get(include=["metadatas"])
    names = sorted({m.get("doc_name", "") for m in result["metadatas"] if m.get("doc_name")})
    return {"documents": names}


@app.post("/admin/ingest")
async def trigger_ingest() -> dict:
    """Trigger the ingestion pipeline for all PDFs in data/.

    Returns:
        Dict with status message.
    """
    import asyncio

    from app.rag.ingest import main as ingest_main

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, ingest_main)
    return {"status": "ingestion complete"}
