"""Application settings endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.app_settings import AppSettings
from backend.app.models.emission_factor import EmissionFactor

router = APIRouter()


class SettingsUpdate(BaseModel):
    campus_name: Optional[str] = None
    total_students: Optional[int] = None
    total_staff: Optional[int] = None
    campus_area_m2: Optional[float] = None
    ollama_enabled: Optional[bool] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    s = db.query(AppSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="Settings not initialized. Restart the server to seed defaults.")
    ef = db.query(EmissionFactor).filter(EmissionFactor.is_default == True).first()  # noqa: E712
    return {
        "campus_name": s.campus_name,
        "total_students": s.total_students,
        "total_staff": s.total_staff,
        "campus_area_m2": s.campus_area_m2,
        "ollama_enabled": s.ollama_enabled,
        "ollama_model": s.ollama_model,
        "ollama_base_url": s.ollama_base_url,
        "emission_factor": {
            "value": ef.factor_value if ef else 0.716,
            "unit": ef.unit if ef else "kgCO2e/kWh",
            "source": ef.source if ef else "CEA CO2 Baseline Database Version 18 (2022-23)",
        },
    }


@router.patch("")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    s = db.query(AppSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="Settings not initialized.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return {"message": "Settings updated.", "campus_name": s.campus_name}
