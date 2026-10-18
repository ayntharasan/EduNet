"""Electricity measurement model."""
import datetime
from sqlalchemy import String, Float, Integer, DateTime, Date, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class ElectricityMeasurement(Base):
    __tablename__ = "electricity_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    building_id: Mapped[int] = mapped_column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    meter_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    occupancy_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="user_input")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dataset_source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dataset_sources.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
