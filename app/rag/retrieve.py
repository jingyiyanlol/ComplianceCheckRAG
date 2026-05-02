from __future__ import annotations

import asyncio
import logging

import ollama

from app.config import settings
from app.rag.ingest import _chroma_client, _get_collection

logger = logging.getLogger(__name__)

# Module-level cached Ollama client — one connection pool, not one per call
_ollama_client: ollama.Client | None = None


def _get_ollama_client() -> ollama.Client:
    """Return a cached Ollama sync client respecting settings.ollama_base_url.

    Returns:
        A shared ollama.Client instance.
    """
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = ollama.Client(host=settings.ollama_base_url)
    return _ollama_client


def _embed_query(query: str) -> list[float]:
    """Embed a single query string using nomic-embed-text.

    Args:
        query: The search query to embed.

    Returns:
        A float vector representation of the query.
    """
    response = _get_ollama_client().embed(model=settings.embed_model, input=[query])
    return response.embeddings[0]


def _chroma_query(
    query_embedding: list[float],
    doc_filter: list[str] | None,
    k: int,
) -> tuple[list[str], list[str], list[dict], list[float]]:
    """Run a synchronous ChromaDB query.

    Args:
        query_embedding: Pre-computed embedding vector for the query.
        doc_filter: Optional list of doc_name values to restrict search to.
        k: Number of results to return.

    Returns:
        Tuple of (ids, documents, metadatas, distances).
    """
    client = _chroma_client()
    collection = _get_collection(client)

    where: dict | None = None
    if doc_filter:
        if len(doc_filter) == 1:
            where = {"doc_name": {"$eq": doc_filter[0]}}
        else:
            where = {"doc_name": {"$in": doc_filter}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return (
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )


async def retrieve(
    query: str,
    doc_filter: list[str] | None = None,
    top_k: int | None = None,
) -> tuple[list[dict], list[float]]:
    """Embed a query and retrieve the top-K chunks from ChromaDB.

    Both the embedding call and ChromaDB query run in a thread-pool executor
    so the async event loop is never blocked by synchronous I/O.

    Args:
        query: The (rewritten) search query.
        doc_filter: Optional list of doc_name values to restrict search to.
                    None means search across all documents.
        top_k: Number of results to return; defaults to settings.top_k.

    Returns:
        A tuple of (chunks, query_embedding) where chunks is a list of dicts
        with keys: chunk_id, score, doc_name, section, text, doc_title, section_path.
    """
    k = top_k if top_k is not None else settings.top_k
    loop = asyncio.get_running_loop()

    query_embedding: list[float] = await loop.run_in_executor(None, _embed_query, query)
    ids, docs, metas, dists = await loop.run_in_executor(
        None, _chroma_query, query_embedding, doc_filter, k
    )

    chunks: list[dict] = []
    for chunk_id, text, meta, dist in zip(ids, docs, metas, dists):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "score": 1.0 - dist,  # cosine distance → similarity
                "doc_name": meta.get("doc_name", ""),
                "doc_title": meta.get("doc_title", ""),
                "section": meta.get("section", ""),
                "section_path": meta.get("section_path", ""),
                "text": text,
            }
        )

    logger.debug("Retrieved %d chunks for query: %s", len(chunks), query[:80])
    return chunks, query_embedding
