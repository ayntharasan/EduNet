"""Waste measurement model."""
import datetime
from sqlalchemy import String, Float, Integer, DateTime, Date, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class WasteMeasurement(Base):
    __tablename__ = "waste_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    measurement_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    building_id: Mapped[int] = mapped_column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    wet_waste_kg: Mapped[float] = mapped_column(Float, default=0.0)
    dry_recyclable_kg: Mapped[float] = mapped_column(Float, default=0.0)
    residual_waste_kg: Mapped[float] = mapped_column(Float, default=0.0)
    special_waste_kg: Mapped[float] = mapped_column(Float, default=0.0)
    total_waste_kg: Mapped[float] = mapped_column(Float, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="user_input")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    dataset_source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dataset_sources.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
