"""Audit run endpoints — start audit, get status, list runs."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pandas as pd

from backend.app.database.session import get_db, SessionLocal
from backend.app.models.audit_run import AuditRun
from backend.app.models.agent_execution import AgentExecution
from backend.app.models.finding import Finding
from backend.app.models.electricity import ElectricityMeasurement
from backend.app.models.water import WaterMeasurement
from backend.app.models.waste import WasteMeasurement
from backend.app.agents.orchestrator import AuditOrchestrator
from backend.app.core.config import settings

router = APIRouter()


class AuditRunRequest(BaseModel):
    campus_name: Optional[str] = None
    analysis_start: Optional[date] = None
    analysis_end: Optional[date] = None
    baseline_start: Optional[date] = None
    baseline_end: Optional[date] = None
    use_demo_data: bool = True
    triggered_by: str = "user"


class AuditRunSummary(BaseModel):
    id: int
    run_id: str
    status: str
    triggered_by: str
    findings_count: int
    actions_count: int
    summary: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str


class AgentExecutionResponse(BaseModel):
    agent_name: str
    agent_type: str
    status: str
    findings_produced: int
    duration_seconds: Optional[float]
    error_message: Optional[str]

    class Config:
        from_attributes = True


def _run_to_summary(r: AuditRun) -> AuditRunSummary:
    return AuditRunSummary(
        id=r.id, run_id=r.run_id, status=r.status, triggered_by=r.triggered_by,
        findings_count=r.findings_count, actions_count=r.actions_count,
        summary=r.summary, error_message=r.error_message,
        started_at=r.started_at.isoformat() if r.started_at else None,
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        created_at=r.created_at.isoformat(),
    )


@router.get("", response_model=list[AuditRunSummary])
def list_audit_runs(limit: int = 20, db: Session = Depends(get_db)):
    runs = db.query(AuditRun).order_by(AuditRun.created_at.desc()).limit(limit).all()
    return [_run_to_summary(r) for r in runs]


@router.post("/run", status_code=202)
def start_audit(
    request: AuditRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start a new audit in the background. Returns immediately with a status message.

    Poll GET /api/audit to see completed runs.
    """
    campus_name = request.campus_name or settings.DEMO_CAMPUS_NAME
    background_tasks.add_task(
        _run_audit_background,
        campus_name=campus_name,
        analysis_start=request.analysis_start,
        analysis_end=request.analysis_end,
        baseline_start=request.baseline_start,
        baseline_end=request.baseline_end,
        use_demo_data=request.use_demo_data,
        triggered_by=request.triggered_by,
    )
    return {
        "message": "Audit started in background.",
        "note": "Poll GET /api/audit to see completed runs.",
    }


def _run_audit_background(
    campus_name: str,
    analysis_start, analysis_end,
    baseline_start, baseline_end,
    use_demo_data: bool,
    triggered_by: str,
):
    """Background task: load data and run the full audit pipeline."""
    import logging
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        elec_df, water_df, waste_df, baseline_elec_df = _load_measurements(
            db, use_demo_data, analysis_start, analysis_end, baseline_start, baseline_end
        )
        orchestrator = AuditOrchestrator(db)
        run_id = orchestrator.run_audit(
            electricity_df=elec_df,
            water_df=water_df,
            waste_df=waste_df,
            baseline_elec_df=baseline_elec_df,
            campus_name=campus_name,
        )
        logger.info(f"Audit {run_id} completed successfully.")
    except Exception as e:
        logger.error(f"Audit background task failed: {e}", exc_info=True)
    finally:
        db.close()


