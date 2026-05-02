from __future__ import annotations

import logging

import ollama

from app.config import settings
from app.rag.ingest import _chroma_client, _get_collection

logger = logging.getLogger(__name__)


def _embed_query(query: str) -> list[float]:
    """Embed a single query string using nomic-embed-text.

    Args:
        query: The search query to embed.

    Returns:
        A float vector representation of the query.
    """
    response = ollama.embed(
        model=settings.embed_model,
        input=[query],
        options={"base_url": settings.ollama_base_url},
    )
    return response.embeddings[0]


def retrieve(
    query: str,
    doc_filter: list[str] | None = None,
    top_k: int | None = None,
) -> tuple[list[dict], list[float]]:
    """Embed a query and retrieve the top-K chunks from ChromaDB.

    Args:
        query: The (rewritten) search query.
        doc_filter: Optional list of doc_name values to restrict search to.
                    None means search across all documents.
        top_k: Number of results to return; defaults to settings.top_k.

    Returns:
        A tuple of (chunks, query_embedding) where chunks is a list of dicts
        with keys: chunk_id, score, doc_name, section, text, doc_title, section_path.
    """
    k = top_k or settings.top_k
    query_embedding = _embed_query(query)

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

    chunks: list[dict] = []
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    for chunk_id, text, meta, dist in zip(ids, docs, metas, dists):
        # ChromaDB cosine distance → similarity score
        score = 1.0 - dist
        chunks.append(
            {
                "chunk_id": chunk_id,
                "score": score,
                "doc_name": meta.get("doc_name", ""),
                "doc_title": meta.get("doc_title", ""),
                "section": meta.get("section", ""),
                "section_path": meta.get("section_path", ""),
                "text": text,
            }
        )

    logger.debug("Retrieved %d chunks for query: %s", len(chunks), query[:80])
    return chunks, query_embedding
