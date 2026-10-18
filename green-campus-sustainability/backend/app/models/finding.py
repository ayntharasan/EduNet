"""Sustainability finding model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    finding_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("audit_runs.run_id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # electricity, water, waste, emissions
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low, info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of evidence items
    alternative_explanations: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    affected_period_start: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    affected_period_end: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    building_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("buildings.id"), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")  # high, medium, low
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    investigation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open")  # open, investigating, resolved, dismissed
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
