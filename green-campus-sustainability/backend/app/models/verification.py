"""Verification result model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_id: Mapped[str] = mapped_column(String(64), ForeignKey("actions.action_id"), nullable=False, index=True)
    baseline_period_start: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    baseline_period_end: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    post_action_period_start: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    post_action_period_end: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_action_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result: Mapped[str] = mapped_column(String(30), default="insufficient_data")  # improved, no_change, regressed, insufficient_data
    confidence: Mapped[str] = mapped_column(String(20), default="low")  # high, medium, low
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    caveats: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
