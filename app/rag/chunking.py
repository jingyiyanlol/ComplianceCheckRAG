from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Font size ratio threshold above body text that signals a heading
_HEADING_SIZE_RATIO = 1.15
# Fraction of page height to ignore at top/bottom (headers/footers)
_MARGIN_FRACTION = 0.05


@dataclass
class Chunk:
    """A single text chunk ready for embedding and upsert."""

    doc_name: str
    doc_title: str
    section: str
    section_path: list[str]
    chunk_index: int
    text: str
    ingested_at: str
    content_hash: str
    pipeline_version: str = "local"

    @property
    def chroma_id(self) -> str:
        """Composite key for idempotent upsert."""
        return f"{self.doc_name}::{self.chunk_index}::{self.content_hash}"

    @property
    def metadata(self) -> dict:
        """Flat metadata dict for ChromaDB."""
        return {
            "doc_name": self.doc_name,
            "doc_title": self.doc_title,
            "section": self.section,
            "section_path": " > ".join(self.section_path),
            "chunk_index": self.chunk_index,
            "ingested_at": self.ingested_at,
            "content_hash": self.content_hash,
            "pipeline_version": self.pipeline_version,
        }


@dataclass
class ExtractedDoc:
    """Raw extraction result from a PDF before chunking."""

    title: str
    sections: list[tuple[str, list[str], str]] = field(default_factory=list)
    # Each entry: (heading, section_path, body_text)


def _body_font_size(page: fitz.Page, margin_top: float, margin_bottom: float) -> float:
    """Return the modal font size for body text on this page, excluding margins.

    Args:
        page: A PyMuPDF page object.
        margin_top: Y-coordinate below which content is considered body.
        margin_bottom: Y-coordinate above which content is considered body.

    Returns:
        The most common font size found in the body area, defaulting to 10.0.
    """
    size_counts: dict[float, int] = {}
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                y = span["origin"][1]
                if margin_top <= y <= margin_bottom:
                    size = round(span["size"], 1)
                    size_counts[size] = size_counts.get(size, 0) + 1
    return max(size_counts, key=size_counts.get) if size_counts else 10.0


def _is_heading(span: dict, body_size: float) -> bool:
    """Return True if a text span looks like a section heading.

    Args:
        span: A PyMuPDF span dict with 'size' and 'flags' keys.
        body_size: Modal body font size for the current page.

    Returns:
        True if span is larger than body text or bold.
    """
    is_large = span["size"] >= body_size * _HEADING_SIZE_RATIO
    is_bold = bool(span["flags"] & 2**4)
    return is_large or is_bold


def extract_doc(pdf_path: str) -> ExtractedDoc:
    """Extract section-aware text from a PDF, skipping headers and footers.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        An ExtractedDoc with a title and ordered list of (heading, path, body) tuples.
    """
    doc = fitz.open(pdf_path)
    title = doc.metadata.get("title", "").strip() or None

    sections: list[tuple[str, list[str], str]] = []
    current_heading = "Preamble"
    current_path: list[str] = ["Preamble"]
    current_body: list[str] = []

    for page in doc:
        page_h = page.rect.height
        margin_top = page_h * _MARGIN_FRACTION
        margin_bottom = page_h * (1 - _MARGIN_FRACTION)
        body_size = _body_font_size(page, margin_top, margin_bottom)

        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                y = spans[0]["origin"][1]
                if y < margin_top or y > margin_bottom:
                    continue

                line_text = " ".join(s["text"] for s in spans).strip()
                if not line_text:
                    continue

                # Detect heading by checking the first span of the line
                if _is_heading(spans[0], body_size) and len(line_text) < 200:
                    if current_body:
                        body = "\n".join(current_body).strip()
                        if body:
                            sections.append((current_heading, current_path[:], body))
                    current_heading = line_text
                    current_path = [line_text]
                    current_body = []
                else:
                    current_body.append(line_text)

    # Flush last section
    if current_body:
        body = "\n".join(current_body).strip()
        if body:
            sections.append((current_heading, current_path[:], body))

    # Fall back to filename-derived title
    if not title and sections:
        title = sections[0][0]

    doc.close()
    return ExtractedDoc(title=title or "Untitled", sections=sections)


def chunk_doc(
    extracted: ExtractedDoc,
    doc_name: str,
    pipeline_version: str = "local",
) -> list[Chunk]:
    """Convert an ExtractedDoc into a flat list of Chunks ready for ChromaDB.

    Args:
        extracted: Output of extract_doc().
        doc_name: Canonical document name (PDF stem).
        pipeline_version: Git SHA or 'local'.

    Returns:
        Ordered list of Chunk objects.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()
    chunks: list[Chunk] = []

    for idx, (heading, path, body) in enumerate(extracted.sections):
        content_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
        chunks.append(
            Chunk(
                doc_name=doc_name,
                doc_title=extracted.title,
                section=heading,
                section_path=path,
                chunk_index=idx,
                text=body,
                ingested_at=ingested_at,
                content_hash=content_hash,
                pipeline_version=pipeline_version,
            )
        )

    logger.debug("Chunked %s into %d sections", doc_name, len(chunks))
    return chunks
