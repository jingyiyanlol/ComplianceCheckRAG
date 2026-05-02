# Testing

## Running the test suite

All tests run inside the dev container where Python 3.11 and all dependencies are guaranteed.

```bash
make test          # pytest -v (recommended)
make lint          # ruff check
make check         # lint + test in one shot
```

Frontend checks:

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

---

## Test structure

```
tests/
├── conftest.py          # shared fixtures (async FastAPI test client)
├── test_pii.py          # Presidio masking unit tests
├── test_rag_eval.py     # chunking pipeline unit tests
├── test_conversation.py # SQLite conversation persistence
├── test_telemetry.py    # async telemetry write verification
└── test_security.py     # API input validation and CORS
```

---

## What each file tests

### `test_pii.py`
Unit tests for `app/pii.py` (Microsoft Presidio masking). No external services required.

| Test | What it checks |
|---|---|
| `test_mask_returns_tuple` | `mask()` always returns `(str, list)` |
| `test_mask_detects_email` | Email addresses are replaced in output and listed in entity metadata |
| `test_mask_empty_string` | Empty input returns empty output without error |
| `test_mask_no_pii` | Compliance-domain text with no PII passes through unchanged |

### `test_rag_eval.py`
Unit tests for `app/rag/chunking.py`. No Ollama or ChromaDB calls — operates entirely on in-memory `ExtractedDoc` objects.

| Test | What it checks |
|---|---|
| `test_chunk_doc_empty_sections` | Empty document produces zero chunks |
| `test_chunk_doc_produces_chunks` | Two sections → two chunks, correct doc_name and section labels |
| `test_chunk_metadata_fields` | Every chunk carries `doc_name`, `pipeline_version`, `content_hash`, `ingested_at` |
| `test_chroma_id_is_unique_for_different_content` | `chroma_id` differs across chunks with different content |

`chroma_id` is the composite key used for idempotent ChromaDB upserts: `{doc_name}::{chunk_index}::{content_hash}`.

### `test_conversation.py`
Integration tests for `app/conversation.py` against a real (temporary) SQLite database.

The `isolated_db` fixture patches `app.telemetry.logger._engine` and `app.telemetry.logger._session_factory` **through the module reference** (not by import-by-value) so that `conversation.py`'s session calls pick up the test engine:

```python
from app.telemetry import logger as tl
tl._engine = engine
tl._session_factory = session_factory
```

| Test | What it checks |
|---|---|
| `test_create_conversation` | `get_or_create_conversation()` returns the conversation ID |
| `test_create_conversation_with_doc_filter` | Scoped conversations are stored; second call is a no-op |
| `test_get_empty_history` | Newly created conversation returns an empty history list |

### `test_telemetry.py`
Verifies that the non-blocking telemetry background task actually writes to the database. This is the most subtle test in the suite.

`log_message()` schedules an `asyncio.create_task()` and returns immediately — the write happens asynchronously. The test drains the event loop with `await asyncio.sleep(0)` five times to let the task complete, then queries the DB directly:

```python
mid = tl.log_message(conversation_id="conv-db-1", role="assistant", content="...")
for _ in range(5):
    await asyncio.sleep(0)          # drain the background task
async with isolated_db() as session:
    row = await session.get(Message, mid)
assert row is not None
```

| Test | What it checks |
|---|---|
| `test_log_message_returns_id` | `log_message()` returns a non-empty string ID synchronously |
| `test_log_message_writes_to_db` | Background task persists the row; content and latency fields are correct |
| `test_log_message_accepts_optional_fields` | Optional fields (chunks, PII entities, latencies) are accepted without error |

### `test_security.py`
API-level security guardrails tested against the real FastAPI app via `httpx.AsyncClient` (from `conftest.py`).

| Test | What it checks |
|---|---|
| `test_chat_rejects_long_message` | Messages > 1000 chars return HTTP 422 |
| `test_feedback_rejects_invalid_rating` | Ratings outside `{1, -1}` return HTTP 422 |
| `test_health_endpoint` | `/health` returns `{"status": "ok"}` |
| `test_cors_not_allowed_from_unknown_origin` | Unknown origins do not receive `Access-Control-Allow-Origin` |

---

## Test configuration

Configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   # all async test functions are treated as asyncio tests
testpaths = ["tests"]
```

`asyncio_mode = "auto"` means you do not need `@pytest.mark.asyncio` on every async test (though the decorator is still accepted and harmless).

---

## What is not yet covered

- `/chat` SSE streaming happy path (needs a running Ollama instance — excluded from unit CI)
- `/admin/ingest` end-to-end (requires PDFs and ChromaDB)
- Frontend component tests (Vitest not yet set up)

These are integration-level and are validated via the Docker Compose stack manually. See `docs/deployment.md` for the full stack test workflow.
