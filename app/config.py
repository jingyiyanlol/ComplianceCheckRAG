from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:4b-q4_0"
    embed_model: str = "nomic-embed-text"

    # ChromaDB
    # chroma_mode: "http" connects to a running ChromaDB server (Docker/K8s);
    # "local" uses PersistentClient backed by chroma_local_path (for dev without Docker).
    chroma_mode: str = "local"
    chroma_local_path: str = ".chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_auth_token: str = ""
    chroma_collection: str = "compliance_docs"

    # Telemetry
    telemetry_db_path: str = "telemetry.db"

    # App
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"

    # Ingestion
    data_dir: str = "data"
    llms_txt_dir: str = "llms-txt"
    top_k: int = 8
    query_rewrite_turns: int = 4
    max_query_length: int = 1000


settings = Settings()
