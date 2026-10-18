"""Database initialization — creates all tables and seeds default data."""

import logging
from sqlalchemy.orm import Session
from backend.app.database.session import engine, Base, SessionLocal
from backend.app.core.config import settings

# Import all models so Base knows about them
from backend.app.models import (
    building, electricity, water, waste, dataset_source,
    audit_run, agent_execution, finding, action, verification,
    emission_factor, app_settings, report
)

logger = logging.getLogger(__name__)


def init_db():
    """Create all database tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        _seed_defaults(db)
    finally:
        db.close()
    logger.info("Database initialization complete.")


def _seed_defaults(db: Session):
    """Seed default emission factor and app settings if not present."""
    from backend.app.models.emission_factor import EmissionFactor
    from backend.app.models.app_settings import AppSettings

    if not db.query(EmissionFactor).filter_by(is_default=True).first():
        ef = EmissionFactor(
            name="India CEA Grid Emission Factor 2022-23",
            factor_value=settings.DEFAULT_EMISSION_FACTOR,
            unit=settings.EMISSION_FACTOR_UNIT,
            source=settings.EMISSION_FACTOR_SOURCE,
            geography="India",
            publication_year=2023,
            notes="CEA CO2 Baseline Database for the Indian Power Sector, Version 18. "
                  "Use the most current official factor for your reporting year.",
            is_default=True,
        )
        db.add(ef)
        logger.info("Seeded default emission factor.")

    if not db.query(AppSettings).first():
        s = AppSettings(
            campus_name=settings.DEMO_CAMPUS_NAME,
            ollama_enabled=False,
            ollama_model="",
            ollama_base_url="",
        )
        db.add(s)
        logger.info("Seeded default app settings.")

    db.commit()
