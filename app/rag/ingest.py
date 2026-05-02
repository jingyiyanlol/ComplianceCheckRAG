from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

import chromadb
import ollama

from app.config import settings
from app.rag.chunking import Chunk, ExtractedDoc, chunk_doc, extract_doc

logger = logging.getLogger(__name__)

# Module-level cached Ollama client — respects settings.ollama_base_url
_ollama_client: ollama.Client | None = None


def _get_ollama_client() -> ollama.Client:
    """Return a cached Ollama sync client.

    Returns:
        A shared ollama.Client instance configured with settings.ollama_base_url.
    """
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = ollama.Client(host=settings.ollama_base_url)
    return _ollama_client


# ---------------------------------------------------------------------------
# ChromaDB client
# ---------------------------------------------------------------------------

def _chroma_client() -> chromadb.ClientAPI:
    """Return a ChromaDB client using settings.

    Uses PersistentClient when CHROMA_MODE=local (default for dev),
    or HttpClient when CHROMA_MODE=http (Docker/K8s).

    Returns:
        A configured chromadb ClientAPI instance.
    """
    if settings.chroma_mode == "local":
        return chromadb.PersistentClient(path=settings.chroma_local_path)
    kwargs: dict = {"host": settings.chroma_host, "port": settings.chroma_port}
    if settings.chroma_auth_token:
        kwargs["headers"] = {"Authorization": f"Bearer {settings.chroma_auth_token}"}
    return chromadb.HttpClient(**kwargs)


def _get_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    """Get or create the compliance docs collection.

    Args:
        client: An active ChromaDB client.

    Returns:
        The ChromaDB Collection object.
    """
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using nomic-embed-text via Ollama.

    Args:
        texts: List of strings to embed.

    Returns:
        List of float vectors, one per input text.
    """
    response = _get_ollama_client().embed(model=settings.embed_model, input=texts)
    return response.embeddings


# ---------------------------------------------------------------------------
# llms-txt generation
# ---------------------------------------------------------------------------

def _write_llms_txt(extracted: ExtractedDoc, doc_name: str, pipeline_version: str) -> None:
    """Write a clean llms-txt markdown artifact for an ingested document.

    Args:
        extracted: Parsed document content.
        doc_name: Canonical document stem name.
        pipeline_version: Git SHA or 'local'.
    """
    from datetime import datetime, timezone

    out_dir = Path(settings.llms_txt_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{doc_name}.md"

    ingested_at = datetime.now(timezone.utc).isoformat()
    lines: list[str] = [
        "---",
        f"title: {extracted.title}",
        "source: local",
        f"ingested_at: {ingested_at}",
        f"pipeline_version: {pipeline_version}",
        "---",
        "",
    ]
    for heading, _path, body in extracted.sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(body)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote llms-txt artifact: %s", out_path)


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def _upsert_chunks(
    collection: chromadb.Collection,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> tuple[int, int]:
    """Upsert chunks into ChromaDB, skipping unchanged ones.

    ChromaDB upsert is idempotent — existing IDs are overwritten only when
    content changes. We rely on the composite chroma_id to detect no-ops at
    the application level by comparing existing IDs before calling upsert.

    Args:
        collection: Target ChromaDB collection.
        chunks: Chunks to upsert.
        embeddings: Corresponding embedding vectors.

    Returns:
        Tuple of (upserted_count, skipped_count).
    """
    existing = set(collection.get(ids=[c.chroma_id for c in chunks])["ids"])
    new_chunks = [(c, e) for c, e in zip(chunks, embeddings) if c.chroma_id not in existing]
    skipped = len(chunks) - len(new_chunks)

    if new_chunks:
        collection.upsert(
            ids=[c.chroma_id for c, _ in new_chunks],
            embeddings=[e for _, e in new_chunks],
            documents=[c.text for c, _ in new_chunks],
            metadatas=[c.metadata for c, _ in new_chunks],
        )

    return len(new_chunks), skipped


# ---------------------------------------------------------------------------
# Per-document ingestion
# ---------------------------------------------------------------------------

def ingest_pdf(pdf_path: Path, collection: chromadb.Collection, pipeline_version: str) -> None:
    """Ingest a single PDF into ChromaDB and write its llms-txt artifact.

    Args:
        pdf_path: Path to the PDF file.
        collection: Target ChromaDB collection.
        pipeline_version: Git SHA or 'local'.

    Raises:
        RuntimeError: If the PDF yields no extractable text.
    """
    doc_name = pdf_path.stem
    start = time.monotonic()

    logger.info("Extracting: %s", pdf_path.name)
    extracted = extract_doc(str(pdf_path))

    if not extracted.sections:
        raise RuntimeError(
            f"{pdf_path.name} yielded no extractable text — "
            "likely a scanned image PDF. OCR is not in scope for MVP."
        )

    chunks = chunk_doc(extracted, doc_name=doc_name, pipeline_version=pipeline_version)
    logger.info("Embedding %d chunks for %s", len(chunks), doc_name)
    embeddings = _embed([c.text for c in chunks])

    upserted, skipped = _upsert_chunks(collection, chunks, embeddings)
    _write_llms_txt(extracted, doc_name=doc_name, pipeline_version=pipeline_version)

    elapsed = time.monotonic() - start
    logger.info(
        "Ingested: %s | chunks: %d | skipped: %d | time: %.1fs",
        doc_name, upserted, skipped, elapsed,
    )


# ---------------------------------------------------------------------------
# Drift check
# ---------------------------------------------------------------------------

def _run_post_ingest_drift() -> None:
    """Run an ad-hoc 1-hour drift check if a baseline snapshot exists."""
    snapshot_marker = Path("monitoring/drift_job/last_snapshot.json")
    if not snapshot_marker.exists():
        logger.debug("No baseline snapshot found — skipping post-ingest drift check.")
        return

    logger.info("Running post-ingest drift check (window=1h)...")
    result = subprocess.run(
        [
            sys.executable,
            "monitoring/drift_job/run_drift.py",
            "--trigger", "adhoc",
            "--window-hours", "1",
        ],
        capture_output=False,
        timeout=300,
    )
    if result.returncode != 0:
        logger.warning("Post-ingest drift check exited with code %d", result.returncode)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Discover all PDFs in data/, ingest each one, then run post-ingest drift check."""
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")

    pipeline_version = _get_pipeline_version()
    data_dir = Path(settings.data_dir)
    pdfs = sorted(data_dir.glob("*.pdf"))

    if not pdfs:
        logger.info("No PDFs found in %s/. Add documents and retry.", data_dir)
        return

    logger.info("Found %d PDF(s) to ingest. Pipeline version: %s", len(pdfs), pipeline_version)

    client = _chroma_client()
    collection = _get_collection(client)

    errors: list[str] = []
    for pdf_path in pdfs:
        try:
            ingest_pdf(pdf_path, collection, pipeline_version)
        except RuntimeError as exc:
            logger.error("%s", exc)
            errors.append(str(exc))

    if errors:
        logger.warning("%d document(s) failed to ingest:", len(errors))
        for e in errors:
            logger.warning("  - %s", e)

    _run_post_ingest_drift()


def _get_pipeline_version() -> str:
    """Return the short git SHA, or 'local' if not in a git repo.

    Returns:
        Short git SHA string or 'local'.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "local"


if __name__ == "__main__":
    main()
