---
description: Full pre-commit checklist — review, security, eval, drift, mobile, lint, test, build
---

Run before every commit. Stop at the first hard failure and fix it.

1. **Code review** — invoke `code-reviewer` on recently modified files in `app/`, `frontend/src/`, `monitoring/drift_job/`, `tests/`
2. **Security scan** — invoke `security-scanner` on the same files plus any changed Dockerfile / compose / k8s manifests
3. **RAG eval** *(only if `app/rag/`, `app/llm.py`, or `app/conversation.py` changed)* — invoke `rag-evaluator`
4. **Drift code review** *(only if `monitoring/drift_job/` changed)* — invoke `drift-analyst` in code-review mode
5. **Mobile review** *(only if `frontend/src/` changed)* — invoke `mobile-tester`
6. **Backend lint** — `ruff check .`
7. **Backend tests** — `pytest -v` — all must pass, including multi-turn conversation tests
8. **Frontend lint** — `cd frontend && npm run lint`
9. **Frontend build** — `cd frontend && npm run build` — must succeed; report gzip bundle size; fail if > 200KB
10. **Smoke test** *(if Docker available)* — `docker compose up -d && sleep 15 && curl -f http://localhost:8000/health && docker compose down`
11. **Summary** — one line: `SHIP IT` or `FIX FIRST: <top 3 issues>`

Do not run `git commit`. Just give me the verdict.
