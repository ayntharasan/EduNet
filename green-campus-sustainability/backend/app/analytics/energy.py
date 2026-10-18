"""Energy consumption analytics and KPI calculations.

All calculation formulas are documented inline.
"""

from __future__ import annotations
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def safe_pct_change(current: float, baseline: float) -> float | None:
    """Calculate percentage change safely.

    Formula: ((current - baseline) / |baseline|) * 100
    Returns None when baseline is zero (undefined) or when either value is NaN.
    """
    if baseline is None or current is None:
        return None
    if baseline == 0:
        logger.warning("Percentage change undefined: baseline is zero.")
        return None
    return ((current - baseline) / abs(baseline)) * 100


def compute_energy_kpis(df: pd.DataFrame, population: int | None = None, area_m2: float | None = None) -> dict[str, Any]:
    """Compute energy KPIs from a DataFrame of electricity measurements.

    Expected columns: timestamp (date), consumption_kwh, building_id (optional),
    occupancy_count (optional), floor_area_m2 (optional).

    Returns a dict of computed KPIs with units and notes.
    """
    if df.empty:
        return {"error": "No electricity data available.", "total_kwh": None}

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    total_kwh = float(df["consumption_kwh"].sum())
    avg_daily_kwh = float(df.groupby("timestamp")["consumption_kwh"].sum().mean())
    max_daily_kwh = float(df.groupby("timestamp")["consumption_kwh"].sum().max())
    min_daily_kwh = float(df.groupby("timestamp")["consumption_kwh"].sum().min())
    record_count = int(len(df))
    date_range_days = (df["timestamp"].max() - df["timestamp"].min()).days + 1

    # kWh per person (where population data exists)
    kwh_per_person = None
    pop_source = None
    if population and population > 0:
        kwh_per_person = round(total_kwh / population, 2)
        pop_source = "provided"
    elif "occupancy_count" in df.columns and df["occupancy_count"].notna().any():
        avg_occupancy = df["occupancy_count"].dropna().mean()
        if avg_occupancy > 0:
            kwh_per_person = round(total_kwh / avg_occupancy, 2)
            pop_source = "average_occupancy"

    # kWh per m2 (where area data exists)
    kwh_per_m2 = None
    if area_m2 and area_m2 > 0:
        kwh_per_m2 = round(total_kwh / area_m2, 2)
    elif "floor_area_m2" in df.columns and df["floor_area_m2"].notna().any():
        total_area = df["floor_area_m2"].dropna().sum()
        if total_area > 0:
            kwh_per_m2 = round(total_kwh / total_area, 2)

    # Monthly aggregation
    df["month"] = df["timestamp"].dt.to_period("M")
    monthly = (
        df.groupby("month")["consumption_kwh"]
        .sum()
        .reset_index()
        .rename(columns={"consumption_kwh": "total_kwh"})
    )
    monthly["month"] = monthly["month"].astype(str)
    monthly_data = monthly.to_dict(orient="records")

    # Peak consumption periods (top 10% of daily totals)
    daily = df.groupby("timestamp")["consumption_kwh"].sum().reset_index()
    threshold_90 = daily["consumption_kwh"].quantile(0.9)
    peak_days = daily[daily["consumption_kwh"] >= threshold_90]["timestamp"].dt.strftime("%Y-%m-%d").tolist()

    return {
        "total_kwh": round(total_kwh, 2),
        "avg_daily_kwh": round(avg_daily_kwh, 2),
        "max_daily_kwh": round(max_daily_kwh, 2),
        "min_daily_kwh": round(min_daily_kwh, 2),
        "kwh_per_person": kwh_per_person,
        "kwh_per_person_source": pop_source,
        "kwh_per_m2": kwh_per_m2,
        "record_count": record_count,
        "date_range_days": date_range_days,
        "monthly_breakdown": monthly_data,
        "peak_days_count": len(peak_days),
        "unit": "kWh",
        "notes": "All figures are totals across all buildings in the selected period.",
    }


def compute_baseline_comparison(
    current_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
) -> dict[str, Any]:
    """Compare current period energy consumption against a baseline period."""
    if current_df.empty:
        return {"error": "No current period data.", "pct_change": None}
    if baseline_df.empty:
        return {"error": "No baseline period data. Cannot compute comparison.", "pct_change": None}

    current_total = float(current_df["consumption_kwh"].sum())
    baseline_total = float(baseline_df["consumption_kwh"].sum())
    pct_change = safe_pct_change(current_total, baseline_total)

    return {
        "current_total_kwh": round(current_total, 2),
        "baseline_total_kwh": round(baseline_total, 2),
        "absolute_change_kwh": round(current_total - baseline_total, 2),
        "pct_change": round(pct_change, 2) if pct_change is not None else None,
        "interpretation": _interpret_pct_change(pct_change),
    }


def _interpret_pct_change(pct: float | None) -> str:
    if pct is None:
        return "Cannot compute: baseline is zero or missing."
    if pct > 20:
        return "Significantly higher than baseline — investigate causes."
    elif pct > 5:
        return "Moderately higher than baseline."
    elif pct < -10:
        return "Significantly lower than baseline — possible improvement or data gap."
    elif pct < -3:
        return "Slightly lower than baseline."
    return "Within normal range of baseline."


def detect_anomalies_statistical(df: pd.DataFrame, z_threshold: float = 2.5) -> pd.DataFrame:
    """Flag anomalous daily consumption using Z-score method.

    Formula: z = (value - mean) / std
    Values with |z| > z_threshold are flagged.
    Returns a DataFrame with an 'is_anomaly' boolean column and 'z_score'.
    """
    if df.empty or len(df) < 5:
        return df.assign(is_anomaly=False, z_score=None)

    daily = df.groupby("timestamp")["consumption_kwh"].sum().reset_index()
    mean_val = daily["consumption_kwh"].mean()
    std_val = daily["consumption_kwh"].std()

    if std_val == 0 or np.isnan(std_val):
        daily["is_anomaly"] = False
        daily["z_score"] = 0.0
    else:
        daily["z_score"] = (daily["consumption_kwh"] - mean_val) / std_val
        daily["is_anomaly"] = daily["z_score"].abs() > z_threshold

    return daily


def compute_emissions(kwh: float, emission_factor: float, factor_source: str = "") -> dict[str, Any]:
    """Estimate CO2-equivalent emissions from electricity consumption.

    Formula: emissions_kgCO2e = electricity_kWh * emission_factor_kgCO2e_per_kWh
    Formula: emissions_tCO2e = emissions_kgCO2e / 1000

    The emission factor must be sourced from a verified official publication.
    This function produces ESTIMATES, not certified carbon inventory figures.
    """
    if kwh is None or kwh < 0:
        return {"error": "Invalid kWh value.", "kg_co2e": None}
    if emission_factor is None or emission_factor <= 0:
        return {"error": "Invalid or missing emission factor.", "kg_co2e": None}

    kg_co2e = kwh * emission_factor
    t_co2e = kg_co2e / 1000

    return {
        "electricity_kwh": round(kwh, 2),
        "emission_factor": emission_factor,
        "emission_factor_source": factor_source,
        "kg_co2e": round(kg_co2e, 2),
        "t_co2e": round(t_co2e, 4),
        "unit": "kgCO2e",
        "disclaimer": (
            "This is an ESTIMATE based on the electricity grid emission factor. "
            "It covers Scope 2 (indirect) emissions from purchased electricity only. "
            "It does not include direct combustion, refrigerants, transport, or other sources. "
            "Consult a certified GHG practitioner for official reporting."
        ),
    }
