"""Agent 7: Reporting Agent.

Generates an evidence-based HTML audit report from orchestrator outputs.
All findings, evidence references, and provenance are included.
Synthetic data is prominently labelled.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from backend.app.schemas.agent_schemas import (
    AgentType, AuditorOutput, DataQualityOutput, InvestigationOutput,
    PrioritizationOutput, ReportSection, ReportingInput, ReportingOutput,
    VerificationResult,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


class ReportingAgent:
    """Agent 7: Generates downloadable HTML audit report.

    Callable interface:
        agent = ReportingAgent()
        output: ReportingOutput = agent.run(inp)

    Report is reproducible from saved orchestrator outputs.
    Synthetic data is clearly flagged throughout.
    """

    name = "reporting_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(self, inp: ReportingInput) -> ReportingOutput:
        logger.info(f"[{self.name}] Generating report for run_id={inp.run_id}")
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

        sections = self._build_sections(inp)

        # Generate HTML
        html = self._render_html(inp, sections, report_id)

        # Save to file
        REPORTS_DIR.mkdir(exist_ok=True)
        file_path = REPORTS_DIR / f"audit_report_{inp.run_id[:8]}_{report_id}.html"
        file_path.write_text(html, encoding="utf-8")
        logger.info(f"[{self.name}] Report saved: {file_path}")

        return ReportingOutput(
            run_id=inp.run_id,
            report_id=report_id,
            title=f"Campus Sustainability Audit Report — {inp.campus_name}",
            sections=sections,
            file_path=str(file_path),
            generated_at=datetime.utcnow(),
            contains_synthetic_data=self._has_synthetic(inp),
        )

    def _has_synthetic(self, inp: ReportingInput) -> bool:
        return any(
            lim for lim in inp.quality_output.limitations
            if "SYNTHETIC" in lim.upper()
        )

    def _build_sections(self, inp: ReportingInput) -> list[ReportSection]:
        sections = []

        # Executive Summary
        kpis = inp.auditor_output.kpis
        findings = inp.auditor_output.findings
        actions = inp.prioritization_output.prioritized_actions

        exec_lines = [
            f"Campus: {inp.campus_name}",
            f"Audit period: {kpis.period_start or 'N/A'} to {kpis.period_end or 'N/A'}",
            f"Data quality score: {inp.quality_output.quality_score:.1f}/100",
            f"Total findings: {len(findings)}",
            f"Total recommended actions: {len(actions)}",
        ]
        if kpis.total_kwh is not None:
            exec_lines.append(f"Total electricity: {kpis.total_kwh:,.1f} kWh")
        if kpis.estimated_t_co2e is not None:
            exec_lines.append(
                f"Estimated CO₂e (Scope 2, electricity only): {kpis.estimated_t_co2e:.2f} tCO₂e "
                f"[ESTIMATE — source: {kpis.emission_factor_source or 'N/A'}]"
            )
        if kpis.total_litres is not None:
            exec_lines.append(f"Total water: {kpis.total_litres:,.0f} litres")
        if kpis.total_waste_kg is not None:
            exec_lines.append(f"Total waste: {kpis.total_waste_kg:,.1f} kg")

        sections.append(ReportSection(
            title="Executive Summary",
            content="\n".join(exec_lines),
        ))

        # Data Quality
        qual_lines = [
            f"Quality Score: {inp.quality_output.quality_score:.1f}/100",
            f"Formula: 100 × (1 − weighted_issue_rate)",
            f"Issues found: {len(inp.quality_output.issues)}",
        ]
        for issue in inp.quality_output.issues:
            qual_lines.append(f"  [{issue.severity.upper()}] {issue.description}")
        for lim in inp.quality_output.limitations:
            qual_lines.append(f"  ⚠️  {lim}")

        sections.append(ReportSection(
            title="Data Quality Assessment",
            content="\n".join(qual_lines),
            is_synthetic_warning=self._has_synthetic(inp),
        ))

        # Findings
        finding_lines = []
        for f in sorted(findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.severity, 9)):
            finding_lines.append(
                f"[{f.severity.upper()}] {f.title} (Confidence: {f.confidence})"
            )
            finding_lines.append(f"  {f.description}")
            for ev in f.evidence:
                synth_flag = " [SYNTHETIC]" if ev.is_synthetic else ""
                finding_lines.append(f"  Evidence ({ev.source}){synth_flag}: {ev.description}")

        sections.append(ReportSection(
            title="Audit Findings",
            content="\n".join(finding_lines) if finding_lines else "No findings generated.",
        ))

        # Investigation Notes
        inv_lines = []
        for result in inp.investigation_output.results:
            inv_lines.append(f"Finding {result.finding_id}:")
            inv_lines.append(f"  {result.investigation_notes}")
            for alt in result.alternative_explanations:
                inv_lines.append(f"  Alternative explanation: {alt}")
            for needed in result.additional_data_needed:
                inv_lines.append(f"  Additional data needed: {needed}")

        sections.append(ReportSection(
            title="Investigation Results",
            content="\n".join(inv_lines) if inv_lines else "No investigation results.",
        ))

        # Prioritized Actions
        act_lines = []
        for pa in actions[:10]:  # top 10
            # Find the action details
            act_lines.append(
                f"Rank #{pa.priority_rank} | Score: {pa.priority_score:.1f}/100 | Action: {pa.action_id}"
            )
            score_str = ", ".join(
                f"{k}={v:.1f}" for k, v in pa.score_breakdown.items()
                if k.endswith("_weighted")
            )
            act_lines.append(f"  Score breakdown: {score_str}")

        sections.append(ReportSection(
            title="Prioritized Actions (Top 10)",
            content="\n".join(act_lines) if act_lines else "No actions generated.",
        ))

        # Methodology
        sections.append(ReportSection(
            title="Methodology and Limitations",
            content=(
                "All findings are generated by deterministic rule-based agents without paid AI APIs.\n"
                "Anomaly detection: Isolation Forest (≥30 samples) or Z-score (< 30 samples).\n"
                f"Emission factor: {kpis.emission_factor_used or 'N/A'} kgCO₂e/kWh "
                f"(source: {kpis.emission_factor_source or 'N/A'}).\n"
                f"{kpis.emission_disclaimer}\n"
                "Priority scores use configurable weights (impact/urgency/confidence/feasibility).\n"
                "Verification requires measured pre/post data — user attestation alone is insufficient.\n"
                "All expected action impacts are ESTIMATES, not guaranteed savings.\n"
            ),
        ))

        return sections

    def _render_html(self, inp: ReportingInput, sections: list[ReportSection], report_id: str) -> str:
        synth_banner = ""
        if self._has_synthetic(inp):
            synth_banner = """
            <div style="background:#ff6b35;color:white;padding:12px 20px;font-weight:bold;font-size:1.1em;border-radius:6px;margin-bottom:20px;">
                ⚠️ SYNTHETIC DEMONSTRATION DATA — This report contains artificially generated data.
                Do NOT use these figures for real environmental or regulatory reporting.
            </div>"""

        section_html = ""
        for s in sections:
            synth_warn = ""
            if s.is_synthetic_warning:
                synth_warn = '<p style="color:#ff6b35;font-weight:bold;">⚠️ Contains synthetic data</p>'
            content_escaped = s.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            section_html += f"""
            <div style="margin-bottom:30px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                <div style="background:#1a365d;color:white;padding:12px 20px;">
                    <h2 style="margin:0;font-size:1.2em;">{s.title}</h2>
                </div>
                <div style="padding:16px 20px;">
                    {synth_warn}
                    <pre style="white-space:pre-wrap;font-family:inherit;font-size:0.9em;margin:0;">{content_escaped}</pre>
                </div>
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Sustainability Audit Report — {inp.campus_name}</title>
<style>
  body {{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:20px;color:#1a202c;background:#f7fafc;}}
  h1 {{color:#1a365d;border-bottom:3px solid #38a169;padding-bottom:10px;}}
  .meta {{color:#718096;font-size:0.9em;margin-bottom:30px;}}
</style>
</head>
<body>
<h1>🌿 Campus Sustainability Audit Report</h1>
<div class="meta">
  <strong>Campus:</strong> {inp.campus_name} &nbsp;|&nbsp;
  <strong>Run ID:</strong> {inp.run_id} &nbsp;|&nbsp;
  <strong>Report ID:</strong> {report_id} &nbsp;|&nbsp;
  <strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
</div>
{synth_banner}
{section_html}
<footer style="margin-top:40px;padding-top:20px;border-top:1px solid #e2e8f0;color:#718096;font-size:0.85em;">
  Generated by Green Campus Sustainability Auditor v1.0.0 |
  All findings are based on available data and configured thresholds. |
  Consult qualified professionals before making financial or regulatory decisions.
</footer>
</body>
</html>"""
