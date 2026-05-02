from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    doc_filter: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(Text, ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_chunks: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    query_embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    pii_entities_found: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    message_id: Mapped[str] = mapped_column(Text, ForeignKey("messages.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or -1
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    message_id: Mapped[str] = mapped_column(Text, ForeignKey("messages.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class DriftRun(Base):
    __tablename__ = "drift_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)  # 'cron' | 'ci' | 'adhoc'
    pipeline_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_at: Mapped[datetime] = mapped_column(nullable=False)
    window_start: Mapped[datetime] = mapped_column(nullable=False)
    window_end: Mapped[datetime] = mapped_column(nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    breached: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string


class BaselineSnapshot(Base):
    __tablename__ = "baseline_snapshots"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    pipeline_version: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    retrieval_score_p50: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_score_p95: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_length_p50: Mapped[float | None] = mapped_column(Float, nullable=True)
    faithfulness_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_relevance_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_thumbsdown_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
