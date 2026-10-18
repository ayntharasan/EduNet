#!/usr/bin/env python3
"""Deterministic synthetic campus dataset generator.

Generates reproducible demo data for Green Valley University (fictional).
Fixed random seed = 42 ensures identical output on every run.

Buildings: 5 fictional campus buildings
Period: 180 days (approx 6 months)
Anomaly: Injected high-consumption spike in Building A (days 60–75)
Intervention: Recorded on day 90; post-intervention readings from day 91
Missing data: Days 45–47 have no electricity readings (meter downtime)

ALL records are labelled is_synthetic=True.
NEVER mix with real campus data without preserving this label.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# Fictional campus buildings
BUILDINGS = [
    {"id": 1, "name": "Main Academic Block", "type": "academic",    "area_m2": 8000,  "capacity": 600},
    {"id": 2, "name": "Science Laboratory",   "type": "laboratory",  "area_m2": 3000,  "capacity": 200},
    {"id": 3, "name": "Student Hostel A",     "type": "residential", "area_m2": 4500,  "capacity": 300},
    {"id": 4, "name": "Administrative Block", "type": "office",      "area_m2": 2000,  "capacity": 100},
    {"id": 5, "name": "Sports Complex",       "type": "sports",      "area_m2": 6000,  "capacity": 400},
]

START_DATE = date(2024, 1, 1)
DAYS = 180
ANOMALY_START = 60   # day index (0-based): artificial spike starts
ANOMALY_END = 75     # spike ends
MISSING_DAYS = {45, 46, 47}  # simulated meter downtime (0-based indices)
INTERVENTION_DAY = 90  # day when corrective action is recorded


def generate_all():
    rng = np.random.default_rng(SEED)

    elec_rows = []
    water_rows = []
    waste_rows = []

    dates = [START_DATE + timedelta(days=i) for i in range(DAYS)]

    for day_idx, dt in enumerate(dates):
        is_weekend = dt.weekday() >= 5
        # Seasonal factor (slightly lower in winter months: Jan=1.0, Jul=0.85)
        month_factor = 1.0 - 0.015 * (dt.month - 1) if dt.month <= 7 else 1.0 - 0.015 * (13 - dt.month)

        for bldg in BUILDINGS:
            bid = bldg["id"]
            btype = bldg["type"]

            # --------------- ELECTRICITY ---------------
            if day_idx not in MISSING_DAYS:
                base_kwh = _base_electricity(btype, is_weekend)
                # Inject anomaly in Building 1 during anomaly window
                anomaly_factor = 1.0
                if bid == 1 and ANOMALY_START <= day_idx < ANOMALY_END:
                    anomaly_factor = 2.1  # 110% above normal — deliberately injected
                # Intervention: Building 1 consumption drops after day 90
                intervention_factor = 1.0
                if bid == 1 and day_idx >= INTERVENTION_DAY:
                    intervention_factor = 0.82  # ~18% reduction post-intervention

                kwh = (
                    base_kwh
                    * anomaly_factor
                    * intervention_factor
                    * month_factor
                    * (1 + rng.normal(0, 0.05))
                )
                kwh = max(kwh, 0.0)

                elec_rows.append({
                    "timestamp": dt.isoformat(),
                    "building_id": bid,
                    "building_name": bldg["name"],
                    "meter_id": f"MTR-{bid:02d}",
                    "consumption_kwh": round(kwh, 3),
                    "occupancy_count": _occupancy(btype, is_weekend, rng),
                    "floor_area_m2": bldg["area_m2"],
                    "source_type": "synthetic_demo",
                    "source_reference": "generate_demo_data.py seed=42",
                    "is_synthetic": True,
                    "anomaly_injected": (bid == 1 and ANOMALY_START <= day_idx < ANOMALY_END),
                    "intervention_applied": (bid == 1 and day_idx >= INTERVENTION_DAY),
                })

            # --------------- WATER ---------------
            base_litres = _base_water(btype, is_weekend)
            # Inject water leak candidate in Building 3 (hostel) days 30-50
            water_factor = 1.0
            if bid == 3 and 30 <= day_idx < 50:
                water_factor = 1.7  # elevated — leak candidate
            litres = base_litres * water_factor * month_factor * (1 + rng.normal(0, 0.07))
            litres = max(litres, 0.0)
            water_rows.append({
                "measurement_date": dt.isoformat(),
                "building_id": bid,
                "building_name": bldg["name"],
                "consumption_litres": round(litres, 1),
                "occupancy_count": _occupancy(btype, is_weekend, rng),
                "source_type": "synthetic_demo",
                "source_reference": "generate_demo_data.py seed=42",
                "is_synthetic": True,
            })

            # --------------- WASTE (weekly) ---------------
            if dt.weekday() == 0:  # Monday only
                total_kg = _base_waste(btype) * (1 + rng.normal(0, 0.1)) * 7
                total_kg = max(total_kg, 0.0)
                wet = total_kg * rng.uniform(0.35, 0.45)
                dry = total_kg * rng.uniform(0.20, 0.30)
                residual = total_kg - wet - dry
                waste_rows.append({
                    "measurement_date": dt.isoformat(),
                    "building_id": bid,
                    "building_name": bldg["name"],
                    "wet_waste_kg": round(wet, 2),
                    "dry_recyclable_kg": round(dry, 2),
                    "residual_waste_kg": round(residual, 2),
                    "special_waste_kg": 0.0,
                    "total_waste_kg": round(total_kg, 2),
                    "source_type": "synthetic_demo",
                    "source_reference": "generate_demo_data.py seed=42",
                    "is_synthetic": True,
                })

    elec_df = pd.DataFrame(elec_rows)
    water_df = pd.DataFrame(water_rows)
    waste_df = pd.DataFrame(waste_rows)

    # Save CSVs
    elec_path = DEMO_DIR / "electricity_demo.csv"
    water_path = DEMO_DIR / "water_demo.csv"
    waste_path = DEMO_DIR / "waste_demo.csv"
    bldg_path = DEMO_DIR / "buildings_demo.json"

    elec_df.to_csv(elec_path, index=False)
    water_df.to_csv(water_path, index=False)
    waste_df.to_csv(waste_path, index=False)

    with open(bldg_path, "w") as f:
        json.dump(BUILDINGS, f, indent=2)

    # Save manifest
    manifest = {
        "description": "Synthetic demo campus dataset for Green Campus Sustainability Auditor",
        "generated_at": date.today().isoformat(),
        "seed": SEED,
        "campus_name": "Green Valley University (SYNTHETIC DEMO)",
        "is_synthetic": True,
        "warning": (
            "ALL DATA IS ARTIFICIALLY GENERATED. "
            "Do not use for real environmental reporting, regulatory compliance, or research."
        ),
        "buildings": len(BUILDINGS),
        "days": DAYS,
        "start_date": START_DATE.isoformat(),
        "end_date": (START_DATE + timedelta(days=DAYS - 1)).isoformat(),
        "electricity_records": len(elec_df),
        "water_records": len(water_df),
        "waste_records": len(waste_df),
        "injected_anomalies": [
            {
                "type": "electricity_spike",
                "building_id": 1,
                "building_name": "Main Academic Block",
                "day_start": ANOMALY_START,
                "day_end": ANOMALY_END,
                "date_start": (START_DATE + timedelta(days=ANOMALY_START)).isoformat(),
                "date_end": (START_DATE + timedelta(days=ANOMALY_END)).isoformat(),
                "factor": 2.1,
                "description": "Simulated HVAC fault causing 110% above-normal consumption",
            },
            {
                "type": "water_elevated",
                "building_id": 3,
                "building_name": "Student Hostel A",
                "day_start": 30,
                "day_end": 50,
                "date_start": (START_DATE + timedelta(days=30)).isoformat(),
                "date_end": (START_DATE + timedelta(days=50)).isoformat(),
                "factor": 1.7,
                "description": "Simulated water leak candidate (persistently elevated, not confirmed leak)",
            },
        ],
        "missing_periods": [
            {
                "category": "electricity",
                "building_ids": "all",
                "days": sorted(MISSING_DAYS),
                "dates": [(START_DATE + timedelta(days=d)).isoformat() for d in sorted(MISSING_DAYS)],
                "description": "Simulated meter downtime",
            }
        ],
        "intervention": {
            "day": INTERVENTION_DAY,
            "date": (START_DATE + timedelta(days=INTERVENTION_DAY)).isoformat(),
            "building_id": 1,
            "building_name": "Main Academic Block",
            "description": "Simulated corrective action: HVAC schedule optimization",
            "post_intervention_factor": 0.82,
            "note": "Post-intervention consumption is ~18% lower than pre-anomaly baseline.",
        },
        "files": {
            "electricity": str(elec_path),
            "water": str(water_path),
            "waste": str(waste_path),
            "buildings": str(bldg_path),
        },
    }
    manifest_path = DEMO_DIR / "demo_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print("SYNTHETIC DEMO DATA GENERATED")
    print(f"{'='*60}")
    print(f"[WARNING] ALL DATA IS SYNTHETIC - Do not use for real reporting")
    print(f"Campus: Green Valley University (DEMO)")
    print(f"Period: {START_DATE} to {START_DATE + timedelta(days=DAYS-1)}")
    print(f"Electricity records: {len(elec_df)}")
    print(f"Water records:       {len(water_df)}")
    print(f"Waste records:       {len(waste_df)}")
    print(f"\nInjected anomaly: Building 1 electricity spike, days {ANOMALY_START}–{ANOMALY_END}")
    print(f"Missing data: Days {sorted(MISSING_DAYS)} (electricity only)")
    print(f"Intervention: Day {INTERVENTION_DAY}, Building 1")
    print(f"\nFiles saved to: {DEMO_DIR}")
    print(f"{'='*60}\n")

    return elec_df, water_df, waste_df


def _base_electricity(btype: str, is_weekend: bool) -> float:
    """Base daily electricity consumption by building type (kWh)."""
    base = {
        "academic": 850.0,
        "laboratory": 420.0,
        "residential": 280.0,
        "office": 180.0,
        "sports": 120.0,
    }.get(btype, 200.0)
    return base * 0.45 if is_weekend else base


def _base_water(btype: str, is_weekend: bool) -> float:
    """Base daily water consumption by building type (litres)."""
    base = {
        "academic": 12000.0,
        "laboratory": 5000.0,
        "residential": 15000.0,
        "office": 3500.0,
        "sports": 8000.0,
    }.get(btype, 4000.0)
    return base * 0.6 if is_weekend else base


def _base_waste(btype: str) -> float:
    """Base daily waste generation by building type (kg)."""
    return {
        "academic": 45.0,
        "laboratory": 15.0,
        "residential": 60.0,
        "office": 12.0,
        "sports": 20.0,
    }.get(btype, 20.0)


def _occupancy(btype: str, is_weekend: bool, rng: np.random.Generator) -> int:
    base = {
        "academic": 400,
        "laboratory": 80,
        "residential": 250,
        "office": 60,
        "sports": 150,
    }.get(btype, 100)
    val = base * 0.3 if is_weekend else base
    return max(0, int(val + rng.normal(0, val * 0.1)))


if __name__ == "__main__":
    generate_all()
