"""Verification endpoints — run post-action verification and retrieve results."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path

from backend.app.database.session import get_db
from backend.app.models.action import Action
from backend.app.models.verification import Verification
from backend.app.models.electricity import ElectricityMeasurement
from backend.app.models.water import WaterMeasurement
from backend.app.agents.orchestrator import AuditOrchestrator
from backend.app.schemas.agent_schemas import Category

router = APIRouter()


class VerificationRequest(BaseModel):
    action_id: str
    run_id: str
    baseline_start: date
    baseline_end: date
    post_action_start: date
    post_action_end: date
    metric: str = "electricity"  # electricity | water
    building_ids: Optional[list[int]] = None


@router.post("/run")
def run_verification(payload: VerificationRequest, db: Session = Depends(get_db)):
    """Run verification for a completed action.

    Requires >=7 days of post-action data per period.
    Never auto-approves — measured reduction must be ≥5%.
    """
    action = db.query(Action).filter(Action.action_id == payload.action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")

    orchestrator = AuditOrchestrator(db)

    if payload.metric == "electricity":
        pre_q = db.query(ElectricityMeasurement).filter(
            ElectricityMeasurement.timestamp >= payload.baseline_start,
            ElectricityMeasurement.timestamp <= payload.baseline_end,
        )
        post_q = db.query(ElectricityMeasurement).filter(
            ElectricityMeasurement.timestamp >= payload.post_action_start,
            ElectricityMeasurement.timestamp <= payload.post_action_end,
        )
        if payload.building_ids:
            pre_q = pre_q.filter(ElectricityMeasurement.building_id.in_(payload.building_ids))
            post_q = post_q.filter(ElectricityMeasurement.building_id.in_(payload.building_ids))
        pre_list = pre_q.all()
        post_list = post_q.all()

        if not pre_list and not post_list:
            demo = Path("data/demo/electricity_demo.csv")
            if demo.exists():
                df = pd.read_csv(demo)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                pre_df = df[df["timestamp"].dt.date.between(payload.baseline_start, payload.baseline_end)][
                    ["timestamp", "building_id", "consumption_kwh", "is_synthetic"]
                ].copy()
                post_df = df[df["timestamp"].dt.date.between(payload.post_action_start, payload.post_action_end)][
                    ["timestamp", "building_id", "consumption_kwh", "is_synthetic"]
                ].copy()
            else:
                pre_df = pd.DataFrame()
                post_df = pd.DataFrame()
        else:
            pre_df = pd.DataFrame([{
                "timestamp": r.timestamp, "building_id": r.building_id,
                "consumption_kwh": r.consumption_kwh, "is_synthetic": r.is_synthetic,
            } for r in pre_list])
            post_df = pd.DataFrame([{
                "timestamp": r.timestamp, "building_id": r.building_id,
                "consumption_kwh": r.consumption_kwh, "is_synthetic": r.is_synthetic,
            } for r in post_list])
        category = Category.ELECTRICITY

    elif payload.metric == "water":
        pre_list = db.query(WaterMeasurement).filter(
            WaterMeasurement.measurement_date >= payload.baseline_start,
            WaterMeasurement.measurement_date <= payload.baseline_end,
        ).all()
        post_list = db.query(WaterMeasurement).filter(
            WaterMeasurement.measurement_date >= payload.post_action_start,
            WaterMeasurement.measurement_date <= payload.post_action_end,
        ).all()
        pre_df = pd.DataFrame([{
            "measurement_date": r.measurement_date, "building_id": r.building_id,
            "consumption_litres": r.consumption_litres, "is_synthetic": r.is_synthetic,
        } for r in pre_list]) if pre_list else pd.DataFrame()
        post_df = pd.DataFrame([{
            "measurement_date": r.measurement_date, "building_id": r.building_id,
            "consumption_litres": r.consumption_litres, "is_synthetic": r.is_synthetic,
        } for r in post_list]) if post_list else pd.DataFrame()
        category = Category.WATER
    else:
        raise HTTPException(status_code=400, detail="metric must be electricity or water.")

    result = orchestrator.run_verification(
        action_id=payload.action_id,
        run_id=payload.run_id,
        pre_df=pre_df,
        post_df=post_df,
        category=category,
        baseline_start=payload.baseline_start,
        baseline_end=payload.baseline_end,
        post_start=payload.post_action_start,
        post_end=payload.post_action_end,
    )
    return {"result": result, "message": f"Verification complete. Result: {result}"}


@router.get("/{action_id}")
def get_verification_results(action_id: str, db: Session = Depends(get_db)):
    results = db.query(Verification).filter(Verification.action_id == action_id).all()
    return [
        {
            "id": v.id, "result": v.result, "confidence": v.confidence,
            "baseline_value": v.baseline_value, "post_action_value": v.post_action_value,
            "measured_change": v.measured_change, "measured_change_pct": v.measured_change_pct,
            "metric_unit": v.metric_unit, "caveats": v.caveats,
            "reviewer_notes": v.reviewer_notes,
            "verified_at": v.verified_at.isoformat() if v.verified_at else None,
        }
        for v in results
    ]
