"""End-to-end demo runner — runs the full audit pipeline on synthetic data.

Usage:
    python scripts/run_demo.py

Steps executed:
  1. Generate demo data (if absent)
  2. Initialize database
  3. Run 7-agent audit pipeline
  4. Print findings, agent timeline, action plan
  5. Simulate post-action verification

No paid APIs or internet required.
"""
from __future__ import annotations
import sys
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.core.logging_config import setup_logging
from backend.app.database.session import SessionLocal
from backend.app.database.init_db import init_db
from backend.app.agents.orchestrator import AuditOrchestrator

setup_logging()
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("demo_runner")

DEMO_DIR = ROOT / "data" / "demo"


def ensure_demo_data():
    if not (DEMO_DIR / "electricity_demo.csv").exists():
        logger.info("Demo data not found. Generating...")
        import subprocess
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_demo_data.py")],
            check=True,
        )
    else:
        logger.info("Demo data already exists.")


def load_demo_data():
    elec_df = pd.read_csv(DEMO_DIR / "electricity_demo.csv")
    water_df = pd.read_csv(DEMO_DIR / "water_demo.csv")
    waste_df = pd.read_csv(DEMO_DIR / "waste_demo.csv")
    elec_df["timestamp"] = pd.to_datetime(elec_df["timestamp"])
    baseline_mask = elec_df["timestamp"] <= elec_df["timestamp"].min() + pd.Timedelta(days=44)
    baseline_df = elec_df[baseline_mask].copy()
    logger.info(f"Loaded {len(elec_df)} elec, {len(water_df)} water, {len(waste_df)} waste records.")
    return elec_df, water_df, waste_df, baseline_df


def sep(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main():
    print("\nGreen Campus Sustainability Auditor -- Demo Run")
    print("[SYNTHETIC DATA] All measurements in this demo are artificially generated.")
    print("No real campus data is used.")

    ensure_demo_data()

    sep("Step 1: Database Initialization")
    init_db()
    print("Database initialized successfully.")

    sep("Step 2: Loading Synthetic Demo Data")
    elec_df, water_df, waste_df, baseline_df = load_demo_data()

    sep("Step 3: Running 7-Agent Audit Pipeline")
    db = SessionLocal()
    try:
        orchestrator = AuditOrchestrator(db)
        run_id = orchestrator.run_audit(
            electricity_df=elec_df,
            water_df=water_df,
            waste_df=waste_df,
            baseline_elec_df=baseline_df,
            campus_name="Green Valley University (Demo)",
        )
        print(f"Audit completed. Run ID: {run_id}")

        from backend.app.models.audit_run import AuditRun
        from backend.app.models.finding import Finding
        from backend.app.models.action import Action, ActionStatusHistory
        from backend.app.models.agent_execution import AgentExecution

        run = db.query(AuditRun).filter(AuditRun.run_id == run_id).first()
        sep("Step 4: Audit Summary")
        print(f"  Status   : {run.status}")
        print(f"  Findings : {run.findings_count}")
        print(f"  Actions  : {run.actions_count}")

        sep("Step 5: Agent Execution Log")
        for ex in db.query(AgentExecution).filter(AgentExecution.run_id == run_id).all():
            dur = f"{ex.duration_seconds:.2f}s" if ex.duration_seconds else "N/A"
            print(f"  [{ex.status.upper():8s}] {ex.agent_name:35s} | {ex.findings_produced} findings | {dur}")

        sep("Step 6: Top Findings")
        findings = db.query(Finding).filter(Finding.run_id == run_id).all()
        for f in findings[:6]:
            chg = f"  ({f.pct_change:+.1f}% vs baseline)" if f.pct_change else ""
            print(f"  [{f.severity.upper():8s}] [{f.category}] {f.title}{chg}")

        sep("Step 7: Priority Action Plan")
        actions = db.query(Action).filter(Action.run_id == run_id).order_by(Action.priority_rank).all()
        for a in actions[:6]:
            print(f"  #{a.priority_rank:02d} [{a.cost_category:15s}] {a.title}")

        sep("Step 8: Verification Simulation (Synthetic)")
        if actions:
            top = actions[0]
            top.status = "completed"
            db.add(ActionStatusHistory(
                action_id=top.action_id, old_status="draft", new_status="completed",
                changed_by="demo_runner",
                notes="[DEMO] Simulated completion for verification demo.",
            ))
            db.commit()

            from backend.app.schemas.agent_schemas import Category as AuditCategory
            from datetime import date

            t_min = elec_df["timestamp"].min()
            # Pre-action window: days 60–75
            pre_start = (t_min + pd.Timedelta(days=60)).date()
            pre_end   = (t_min + pd.Timedelta(days=75)).date()
            # Post-action window: days 90–110
            post_start = (t_min + pd.Timedelta(days=90)).date()
            post_end   = (t_min + pd.Timedelta(days=110)).date()

            pre_df_ver = elec_df[
                (elec_df["timestamp"].dt.date >= pre_start) &
                (elec_df["timestamp"].dt.date <= pre_end)
            ].copy()
            # Simulate 18% consumption reduction post-intervention
            post_df_ver = elec_df[
                (elec_df["timestamp"].dt.date >= post_start) &
                (elec_df["timestamp"].dt.date <= post_end)
            ].copy()
            post_df_ver["consumption_kwh"] = post_df_ver["consumption_kwh"] * 0.82

            # run_id from the most recent audit run in DB
            from backend.app.models.audit_run import AuditRun as AuditRunModel
            latest_run = db.query(AuditRunModel).order_by(AuditRunModel.created_at.desc()).first()
            ver_run_id = latest_run.run_id if latest_run else "RUN-DEMO"

            ver_result = orchestrator.run_verification(
                action_id=top.action_id,
                run_id=ver_run_id,
                pre_df=pre_df_ver,
                post_df=post_df_ver,
                category=AuditCategory.ELECTRICITY,
                baseline_start=pre_start,
                baseline_end=pre_end,
                post_start=post_start,
                post_end=post_end,
            )
            print(f"  Action   : {top.title}")
            print(f"  Result   : {ver_result}")
            print(f"  [NOTE] Verification used SYNTHETIC data — 18% reduction simulated.")

        sep("Demo Complete -- Next Steps")
        print("  Backend  : python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload")
        print("  Docs     : http://127.0.0.1:8000/api/docs")
        print("  Frontend : cd frontend && npm run dev")
        print("  UI       : http://localhost:5173")

    finally:
        db.close()


if __name__ == "__main__":
    main()
