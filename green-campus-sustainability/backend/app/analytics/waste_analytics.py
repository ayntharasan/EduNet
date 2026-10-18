"""Waste measurement analytics and KPI calculations."""

from __future__ import annotations
import logging
from typing import Any
import pandas as pd

logger = logging.getLogger(__name__)


def compute_waste_kpis(df: pd.DataFrame, population: int | None = None) -> dict[str, Any]:
    """Compute waste KPIs from measurement data."""
    if df.empty:
        return {"error": "No waste data available.", "total_kg": None}

    df = df.copy()
    df["measurement_date"] = pd.to_datetime(df["measurement_date"])

    total_kg = float(df["total_waste_kg"].sum())
    total_wet = float(df["wet_waste_kg"].sum())
    total_dry = float(df["dry_recyclable_kg"].sum())
    total_residual = float(df["residual_waste_kg"].sum())
    total_special = float(df["special_waste_kg"].sum()) if "special_waste_kg" in df.columns else 0.0

    # Diversion/recycling rate: (wet + dry recyclable) / total * 100
    # Only computed when numerator and denominator are clearly defined
    diversion_rate = None
    if total_kg > 0:
        diversion_rate = round((total_wet + total_dry) / total_kg * 100, 2)

    per_person_kg = None
    if population and population > 0:
        per_person_kg = round(total_kg / population, 2)

    # Monthly
    df["month"] = df["measurement_date"].dt.to_period("M")
    monthly = (
        df.groupby("month")["total_waste_kg"]
        .sum()
        .reset_index()
        .rename(columns={"total_waste_kg": "total_kg"})
    )
    monthly["month"] = monthly["month"].astype(str)

    return {
        "total_kg": round(total_kg, 2),
        "total_wet_kg": round(total_wet, 2),
        "total_dry_recyclable_kg": round(total_dry, 2),
        "total_residual_kg": round(total_residual, 2),
        "total_special_kg": round(total_special, 2),
        "diversion_rate_pct": diversion_rate,
        "per_person_kg": per_person_kg,
        "record_count": len(df),
        "monthly_breakdown": monthly.to_dict(orient="records"),
        "unit": "kg",
        "notes": (
            "Diversion rate = (wet + dry recyclable) / total_waste * 100. "
            "Requires accurate category-level measurements to be meaningful."
        ),
    }
