"""Water consumption analytics and KPI calculations."""

from __future__ import annotations
import logging
from typing import Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# WHO benchmark: 50-100 L per person per day for basic needs
# University campus benchmark: 50-150 L per person per day (varies by amenities)
LEAK_SUSPICIOUS_FACTOR = 1.5  # Flag if weekend/holiday use > 150% of weekday avg
MIN_OBSERVATIONS_FOR_TREND = 7


def compute_water_kpis(df: pd.DataFrame, population: int | None = None) -> dict[str, Any]:
    """Compute water consumption KPIs."""
    if df.empty:
        return {"error": "No water data available.", "total_litres": None}

    df = df.copy()
    df["measurement_date"] = pd.to_datetime(df["measurement_date"])

    total_litres = float(df["consumption_litres"].sum())
    total_kl = round(total_litres / 1000, 2)
    avg_daily_litres = float(df.groupby("measurement_date")["consumption_litres"].sum().mean())
    date_range_days = (df["measurement_date"].max() - df["measurement_date"].min()).days + 1

    litres_per_person_per_day = None
    if population and population > 0 and date_range_days > 0:
        litres_per_person_per_day = round(total_litres / population / date_range_days, 2)

    # Monthly breakdown
    df["month"] = df["measurement_date"].dt.to_period("M")
    monthly = (
        df.groupby("month")["consumption_litres"]
        .sum()
        .reset_index()
        .rename(columns={"consumption_litres": "total_litres"})
    )
    monthly["month"] = monthly["month"].astype(str)

    # Leak suspicion: unusually persistent high consumption
    leak_suspects = detect_leak_candidates(df)

    return {
        "total_litres": round(total_litres, 2),
        "total_kl": total_kl,
        "avg_daily_litres": round(avg_daily_litres, 2),
        "litres_per_person_per_day": litres_per_person_per_day,
        "record_count": len(df),
        "date_range_days": date_range_days,
        "monthly_breakdown": monthly.to_dict(orient="records"),
        "leak_suspect_periods": leak_suspects,
        "unit": "litres",
        "notes": "Litres per person per day requires reliable occupancy data.",
    }


def detect_leak_candidates(df: pd.DataFrame, consecutive_days: int = 3, multiplier: float = 1.5) -> list[dict]:
    """Identify periods with persistently elevated water use that may indicate leaks.

    Method: Flag periods where consumption exceeds 1.5x the rolling median for
    more than `consecutive_days` consecutive days.
    These are CANDIDATES for investigation, not confirmed leaks.
    """
    if len(df) < MIN_OBSERVATIONS_FOR_TREND:
        return []

    daily = df.groupby("measurement_date")["consumption_litres"].sum().reset_index()
    daily = daily.sort_values("measurement_date")
    rolling_median = daily["consumption_litres"].rolling(window=7, min_periods=3).median()
    daily["rolling_median"] = rolling_median
    daily["elevated"] = daily["consumption_litres"] > (rolling_median * multiplier)

    suspects = []
    streak = 0
    start_date = None
    for _, row in daily.iterrows():
        if row["elevated"]:
            if streak == 0:
                start_date = row["measurement_date"]
            streak += 1
        else:
            if streak >= consecutive_days and start_date is not None:
                suspects.append({
                    "start": str(start_date.date() if hasattr(start_date, 'date') else start_date),
                    "end": str(row["measurement_date"].date() if hasattr(row["measurement_date"], 'date') else row["measurement_date"]),
                    "consecutive_days": streak,
                    "note": "Elevated usage — inspection recommended, not a confirmed leak.",
                })
            streak = 0
            start_date = None
    return suspects
