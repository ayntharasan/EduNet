"""Application settings model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campus_name: Mapped[str] = mapped_column(String(300), default="My Campus")
    campus_area_m2: Mapped[float | None] = mapped_column(Integer, nullable=True)
    total_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_staff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ollama_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ollama_model: Mapped[str] = mapped_column(String(200), default="")
    ollama_base_url: Mapped[str] = mapped_column(String(500), default="")
    priority_weight_impact: Mapped[float] = mapped_column(Integer, default=40)
    priority_weight_urgency: Mapped[float] = mapped_column(Integer, default=25)
    priority_weight_confidence: Mapped[float] = mapped_column(Integer, default=20)
    priority_weight_feasibility: Mapped[float] = mapped_column(Integer, default=15)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
