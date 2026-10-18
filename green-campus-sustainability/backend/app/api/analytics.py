"""Analytics summary endpoints — energy, water, waste, dashboard."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path

from backend.app.database.session import get_db
from backend.app.models.electricity import ElectricityMeasurement
from backend.app.models.water import WaterMeasurement
from backend.app.models.waste import WasteMeasurement
from backend.app.analytics.energy import compute_energy_kpis, compute_emissions
from backend.app.analytics.water import compute_water_kpis
from backend.app.analytics.waste_analytics import compute_waste_kpis
from backend.app.core.config import settings

router = APIRouter()


def _demo_note(df: pd.DataFrame) -> str:
    if df.empty:
        return "No data available."
    if "is_synthetic" in df.columns and bool(df["is_synthetic"].any()):
        return "[SYNTHETIC DEMO DATA] These figures are generated from synthetic data for demonstration purposes only. Not real campus measurements."
    return "Data loaded from user-uploaded measurements."


def _load_elec(db: Session, start, end) -> pd.DataFrame:
    q = db.query(ElectricityMeasurement)
    if start:
        q = q.filter(ElectricityMeasurement.timestamp >= start)
    if end:
        q = q.filter(ElectricityMeasurement.timestamp <= end)
    rows = q.all()
    if not rows:
        p = Path("data/demo/electricity_demo.csv")
        return pd.read_csv(p) if p.exists() else pd.DataFrame()
    return pd.DataFrame([{
        "timestamp": r.timestamp, "building_id": r.building_id,
        "consumption_kwh": r.consumption_kwh, "occupancy_count": r.occupancy_count,
        "floor_area_m2": r.floor_area_m2, "is_synthetic": r.is_synthetic,
    } for r in rows])


def _load_water(db: Session, start, end) -> pd.DataFrame:
    q = db.query(WaterMeasurement)
    if start:
        q = q.filter(WaterMeasurement.measurement_date >= start)
    if end:
        q = q.filter(WaterMeasurement.measurement_date <= end)
    rows = q.all()
    if not rows:
        p = Path("data/demo/water_demo.csv")
        return pd.read_csv(p) if p.exists() else pd.DataFrame()
    return pd.DataFrame([{
        "measurement_date": r.measurement_date, "building_id": r.building_id,
        "consumption_litres": r.consumption_litres, "is_synthetic": r.is_synthetic,
    } for r in rows])


def _load_waste(db: Session, start, end) -> pd.DataFrame:
    q = db.query(WasteMeasurement)
    if start:
        q = q.filter(WasteMeasurement.measurement_date >= start)
    if end:
        q = q.filter(WasteMeasurement.measurement_date <= end)
    rows = q.all()
    if not rows:
        p = Path("data/demo/waste_demo.csv")
        return pd.read_csv(p) if p.exists() else pd.DataFrame()
    return pd.DataFrame([{
        "measurement_date": r.measurement_date, "building_id": r.building_id,
        "wet_waste_kg": r.wet_waste_kg, "dry_recyclable_kg": r.dry_recyclable_kg,
        "residual_waste_kg": r.residual_waste_kg, "total_waste_kg": r.total_waste_kg,
        "is_synthetic": r.is_synthetic,
    } for r in rows])


@router.get("/energy")
def energy_kpis(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    population: Optional[int] = Query(None),
    area_m2: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    df = _load_elec(db, start, end)
    kpis = compute_energy_kpis(df, population=population, area_m2=area_m2)
    if kpis.get("total_kwh"):
        kpis["emissions"] = compute_emissions(
            kpis["total_kwh"], settings.DEFAULT_EMISSION_FACTOR, settings.EMISSION_FACTOR_SOURCE
        )
    kpis["data_source_note"] = _demo_note(df)
    return kpis


@router.get("/water")
def water_kpis(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    population: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    df = _load_water(db, start, end)
    kpis = compute_water_kpis(df, population=population)
    kpis["data_source_note"] = _demo_note(df)
    return kpis


@router.get("/waste")
def waste_kpis(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    df = _load_waste(db, start, end)
    kpis = compute_waste_kpis(df)
    kpis["data_source_note"] = _demo_note(df)
    return kpis


@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db)):
    """Combined KPI summary for the dashboard."""
    elec_df = _load_elec(db, None, None)
    water_df = _load_water(db, None, None)
    waste_df = _load_waste(db, None, None)

    energy = compute_energy_kpis(elec_df)
    water = compute_water_kpis(water_df)
    waste = compute_waste_kpis(waste_df)
    emissions = {}
    if energy.get("total_kwh"):
        emissions = compute_emissions(
            energy["total_kwh"], settings.DEFAULT_EMISSION_FACTOR, settings.EMISSION_FACTOR_SOURCE
        )

    is_demo = (
        not elec_df.empty
        and "is_synthetic" in elec_df.columns
        and bool(elec_df["is_synthetic"].any())
    )

    return {
        "is_demo_data": is_demo,
        "demo_warning": (
            "[SYNTHETIC DEMO DATA] All figures below are from synthetic demonstration data. "
            "Not real campus measurements."
        ) if is_demo else None,
        "energy": energy,
        "water": water,
        "waste": waste,
        "emissions": emissions,
    }