def _load_measurements(db, use_demo_data, analysis_start, analysis_end, baseline_start, baseline_end):
    """Load from DB, fall back to demo CSVs if no records found and use_demo_data=True."""
    import logging
    from pathlib import Path
    logger = logging.getLogger(__name__)

    elec_q = db.query(ElectricityMeasurement)
    water_q = db.query(WaterMeasurement)
    waste_q = db.query(WasteMeasurement)

    if analysis_start:
        elec_q = elec_q.filter(ElectricityMeasurement.timestamp >= analysis_start)
        water_q = water_q.filter(WaterMeasurement.measurement_date >= analysis_start)
        waste_q = waste_q.filter(WasteMeasurement.measurement_date >= analysis_start)
    if analysis_end:
        elec_q = elec_q.filter(ElectricityMeasurement.timestamp <= analysis_end)
        water_q = water_q.filter(WaterMeasurement.measurement_date <= analysis_end)
        waste_q = waste_q.filter(WasteMeasurement.measurement_date <= analysis_end)

    elec_rows = elec_q.all()

    if not elec_rows and use_demo_data:
        demo_dir = Path("data/demo")
        elec_path = demo_dir / "electricity_demo.csv"
        if elec_path.exists():
            logger.info("No DB measurements — loading demo CSV data (SYNTHETIC).")
            elec_df = pd.read_csv(elec_path)
            water_df = pd.read_csv(demo_dir / "water_demo.csv") if (demo_dir / "water_demo.csv").exists() else pd.DataFrame()
            waste_df = pd.read_csv(demo_dir / "waste_demo.csv") if (demo_dir / "waste_demo.csv").exists() else pd.DataFrame()
            elec_df["timestamp"] = pd.to_datetime(elec_df["timestamp"])
            baseline_mask = elec_df["timestamp"] <= elec_df["timestamp"].min() + pd.Timedelta(days=44)
            return elec_df, water_df, waste_df, elec_df[baseline_mask].copy()
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def orm_elec(rows):
        if not rows: return pd.DataFrame()
        return pd.DataFrame([{
            "timestamp": r.timestamp, "building_id": r.building_id,
            "consumption_kwh": r.consumption_kwh, "occupancy_count": r.occupancy_count,
            "floor_area_m2": r.floor_area_m2, "source_type": r.source_type, "is_synthetic": r.is_synthetic,
        } for r in rows])

    def orm_water(rows):
        if not rows: return pd.DataFrame()
        return pd.DataFrame([{
            "measurement_date": r.measurement_date, "building_id": r.building_id,
            "consumption_litres": r.consumption_litres, "is_synthetic": r.is_synthetic,
        } for r in rows])

    def orm_waste(rows):
        if not rows: return pd.DataFrame()
        return pd.DataFrame([{
            "measurement_date": r.measurement_date, "building_id": r.building_id,
            "wet_waste_kg": r.wet_waste_kg, "dry_recyclable_kg": r.dry_recyclable_kg,
            "residual_waste_kg": r.residual_waste_kg, "total_waste_kg": r.total_waste_kg,
            "is_synthetic": r.is_synthetic,
        } for r in rows])

    elec_df = orm_elec(elec_rows)
    water_df = orm_water(db.query(WaterMeasurement).all())
    waste_df = orm_waste(db.query(WasteMeasurement).all())
    baseline_elec_df = pd.DataFrame()

    if baseline_start and baseline_end:
        b_rows = db.query(ElectricityMeasurement).filter(
            ElectricityMeasurement.timestamp >= baseline_start,
            ElectricityMeasurement.timestamp <= baseline_end,
        ).all()
        baseline_elec_df = orm_elec(b_rows)

    return elec_df, water_df, waste_df, baseline_elec_df


@router.get("/{run_id}", response_model=AuditRunSummary)
def get_audit_run(run_id: str, db: Session = Depends(get_db)):
    r = db.query(AuditRun).filter(AuditRun.run_id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Audit run not found.")
    return _run_to_summary(r)


@router.get("/{run_id}/agents", response_model=list[AgentExecutionResponse])
def get_run_agents(run_id: str, db: Session = Depends(get_db)):
    return db.query(AgentExecution).filter(AgentExecution.run_id == run_id).all()


@router.get("/{run_id}/findings")
def get_run_findings(run_id: str, db: Session = Depends(get_db)):
    findings = db.query(Finding).filter(Finding.run_id == run_id).all()
    return [
        {
            "finding_id": f.finding_id, "category": f.category, "severity": f.severity,
            "title": f.title, "description": f.description, "confidence": f.confidence,
            "metric_value": f.metric_value, "metric_unit": f.metric_unit,
            "baseline_value": f.baseline_value, "pct_change": f.pct_change,
            "status": f.status, "investigation_notes": f.investigation_notes,
        }
        for f in findings
    ]
