"""Report generation and download endpoints."""
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.audit_run import AuditRun
from backend.app.models.finding import Finding
from backend.app.models.action import Action
from backend.app.models.report import AuditReport
from backend.app.agents.reporting_agent import ReportingAgent
from backend.app.schemas.agent_schemas import (
    ReportingInput, AuditFinding, RecommendedAction,
)

router = APIRouter()


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(AuditReport).order_by(AuditReport.created_at.desc()).all()
    return [
        {
            "report_id": r.report_id, "run_id": r.run_id, "title": r.title,
            "format": r.format, "file_path": r.file_path,
            "generated_by": r.generated_by, "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.post("/generate/{run_id}")
def generate_report(
    run_id: str,
    campus_name: str = "Green Valley University (Demo)",
    db: Session = Depends(get_db),
):
    """Generate an HTML audit report for the given run_id."""
    run = db.query(AuditRun).filter(AuditRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Audit run not found.")

    findings_orm = db.query(Finding).filter(Finding.run_id == run_id).all()
    actions_orm = db.query(Action).filter(Action.run_id == run_id).order_by(Action.priority_rank).all()

    findings = [
        AuditFinding(
            finding_id=f.finding_id, category=f.category, severity=f.severity,
            title=f.title, description=f.description, evidence=[],
            confidence=f.confidence, metric_value=f.metric_value,
            metric_unit=f.metric_unit, baseline_value=f.baseline_value,
            pct_change=f.pct_change, investigation_notes=f.investigation_notes,
        )
        for f in findings_orm
    ]
    actions = [
        RecommendedAction(
            action_id=a.action_id, title=a.title, description=a.description,
            category=a.category, cost_category=a.cost_category,
            implementation_difficulty=a.implementation_difficulty,
            expected_impact=a.expected_impact or "",
            time_horizon=a.time_horizon,
            responsible_role=a.responsible_role or "",
            verification_method=a.verification_method or "",
            prerequisites=[], finding_ids=[],
        )
        for a in actions_orm
    ]

    agent = ReportingAgent()
    inp = ReportingInput(
        run_id=run_id,
        campus_name=campus_name,
        audit_period_start=str(run.analysis_period_start) if run.analysis_period_start else "N/A",
        audit_period_end=str(run.analysis_period_end) if run.analysis_period_end else "N/A",
        findings=findings,
        prioritized_actions=actions,
        energy_kpis={}, water_kpis={}, waste_kpis={}, emissions_estimate={},
        data_quality_summary={"quality_score": 0, "total_records": len(findings_orm)},
        contains_synthetic_data=True,
        generated_by="reporting_agent",
    )
    output = agent.run(inp)

    report_id = str(uuid.uuid4())[:16]
    existing = db.query(AuditReport).filter(
        AuditReport.run_id == run_id, AuditReport.format == "html"
    ).first()
    if existing:
        existing.file_path = output.report_file_path
        existing.content_summary = (output.executive_summary or "")[:500]
        db.commit()
        return {"report_id": existing.report_id, "file_path": output.report_file_path, "message": "Report regenerated."}

    report_record = AuditReport(
        report_id=report_id,
        run_id=run_id,
        title=f"Sustainability Audit Report — {run_id[:8]}",
        format="html",
        file_path=output.report_file_path,
        content_summary=(output.executive_summary or "")[:500],
    )
    db.add(report_record)
    db.commit()
    return {"report_id": report_id, "file_path": output.report_file_path, "message": "Report generated."}


@router.get("/download/{report_id}")
def download_report(report_id: str, db: Session = Depends(get_db)):
    """Download a generated HTML report file."""
    report = db.query(AuditReport).filter(AuditReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if not report.file_path:
        raise HTTPException(status_code=404, detail="Report file path not recorded.")
    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Report file not found at: {path}")
    return FileResponse(
        path=str(path),
        media_type="text/html",
        filename=path.name,
    )
