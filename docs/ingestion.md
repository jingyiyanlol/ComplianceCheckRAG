# Ingestion pipeline

The ingestion pipeline converts raw PDF files into searchable chunks inside ChromaDB. It is idempotent — re-running it on an unchanged document is a no-op.

## Running ingestion

```bash
# Inside the dev container
make ingest

# Or directly
PYTHONPATH=. python -m app.rag.ingest

# Via Docker Compose (full stack)
docker compose exec backend python -m app.rag.ingest
```

---

## Pipeline stages

### 1. Discover PDFs

The pipeline loops over every `*.pdf` file in `settings.data_dir` (default: `data/`). Any number of documents are supported.

### 2. Extract text (`app/rag/chunking.py — extract_doc`)

PyMuPDF (`fitz`) reads each page. Two heuristics filter noise:

**Header/footer exclusion** — content in the top and bottom 5% of each page height is ignored (`_MARGIN_FRACTION = 0.05`). This strips page numbers, running headers, and footers without needing document-specific config.

**Heading detection** — a span is treated as a section heading if:
- Its font size is ≥ 1.15× the modal body font size on the same page (`_HEADING_SIZE_RATIO = 1.15`), **or**
- It has the bold flag set (bit 4 of PyMuPDF's font flags)
- And it is under 200 characters (guards against bold body sentences)

The modal body font size is computed per-page by taking the most frequent font size across all body-area spans.

The result is an `ExtractedDoc` — an ordered list of `(heading, section_path, body_text)` tuples.

### 3. Generate `llms-txt` artifact (`app/rag/ingest.py`)

For each document, a clean markdown file is written to `llms-txt/<doc_stem>.md`:

```markdown
---
title: <extracted or filename>
source: local
ingested_at: <ISO timestamp>
pipeline_version: <git SHA or 'local'>
---

## <Section heading>

<body text>
```

This file is a standalone deliverable that can be fed directly to any LLM without further processing.

### 4. Chunk by section (`app/rag/chunking.py — chunk_doc`)

Each `(heading, path, body)` tuple becomes one `Chunk`. Every chunk carries:

| Field | Description |
|---|---|
| `doc_name` | PDF stem (filename without extension) |
| `doc_title` | Title extracted from PDF metadata or first heading |
| `section` | Heading text |
| `section_path` | Breadcrumb string, e.g. `"Capital Requirements > Tier 1"` |
| `chunk_index` | 0-based position within the document |
| `ingested_at` | UTC ISO timestamp |
| `content_hash` | SHA-256 of the body text, first 16 hex chars |
| `pipeline_version` | Git SHA of the running pipeline, or `"local"` |

The **Chroma ID** is `{doc_name}::{chunk_index}::{content_hash}` — this composite key makes upserts idempotent. If the content of a section changes between ingestion runs, the hash changes and a new embedding is generated. Unchanged sections are skipped.

### 5. Embed and upsert (`app/rag/ingest.py`)

Each chunk's text is embedded using `nomic-embed-text` via the Ollama client. The embedding, text, and metadata are upserted into ChromaDB under the collection defined by `settings.chroma_collection` (default: `compliance_docs`).

ChromaDB is accessed via:
- `PersistentClient` when `CHROMA_MODE=local` (default for dev — no Docker needed)
- `HttpClient` when `CHROMA_MODE=http` (Docker Compose and K8s)

### 6. Post-ingest drift check (optional)

If a `baseline_snapshots` row exists for the previous pipeline version, the ingestion script automatically triggers an ad-hoc drift check:

```bash
python monitoring/drift_job/run_drift.py --trigger adhoc --window-hours 1
```

This surfaces any immediate retrieval score shifts caused by chunking or embedding changes.

---

## Idempotency guarantee

Re-running ingestion on the same PDFs:
- Chunks with unchanged content: **skipped** (same Chroma ID already exists)
- Chunks whose text changed: **replaced** (new hash → new Chroma ID)
- New sections added to a doc: **inserted**
- Removed sections: **not deleted** (ChromaDB retains old chunks — manual cleanup required if needed)

---

## Limitations

- **Scanned PDFs** (image-only) will produce empty sections — PyMuPDF cannot OCR. These are flagged as warnings during ingestion. OCR is a roadmap item.
- **Tables** are extracted as flat text. Table-as-markdown conversion is a roadmap item.
- **Very large sections** are not split — one heading = one chunk regardless of length. Fixed-size fallback chunking is a roadmap item.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `data` | Source PDF directory |
| `LLMS_TXT_DIR` | `llms-txt` | Output directory for markdown artifacts |
| `CHROMA_MODE` | `local` | `local` = PersistentClient; `http` = server |
| `CHROMA_LOCAL_PATH` | `.chroma` | On-disk path (local mode only) |
| `CHROMA_COLLECTION` | `compliance_docs` | ChromaDB collection name |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
