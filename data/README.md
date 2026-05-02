# data/

Drop regulatory PDFs here before running ingestion.

## Adding documents

1. Place any number of PDF files directly in this folder:

   ```
   data/
   ├── compliance_document1.pdf
   ├── compliance_document2.pdf
   └── compliance_document3.pdf
   ```

2. Run the ingestion pipeline:

   ```bash
   # Via Docker Compose (recommended)
   docker compose exec backend python -m app.rag.ingest

   # Or directly (with venv activated)
   python -m app.rag.ingest
   ```

3. Each PDF will be:
   - Extracted and chunked by section using PyMuPDF
   - Embedded with `nomic-embed-text` via Ollama
   - Upserted into ChromaDB (re-ingestion is idempotent)
   - Converted to a clean markdown file under `llms-txt/`

## Notes

- Any number of PDFs are supported — the pipeline loops over all files in this folder
- Re-ingestion of an unchanged file is a no-op (keyed on `doc_name + chunk_index + content_hash`)
- After adding new documents, refresh the UI — the Scope Modal on new conversations will list all ingested doc names
- PDF files are gitignored; only this README is tracked
