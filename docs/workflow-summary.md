# Development Workflow & CI/CD Summary

This document outlines the complete development, testing, and deployment workflow for ComplianceCheckRAG.

## Local Development Workflow

### 1. Start work

```bash
# Clone and open in VS Code dev container
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
code ComplianceCheckRAG
# Select "Reopen in Container" when prompted
# make setup runs automatically inside the container

# Or use CLI dev container
git clone https://github.com/jingyiyanlol/ComplianceCheckRAG.git
cd ComplianceCheckRAG
make install-hooks   # one-time: install git hooks from scripts/
make dev-shell       # build image (deps pre-installed) and drop into bash
```

### 2. Make changes

```bash
# Edit backend code
vim app/main.py

# Edit frontend code
vim frontend/src/components/ChatWindow.tsx

# Add/update dependencies
vim requirements.in   # (pre-commit hook will auto-compile requirements.txt)
vim frontend/package.json
```

### 3. Test before committing

```bash
# Test in local venv (fast iteration, requires Python 3.11)
make test-local

# Test in Docker (guaranteed Python 3.11 + all deps, matches CI exactly)
make test

# Frontend
cd frontend && npm run lint && npm run build
```

**Note:** `make test` builds a Docker image with a dedicated test stage and runs pytest inside it, ensuring the same Python 3.11 and dependency versions as CI. This is the recommended approach to avoid local environment drift.

### 4. Pre-commit hooks

When you stage `requirements.in`:
```bash
git add requirements.in
git commit -m "Add greenlet dependency"
# Hook automatically runs:
#   1. Detects requirements.in in staging
#   2. Runs make compile-deps (in dev container)
#   3. Stages regenerated requirements.txt
#   4. Allows commit to proceed
```

**What happens if the hook fails?**
```bash
# Hook blocked commit due to pip-compile error
# Fix the constraint
vim requirements.in

# Re-stage and retry
git add requirements.in
git commit -m "Fix constraint"
```

### 5. Commit changes

```bash
# Backend changes
git add app/ tests/
git commit -m "Fix: handle concurrent message writes safely"

# Frontend changes
git add frontend/src/ frontend/package.json frontend/package-lock.json
git commit -m "Feat: improve mobile chat input with safe-area-inset"

# Both dependencies and code
git add requirements.in requirements.txt app/
git commit -m "Add greenlet and update async database layer"
```

### 6. Push and create PR

```bash
git push origin my-feature-branch
# Create PR on GitHub
```

---

## Continuous Integration (GitHub Actions)

Automatically runs on every push and PR to `main`:

### Backend CI (`lint-test` job)

```
Checkout code
  ↓
Install ruff (fast path)
  ↓
Ruff lint (Python code quality)
  ↓
Build Docker test image
  ↓
Run pytest in Docker (Python 3.11 + all deps)
  ↓
[PASS] → triggers build-push job
[FAIL] → blocks PR merge
```

**Why Docker for testing?**
- Python 3.11 guaranteed (no local version drift)
- All dependencies pinned (greenlet builds correctly)
- Identical to production environment
- No setup required on CI runners

### Backend CI (`build-push` job, main only)

```
Checkout code
  ↓
Login to GHCR
  ↓
Build backend Docker image (runtime stage)
  ↓
Push to ghcr.io/{repo}/backend:latest
         ghcr.io/{repo}/backend:{sha}
  ↓
[SUCCESS] → triggers drift-check job
```

### Drift Check job (RAG changes only)

```
Detected changes in: app/rag/, app/llm.py, or docker-compose.yml
  ↓
Set up Python 3.11
  ↓
Install drift deps (evidently, deepeval, etc.)
  ↓
Run drift detection:
  - retrieval score distribution (KS test)
  - response embedding drift (cosine similarity)
  - LLM output quality (DeepEval judge)
  - user feedback ratio
  ↓
[Breach detected] → Pushes alert to Prometheus Pushgateway → Grafana
[All clear] → Completes silently
```

### Frontend CI

```
Checkout code
  ↓
Set up Node 24
  ↓
npm run lint (ESLint v9 flat config)
  ↓
npm run build (fails if gzip > 200KB)
  ↓
Build & push frontend image to GHCR
```

---

## Dependency Management Workflow

### Adding a new dependency

```bash
# Step 1: Edit the source file
vim requirements.in
# Add: chromadb>=1.0.7

# Step 2: Stage the change
git add requirements.in

# Step 3: Commit (pre-commit hook auto-regenerates requirements.txt)
git commit -m "Add chromadb for vector storage"
# Hook output:
#   requirements.in modified — regenerating requirements.txt in dev container...
#   ✓ requirements.txt regenerated and staged

# Step 4: Verify the change
git log --oneline -1
git show HEAD:requirements.txt | grep chromadb
```

### Why this workflow?

- **Source of truth**: `requirements.in` with version bounds (human-readable)
- **Reproducibility**: `requirements.txt` with exact pins (machine-readable)
- **Consistency**: Always compiled in dev container (Python 3.11)
- **Safety**: Pre-commit hook prevents out-of-sync files
- **Automation**: No manual pip-compile commands needed

---

## Testing Strategy

### Local (fast iteration)

```bash
make test-local
# Runs in your local venv
# ✓ Fast feedback loop
# ✗ Requires Python 3.11 + correct greenlet wheel
```

### Docker (guaranteed correctness)

```bash
make test
# Builds test Docker image, runs pytest inside
# ✓ Python 3.11 guaranteed
# ✓ Greenlet always works
# ✓ Matches CI environment exactly
# ✗ Slower (image build ~30s)
```

### CI

- Always Docker-based
- Runs on every PR and push
- Blocks merge if any test fails

### Test coverage

| Test file | Purpose | Environment |
|---|---|---|
| `test_pii.py` | Presidio masking | Local or Docker |
| `test_rag_eval.py` | Chunking pipeline | Local or Docker |
| `test_conversation.py` | SQLite persistence | Local or Docker |
| `test_telemetry.py` | Background tasks | Local or Docker (greenlet required) |
| `test_security.py` | API validation | Local or Docker |

---

## Troubleshooting

### Pre-commit hook fails

```
ERROR: make compile-deps failed. Fix requirements.in and try again.
```

**Cause:** pip-compile found a version conflict

**Fix:**
```bash
# See the full error
make compile-deps

# Adjust the constraint in requirements.in
vim requirements.in

# Re-stage and retry
git add requirements.in
git commit -m "Fix version constraint"
```

### Local tests pass, CI tests fail

**Cause:** Your local venv is Python 3.13, CI uses Python 3.11

**Fix:** Use `make test` (Docker) instead of `make test-local`

### CI lint fails but local lint passes

**Cause:** You're using an older ruff version

**Fix:** Install ruff from requirements.txt
```bash
make setup-backend
```

### Docker test fails with permission error

**Cause:** The test container runs as root but can't write to mounted workspace

**Fix:** Already fixed in the updated Dockerfile. Re-pull and rebuild:
```bash
git pull
make test
```

---

## See Also

- [Testing documentation](testing.md) — detailed test structure
- [Pre-commit hook documentation](pre-commit-hook.md) — hook usage and troubleshooting
- [Dependency management](dependencies.md) — pip-compile workflow details
- [GitHub workflows](../.github/workflows/) — CI/CD configuration
- [Dockerfile](../Dockerfile) — multi-stage build with test stage
- [Makefile](../Makefile) — all available targets
