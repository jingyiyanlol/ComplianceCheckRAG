FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
       "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

# ---- test stage (runs as root for pytest compatibility) ----
FROM python:3.11-slim AS test

WORKDIR /workspace

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Don't set a user — pytest needs write access to the mounted workspace
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["tests/", "-v"]

# ---- runtime (default stage when no --target specified) ----
FROM python:3.11-slim

RUN groupadd -r raguser && useradd -r -g raguser raguser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/

RUN chown -R raguser:raguser /app
USER raguser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
