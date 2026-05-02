from __future__ import annotations

from app.rag.chunking import ExtractedDoc, chunk_doc


def test_chunk_doc_empty_sections():
    doc = ExtractedDoc(title="Test Doc", sections=[])
    chunks = chunk_doc(doc, doc_name="test_doc")
    assert chunks == []


def test_chunk_doc_produces_chunks():
    doc = ExtractedDoc(
        title="Basel III",
        sections=[
            ("Introduction", ["Introduction"], "Basel III is a framework."),
            ("Capital Requirements", ["Capital Requirements"], "Banks must hold 8% capital."),
        ],
    )
    chunks = chunk_doc(doc, doc_name="basel_iii")
    assert len(chunks) == 2
    assert chunks[0].doc_name == "basel_iii"
    assert chunks[0].section == "Introduction"
    assert chunks[1].chunk_index == 1


def test_chunk_metadata_fields():
    doc = ExtractedDoc(
        title="My Doc",
        sections=[("Section A", ["Section A"], "Some content here.")],
    )
    chunk = chunk_doc(doc, doc_name="my_doc", pipeline_version="abc123")[0]
    meta = chunk.metadata
    assert meta["doc_name"] == "my_doc"
    assert meta["pipeline_version"] == "abc123"
    assert "content_hash" in meta
    assert "ingested_at" in meta


def test_chroma_id_is_unique_for_different_content():
    doc = ExtractedDoc(
        title="Doc",
        sections=[
            ("S1", ["S1"], "Content A"),
            ("S2", ["S2"], "Content B"),
        ],
    )
    chunks = chunk_doc(doc, doc_name="doc")
    assert chunks[0].chroma_id != chunks[1].chroma_id
