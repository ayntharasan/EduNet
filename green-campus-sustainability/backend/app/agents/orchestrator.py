"""Central Orchestrator — wires all 7 agents with typed handoffs.

Execution order:
  DATA INGESTION → [1] DataQuality → [2] SustainabilityAuditor
  → [3] Investigation → [4] ActionPlanning → [5] Prioritization
  → [7] Reporting

Agent 6 (Verification) is invoked separately per action after interventions.

Each agent's output is validated before passing to the next stage.
Failures are isolated — a failing agent is logged and the run continues
where possible. Retry limit: 1 retry per agent.

Execution is fully deterministic. No paid APIs required.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.agents.action_planning_agent import ActionPlanningAgent
from backend.app.agents.data_quality_agent import DataQualityAgent
from backend.app.agents.investigation_agent import InvestigationAgent
from backend.app.agents.prioritization_agent import PrioritizationAgent
from backend.app.agents.reporting_agent import ReportingAgent
from backend.app.agents.sustainability_auditor_agent import SustainabilityAuditorAgent
from backend.app.agents.verification_agent import VerificationAgent
from backend.app.models.action import Action, ActionStatusHistory
from backend.app.models.agent_execution import AgentExecution
from backend.app.models.audit_run import AuditRun
from backend.app.models.finding import Finding
from backend.app.models.verification import Verification
from backend.app.models.report import AuditReport
from backend.app.schemas.agent_schemas import (
    ActionPlanningInput, AuditorInput, Category, DataQualityInput,
    InvestigationInput, OrchestratorRunStatus, PrioritizationInput,
    ReportingInput, VerificationInput,
)

logger = logging.getLogger(__name__)
MAX_RETRIES = 1


class AuditOrchestrator:
    """Central coordinator for the sustainability audit workflow.

    Usage:
        orchestrator = AuditOrchestrator(db)
        run_id = orchestrator.run_audit(
            electricity_df=..., water_df=..., waste_df=...,
            baseline_elec_df=..., campus_name="My Campus"
        )
    """

    def __init__(self, db: Session):
        self.db = db
        self.dq_agent = DataQualityAgent()
        self.auditor_agent = SustainabilityAuditorAgent()
        self.inv_agent = InvestigationAgent()
        self.act_agent = ActionPlanningAgent()
        self.pri_agent = PrioritizationAgent()
        self.rep_agent = ReportingAgent()
        self.ver_agent = VerificationAgent()

    def run_audit(
        self,
        electricity_df: pd.DataFrame,
        water_df: pd.DataFrame,
        waste_df: pd.DataFrame,
        baseline_elec_df: pd.DataFrame | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        baseline_start: date | None = None,
        baseline_end: date | None = None,
        campus_name: str = "Campus",
        emission_factor: float = 0.716,
        emission_factor_source: str = "CEA CO2 Baseline Database Version 18 (2022-23)",
        weight_impact: float = 40.0,
        weight_urgency: float = 25.0,
        weight_confidence: float = 20.0,
        weight_feasibility: float = 15.0,
    ) -> str:
        """Execute the full audit pipeline. Returns the run_id."""

        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"[Orchestrator] Starting audit run_id={run_id}")

        # Create audit run record
        audit_run = AuditRun(
            run_id=run_id,
            status="running",
            triggered_by="user",
            analysis_period_start=period_start,
            analysis_period_end=period_end,
            started_at=datetime.utcnow(),
        )
        self.db.add(audit_run)
        self.db.commit()

        agent_statuses: dict[str, str] = {}

        try:
            # ---------------------------------------------------------------
            # AGENT 1: Data Quality
            # ---------------------------------------------------------------
            dq_input = DataQualityInput(run_id=run_id)
            dq_output = self._run_agent(
                agent=self.dq_agent,
                agent_name="data_quality_agent",
                run_id=run_id,
                fn=lambda: self.dq_agent.run(dq_input, electricity_df, water_df, waste_df),
                agent_statuses=agent_statuses,
            )
            if dq_output is None:
                self._fail_run(audit_run, run_id, "Data Quality Agent failed critically.")
                return run_id

            # ---------------------------------------------------------------
            # AGENT 2: Sustainability Auditor
            # ---------------------------------------------------------------
            auditor_input = AuditorInput(
                run_id=run_id,
                quality_output=dq_output,
                period_start=period_start,
                period_end=period_end,
                baseline_start=baseline_start,
                baseline_end=baseline_end,
                emission_factor=emission_factor,
                emission_factor_source=emission_factor_source,
            )
            auditor_output = self._run_agent(
                agent=self.auditor_agent,
                agent_name="sustainability_auditor_agent",
                run_id=run_id,
                fn=lambda: self.auditor_agent.run(
                    auditor_input, electricity_df, water_df, waste_df, baseline_elec_df
                ),
                agent_statuses=agent_statuses,
            )
            if auditor_output is None:
                auditor_output = self._empty_auditor_output(run_id, emission_factor, emission_factor_source)

            # Save findings to DB
            self._save_findings(auditor_output.findings, run_id)

            # ---------------------------------------------------------------
            # AGENT 3: Investigation
            # ---------------------------------------------------------------
            inv_input = InvestigationInput(
                run_id=run_id,
                findings=auditor_output.findings,
                quality_output=dq_output,
            )
            inv_output = self._run_agent(
                agent=self.inv_agent,
                agent_name="investigation_agent",
                run_id=run_id,
                fn=lambda: self.inv_agent.run(inv_input, electricity_df, water_df, waste_df),
                agent_statuses=agent_statuses,
            )
            if inv_output is None:
                from backend.app.schemas.agent_schemas import InvestigationOutput
                inv_output = InvestigationOutput(run_id=run_id, results=[])

            # ---------------------------------------------------------------
            # AGENT 4: Action Planning
            # ---------------------------------------------------------------
            act_input = ActionPlanningInput(
                run_id=run_id,
                findings=auditor_output.findings,
                investigation_results=inv_output.results,
            )
            act_output = self._run_agent(
                agent=self.act_agent,
                agent_name="action_planning_agent",
                run_id=run_id,
                fn=lambda: self.act_agent.run(act_input),
                agent_statuses=agent_statuses,
            )
            if act_output is None:
                from backend.app.schemas.agent_schemas import ActionPlanningOutput
                act_output = ActionPlanningOutput(run_id=run_id, actions=[])

            # ---------------------------------------------------------------
            # AGENT 5: Prioritization
            # ---------------------------------------------------------------
            pri_input = PrioritizationInput(
                run_id=run_id,
                actions=act_output.actions,
                weight_impact=weight_impact,
                weight_urgency=weight_urgency,
                weight_confidence=weight_confidence,
                weight_feasibility=weight_feasibility,
            )
            pri_output = self._run_agent(
                agent=self.pri_agent,
                agent_name="prioritization_agent",
                run_id=run_id,
                fn=lambda: self.pri_agent.run(pri_input),
                agent_statuses=agent_statuses,
            )
            if pri_output is None:
                from backend.app.schemas.agent_schemas import PrioritizationOutput
                pri_output = PrioritizationOutput(run_id=run_id, prioritized_actions=[], weights_used={})

            # Save actions to DB
            self._save_actions(act_output.actions, pri_output.prioritized_actions, run_id)

            # ---------------------------------------------------------------
            # AGENT 7: Reporting
            # ---------------------------------------------------------------
            rep_input = ReportingInput(
                run_id=run_id,
                auditor_output=auditor_output,
                investigation_output=inv_output,
                prioritization_output=pri_output,
                quality_output=dq_output,
                campus_name=campus_name,
                report_format="html",
            )
            rep_output = self._run_agent(
                agent=self.rep_agent,
                agent_name="reporting_agent",
                run_id=run_id,
                fn=lambda: self.rep_agent.run(rep_input),
                agent_statuses=agent_statuses,
            )

            # Save report
            if rep_output:
                report = AuditReport(
                    report_id=rep_output.report_id,
                    run_id=run_id,
                    title=rep_output.title,
                    format="html",
                    file_path=rep_output.file_path,
                    generated_by="reporting_agent",
                )
                self.db.add(report)

            # ---------------------------------------------------------------
            # Finalise
            # ---------------------------------------------------------------
            audit_run.status = "complete"
            audit_run.completed_at = datetime.utcnow()
            audit_run.findings_count = len(auditor_output.findings)
            audit_run.actions_count = len(act_output.actions)
            audit_run.summary = (
                f"Audit complete. Findings: {len(auditor_output.findings)}, "
                f"Actions: {len(act_output.actions)}, "
                f"Quality score: {dq_output.quality_score:.1f}"
            )
            self.db.commit()
            logger.info(f"[Orchestrator] Audit complete. run_id={run_id}")

        except Exception as e:
            logger.exception(f"[Orchestrator] Unhandled error in run_id={run_id}: {e}")
            self._fail_run(audit_run, run_id, str(e))

        return run_id

    def run_verification(
        self,
        action_id: str,
        run_id: str,
        pre_df: pd.DataFrame,
        post_df: pd.DataFrame,
        category: Category,
        baseline_start: date,
        baseline_end: date,
        post_start: date,
        post_end: date,
        building_id: int | None = None,
    ) -> str:
        """Run verification for a single action. Returns verification result."""
        ver_input = VerificationInput(
            action_id=action_id,
            run_id=run_id,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            post_action_start=post_start,
            post_action_end=post_end,
            category=category,
            building_id=building_id,
        )
        output = self.ver_agent.run(ver_input, pre_df, post_df)

        # Persist verification result
        ver = Verification(
            action_id=action_id,
            baseline_period_start=baseline_start,
            baseline_period_end=baseline_end,
            post_action_period_start=post_start,
            post_action_period_end=post_end,
            baseline_value=output.baseline_value,
            post_action_value=output.post_action_value,
            measured_change=output.measured_change,
            measured_change_pct=output.measured_change_pct,
            metric_unit=output.metric_unit,
            result=output.result.value,
            confidence=output.confidence.value,
            reviewer_notes=output.reviewer_notes,
            caveats="\n".join(output.caveats),
            verified_at=datetime.utcnow(),
        )
        self.db.add(ver)

        # Only update action status to "verified" if result == improved
        action = self.db.query(Action).filter_by(action_id=action_id).first()
        if action:
            old_status = action.status
            if output.result.value == "improved":
                action.status = "verified"
            else:
                action.status = "completed"  # completed but not verified as improved
            hist = ActionStatusHistory(
                action_id=action_id,
                old_status=old_status,
                new_status=action.status,
                changed_by="verification_agent",
                notes=f"Verification result: {output.result.value}, confidence={output.confidence.value}",
            )
            self.db.add(hist)

        self.db.commit()
        logger.info(
            f"[Orchestrator] Verification complete. action={action_id}, "
            f"result={output.result.value}"
        )
        return output.result.value

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_agent(
        self,
        agent: Any,
        agent_name: str,
        run_id: str,
        fn,
        agent_statuses: dict,
        retries: int = MAX_RETRIES,
    ) -> Any:
        """Execute an agent function with error handling, timing, and DB logging."""
        exec_record = AgentExecution(
            run_id=run_id,
            agent_name=agent_name,
            agent_type=agent.agent_type.value,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(exec_record)
        self.db.commit()

        attempt = 0
        last_error = None
        while attempt <= retries:
            try:
                t0 = time.monotonic()
                output = fn()
                duration = time.monotonic() - t0

                exec_record.status = "complete"
                exec_record.completed_at = datetime.utcnow()
                exec_record.duration_seconds = round(duration, 3)
                exec_record.output_summary = f"Completed in {duration:.2f}s"

                # Count findings if present
                if hasattr(output, "findings"):
                    exec_record.findings_produced = len(output.findings)
                elif hasattr(output, "results"):
                    exec_record.findings_produced = len(output.results)
                elif hasattr(output, "actions"):
                    exec_record.findings_produced = len(output.actions)

                self.db.commit()
                agent_statuses[agent_name] = "complete"
                logger.info(f"[Orchestrator] Agent '{agent_name}' completed in {duration:.2f}s")
                return output

            except Exception as e:
                last_error = e
                attempt += 1
                logger.warning(
                    f"[Orchestrator] Agent '{agent_name}' attempt {attempt} failed: {e}"
                )
                if attempt > retries:
                    break

        # All retries exhausted
        exec_record.status = "failed"
        exec_record.error_message = str(last_error)
        exec_record.completed_at = datetime.utcnow()
        self.db.commit()
        agent_statuses[agent_name] = "failed"
        logger.error(f"[Orchestrator] Agent '{agent_name}' failed after {retries+1} attempt(s): {last_error}")
        return None

    def _save_findings(self, findings: list, run_id: str):
        import json
        for f in findings:
            db_finding = Finding(
                finding_id=f.finding_id,
                run_id=run_id,
                category=f.category.value,
                severity=f.severity.value,
                title=f.title,
                description=f.description,
                evidence=json.dumps([ev.model_dump() for ev in f.evidence], default=str),
                affected_period_start=f.affected_period_start,
                affected_period_end=f.affected_period_end,
                building_id=f.building_id,
                confidence=f.confidence.value,
                metric_value=f.metric_value,
                metric_unit=f.metric_unit,
                baseline_value=f.baseline_value,
                pct_change=f.pct_change,
            )
            self.db.add(db_finding)
        self.db.commit()

    def _save_actions(self, actions: list, prioritized: list, run_id: str):
        import json
        # Build priority map
        pri_map = {pa.action_id: pa for pa in prioritized}
        for a in actions:
            pa = pri_map.get(a.action_id)
            db_action = Action(
                action_id=a.action_id,
                run_id=run_id,
                title=a.title,
                description=a.description,
                category=a.category.value,
                finding_ids=json.dumps(a.finding_ids),
                responsible_role=a.responsible_role,
                cost_category=a.cost_category.value,
                implementation_difficulty=a.implementation_difficulty.value,
                expected_impact=a.expected_impact,
                prerequisites=json.dumps(a.prerequisites),
                time_horizon=a.time_horizon.value,
                verification_method=a.verification_method,
                priority_score=pa.priority_score if pa else 0.0,
                priority_rank=pa.priority_rank if pa else 0,
                priority_explanation=json.dumps(pa.score_breakdown) if pa else None,
                status="draft",
            )
            self.db.add(db_action)
        self.db.commit()

    def _fail_run(self, audit_run: AuditRun, run_id: str, error: str):
        audit_run.status = "failed"
        audit_run.error_message = error
        audit_run.completed_at = datetime.utcnow()
        self.db.commit()
        logger.error(f"[Orchestrator] Run {run_id} failed: {error}")

    @staticmethod
    def _empty_auditor_output(run_id, emission_factor, emission_factor_source):
        from backend.app.schemas.agent_schemas import AuditorOutput, KPISummary
        return AuditorOutput(
            run_id=run_id,
            kpis=KPISummary(
                emission_factor_used=emission_factor,
                emission_factor_source=emission_factor_source,
            ),
            findings=[],
        )
