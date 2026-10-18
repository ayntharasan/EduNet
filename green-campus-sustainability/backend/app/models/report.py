"""Audit report model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("audit_runs.run_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="html")  # html, pdf
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(100), default="reporting_agent")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
