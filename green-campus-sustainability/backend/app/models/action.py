"""Action / recommendation model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("audit_runs.run_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    finding_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    responsible_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost_category: Mapped[str] = mapped_column(String(50), default="zero-cost")  # zero-cost, low-cost, medium-cost, requires-quotation
    implementation_difficulty: Mapped[str] = mapped_column(String(20), default="easy")  # easy, medium, hard
    expected_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_horizon: Mapped[str] = mapped_column(String(50), default="short-term")  # immediate, short-term, medium-term, long-term
    verification_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_rank: Mapped[int] = mapped_column(Integer, default=0)
    priority_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft, approved, in-progress, completed, verified, rejected
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_date: Mapped[datetime.date | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ActionStatusHistory(Base):
    __tablename__ = "action_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_id: Mapped[str] = mapped_column(String(64), ForeignKey("actions.action_id"), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(200), default="user")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
