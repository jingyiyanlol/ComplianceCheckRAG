FROM python:3.11-slim

# System deps: compiler (for native Python extensions), git, curl (for NodeSource)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Node.js 24 LTS via NodeSource (pinned major version, deterministic on any Debian/Ubuntu)
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — matches production Dockerfile convention
RUN useradd -m -s /bin/bash dev

# pip-tools: build tool for compiling requirements.in → requirements.txt
# Installed globally (not in the project venv) so it is available before make setup runs.
# It is NOT listed in requirements.in — it is a dev container concern only.
RUN pip install --no-cache-dir pip-tools

USER dev

# Ensure ~/.local/bin (where pip installs user scripts) is on PATH
ENV PATH="/home/dev/.local/bin:${PATH}"

WORKDIR /workspace
