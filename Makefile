.PHONY: help setup setup-backend setup-frontend install-hooks backend frontend ingest \
        test test-local lint lint-fix check clean clean-all dev-shell

VENV    := .venv

# If running inside the dev container (no .venv needed — deps in system Python),
# fall back to system python3/pip3. Otherwise use the local .venv.
ifeq ($(wildcard $(VENV)/bin/python),)
  PYTHON  := python3
  PIP     := pip3
  UVICORN := python3 -m uvicorn
  PYTEST  := python3 -m pytest
  RUFF    := python3 -m ruff
else
  PYTHON  := $(VENV)/bin/python
  PIP     := $(VENV)/bin/pip
  UVICORN := $(VENV)/bin/uvicorn
  PYTEST  := $(VENV)/bin/pytest
  RUFF    := $(VENV)/bin/ruff
endif

# ---------------------------------------------------------------------------
# Python 3.11 resolution — works on Linux, macOS, and any CI runner
#   Tries: python3.11 → python3 (if it is 3.11) → python (if it is 3.11)
#   Fails with a clear message pointing to the dev container.
# ---------------------------------------------------------------------------

define _check_ver
$(shell $(1) -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)
endef

ifeq ($(call _check_ver,python3.11),3.11)
  PYTHON311 := python3.11
else ifeq ($(call _check_ver,python3),3.11)
  PYTHON311 := python3
else ifeq ($(call _check_ver,python),3.11)
  PYTHON311 := python
else
  PYTHON311 :=
endif

.python-check:
	@if [ -z "$(PYTHON311)" ]; then \
	  echo ""; \
	  echo "ERROR: Python 3.11 not found on PATH."; \
	  echo ""; \
	  echo "Recommended: use the dev container — it ships Python 3.11 automatically."; \
	  echo "  VS Code:  'Dev Containers: Reopen in Container'"; \
	  echo "  CLI:      make dev-shell"; \
	  echo ""; \
	  echo "Or install Python 3.11 manually and ensure it appears on PATH as"; \
	  echo "  python3.11, python3, or python."; \
	  echo ""; \
	  exit 1; \
	fi
	@echo "Python 3.11 OK  ($(PYTHON311))"

# ---------------------------------------------------------------------------
# Node >= 18 resolution — works on Linux and macOS
# ---------------------------------------------------------------------------

.node-check:
	@if ! command -v node >/dev/null 2>&1; then \
	  echo ""; \
	  echo "ERROR: node not found."; \
	  echo ""; \
	  echo "Recommended: use the dev container — it ships Node 24 automatically."; \
	  echo "  VS Code:  'Dev Containers: Reopen in Container'"; \
	  echo "  CLI:      make dev-shell"; \
	  echo ""; \
	  exit 1; \
	fi
	@NODE_MAJOR=$$(node -e "process.stdout.write(String(process.versions.node.split('.')[0]))"); \
	if [ "$$NODE_MAJOR" -lt 24 ]; then \
	  echo "ERROR: Node.js >= 24 required, found $$(node --version)"; \
	  echo "       Use the dev container: make dev-shell"; \
	  exit 1; \
	fi
	@echo "Node $$(node --version) / npm $$(npm --version) OK"

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Recommended workflow:"
	@echo "    VS Code: 'Dev Containers: Reopen in Container'  (runs make setup automatically)"
	@echo "    CLI:     make dev-shell   then   make setup"

# ---------------------------------------------------------------------------
# Dev container shell — for non-VS Code users
# ---------------------------------------------------------------------------

dev-shell: ## Build the dev container (Python 3.11 + Node 24), run setup, drop into bash
	docker build -t ccrag-dev -f .devcontainer/Dockerfile .
	docker run --rm -it \
	  -v "$(CURDIR)":/workspace \
	  -w /workspace \
	  -p 8000:8000 \
	  -p 5173:5173 \
	  ccrag-dev bash

# ---------------------------------------------------------------------------
# Setup (run inside the dev container, or locally if Python 3.11 is present)
# ---------------------------------------------------------------------------

setup: setup-backend setup-frontend install-hooks ## Full first-time setup (backend + frontend + git hooks)
	@echo ""
	@echo "Setup complete. Next steps:"
	@echo "  1. Add PDFs to data/"
	@echo "  2. make ingest"
	@echo "  3. make backend     (terminal 1)"
	@echo "  4. make frontend    (terminal 2)"
	@echo "  5. Open http://localhost:5173"

install-hooks: ## Install git hooks from scripts/ into .git/hooks/
	cp scripts/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "✓ pre-commit hook installed"

setup-backend: .python-check ## Install Python deps and spacy model
	"$(PYTHON311)" -m venv --clear $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install --quiet "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example — edit if needed")

setup-frontend: .node-check ## Install frontend npm dependencies
	cd frontend && npm ci

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

backend: ## Start the FastAPI backend (http://localhost:8000)
	PYTHONPATH=. $(UVICORN) app.main:app --reload --port 8000

frontend: ## Start the Vite dev server (http://localhost:5173)
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

ingest: ## Ingest all PDFs in data/ into ChromaDB
	PYTHONPATH=. $(PYTHON) -m app.rag.ingest

# ---------------------------------------------------------------------------
# Dependency management
# ---------------------------------------------------------------------------

compile-deps: ## Recompile requirements.txt from requirements.in (runs inside dev container)
	docker build -q -t ccrag-dev -f .devcontainer/Dockerfile .
	docker run --rm \
	  -v "$(CURDIR)":/workspace \
	  -w /workspace \
	  ccrag-dev \
	  pip-compile requirements.in \
	    --output-file requirements.txt \
	    --strip-extras \
	    --resolver=backtracking
	@echo ""
	@echo "requirements.txt updated. Review the diff then run: make setup-backend"

# ---------------------------------------------------------------------------
# Test & lint
# ---------------------------------------------------------------------------

test: ## Run pytest in Docker container (Python 3.11, all dependencies pinned)
	docker build -q --target test -t ccrag-test -f Dockerfile .
	docker run --rm \
	  -v "$(CURDIR)":/workspace \
	  ccrag-test

test-local: ## Run pytest locally (requires Python 3.11 venv)
	PYTHONPATH=. $(PYTEST) tests/ -v

lint: ## Run ruff linter
	$(RUFF) check .

lint-fix: ## Run ruff with auto-fix
	$(RUFF) check . --fix

check: lint test ## Run lint + tests (in Docker)

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean: ## Remove generated files (chroma data, telemetry db, caches)
	rm -rf .chroma/ telemetry.db llms-txt/*.md
	find . -type d -name __pycache__ | grep -v .venv | xargs rm -rf
	find . -type d -name .pytest_cache | grep -v .venv | xargs rm -rf
	find . -type d -name .ruff_cache | grep -v .venv | xargs rm -rf

clean-all: clean ## Also remove venv and frontend node_modules
	rm -rf $(VENV) frontend/node_modules frontend/dist
