"""Building model."""
import datetime
from sqlalchemy import String, Float, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    building_type: Mapped[str] = mapped_column(String(100), nullable=False, default="academic")
    floor_area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    student_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    staff_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
