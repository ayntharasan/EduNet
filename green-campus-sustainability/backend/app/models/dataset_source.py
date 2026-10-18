"""Dataset source tracking model."""
import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base


class DatasetSource(Base):
    __tablename__ = "dataset_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # upload, demo, external
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    original_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    licence: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
