"""Agent 2: Sustainability Auditor Agent.

Calculates KPIs and identifies findings by comparing current consumption
against configurable thresholds and baseline periods.

Method: Deterministic rule-based. All thresholds are configurable.
No fabricated regulatory standards. Findings include full evidence references.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

import pandas as pd

from backend.app.analytics.energy import (
    compute_baseline_comparison, compute_emissions, compute_energy_kpis,
    detect_anomalies_statistical,
)
from backend.app.analytics.water import compute_water_kpis
from backend.app.analytics.waste_analytics import compute_waste_kpis
from backend.app.ml.anomaly_detection import detect_anomalies
from backend.app.schemas.agent_schemas import (
    AgentType, AuditFinding, AuditorInput, AuditorOutput, Category,
    Confidence, EvidenceItem, KPISummary, Severity,
)

logger = logging.getLogger(__name__)

# Configurable thresholds — not fabricated regulatory limits
DEFAULT_THRESHOLDS = {
    "electricity_spike_pct": 25.0,      # Flag if consumption > 25% above baseline
    "electricity_drop_pct": -30.0,      # Flag if consumption drops > 30% (possible data gap)
    "water_spike_pct": 30.0,
    "waste_high_residual_pct": 60.0,    # Flag if residual waste > 60% of total
    "anomaly_z_threshold": 2.5,
    "emission_high_t_co2e_per_person": 5.0,  # Rough illustrative threshold only
}


class SustainabilityAuditorAgent:
    """Agent 2: Calculates KPIs and generates structured audit findings.

    Callable interface:
        agent = SustainabilityAuditorAgent()
        output: AuditorOutput = agent.run(inp, electricity_df, water_df, waste_df)

    Runs fully deterministically. Optional ML anomaly detection used when
    sufficient data exists (>= 30 observations).
    """

    name = "sustainability_auditor_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(
        self,
        inp: AuditorInput,
        electricity_df: pd.DataFrame,
        water_df: pd.DataFrame,
        waste_df: pd.DataFrame,
        baseline_elec_df: pd.DataFrame | None = None,
        thresholds: dict | None = None,
    ) -> AuditorOutput:
        logger.info(f"[{self.name}] Starting audit for run_id={inp.run_id}")
        thr = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        findings: list[AuditFinding] = []

        # --- Energy KPIs ---
        energy_kpis = compute_energy_kpis(electricity_df)
        total_kwh = energy_kpis.get("total_kwh")

        # --- Emissions ---
        emissions = {}
        if total_kwh:
            emissions = compute_emissions(total_kwh, inp.emission_factor, inp.emission_factor_source)

        # --- Water KPIs ---
        water_kpis = compute_water_kpis(water_df)
        total_litres = water_kpis.get("total_litres")

        # --- Waste KPIs ---
        waste_kpis = compute_waste_kpis(waste_df)
        total_waste_kg = waste_kpis.get("total_kg")

        kpis = KPISummary(
            total_kwh=total_kwh,
            avg_daily_kwh=energy_kpis.get("avg_daily_kwh"),
            total_litres=total_litres,
            total_waste_kg=total_waste_kg,
            estimated_kg_co2e=emissions.get("kg_co2e"),
            estimated_t_co2e=emissions.get("t_co2e"),
            emission_factor_used=inp.emission_factor,
            emission_factor_source=inp.emission_factor_source,
            period_start=inp.period_start,
            period_end=inp.period_end,
        )

        # --- Findings: Electricity anomalies ---
        if not electricity_df.empty:
            findings.extend(self._electricity_findings(electricity_df, baseline_elec_df, thr, inp))

        # --- Findings: Water anomalies ---
        if not water_df.empty:
            findings.extend(self._water_findings(water_df, thr, inp))

        # --- Findings: Waste composition ---
        if not waste_df.empty and waste_kpis.get("total_kg"):
            findings.extend(self._waste_findings(waste_df, waste_kpis, thr, inp))

        logger.info(f"[{self.name}] Complete. Findings={len(findings)}")
        return AuditorOutput(
            run_id=inp.run_id,
            kpis=kpis,
            findings=findings,
            thresholds_used=thr,
            timestamp=datetime.utcnow(),
        )

    def _electricity_findings(
        self, df: pd.DataFrame, baseline_df: pd.DataFrame | None,
        thr: dict, inp: AuditorInput,
    ) -> list[AuditFinding]:
        findings = []
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # --- Baseline comparison ---
        if baseline_df is not None and not baseline_df.empty:
            comparison = compute_baseline_comparison(df, baseline_df)
            pct = comparison.get("pct_change")
            if pct is not None and pct > thr["electricity_spike_pct"]:
                is_synth = bool(df.get("is_synthetic", pd.Series([False])).any())
                findings.append(AuditFinding(
                    finding_id=f"ELEC-SPIKE-{uuid.uuid4().hex[:8].upper()}",
                    category=Category.ELECTRICITY,
                    severity=Severity.HIGH if pct > 40 else Severity.MEDIUM,
                    confidence=Confidence.HIGH,
                    title=f"Electricity consumption {pct:.1f}% above baseline",
                    description=(
                        f"Current period total ({comparison['current_total_kwh']:.1f} kWh) "
                        f"is {pct:.1f}% higher than the baseline period "
                        f"({comparison['baseline_total_kwh']:.1f} kWh). "
                        f"Threshold: {thr['electricity_spike_pct']}% above baseline."
                    ),
                    metric_value=comparison["current_total_kwh"],
                    metric_unit="kWh",
                    baseline_value=comparison["baseline_total_kwh"],
                    pct_change=pct,
                    affected_period_start=inp.period_start,
                    affected_period_end=inp.period_end,
                    evidence=[EvidenceItem(
                        source="calculation",
                        description=f"Baseline comparison: {comparison['baseline_total_kwh']:.1f} kWh → {comparison['current_total_kwh']:.1f} kWh",
                        value=pct,
                        unit="%",
                        date_range=f"{inp.period_start} to {inp.period_end}",
                        supports_finding=True,
                        is_synthetic=is_synth,
                    )],
                    rule_triggered="electricity_spike_threshold",
                ))
            elif pct is not None and pct < thr["electricity_drop_pct"]:
                findings.append(AuditFinding(
                    finding_id=f"ELEC-DROP-{uuid.uuid4().hex[:8].upper()}",
                    category=Category.ELECTRICITY,
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    title=f"Electricity consumption {abs(pct):.1f}% below baseline — possible data gap",
                    description=(
                        f"Current period total is {abs(pct):.1f}% lower than baseline. "
                        f"This may indicate meter downtime, missing records, or genuine efficiency improvement. "
                        f"Investigate before claiming it as an improvement."
                    ),
                    metric_value=comparison["current_total_kwh"],
                    metric_unit="kWh",
                    baseline_value=comparison["baseline_total_kwh"],
                    pct_change=pct,
                    evidence=[EvidenceItem(
                        source="calculation",
                        description="Consumption is significantly below baseline — requires investigation",
                        value=pct,
                        unit="%",
                        supports_finding=True,
                        is_synthetic=bool(df.get("is_synthetic", pd.Series([False])).any()),
                    )],
                    rule_triggered="electricity_drop_threshold",
                ))

        # --- Statistical anomaly detection ---
        anomaly_result = detect_anomalies(df, "consumption_kwh", "timestamp")
        if not anomaly_result.get("error") and anomaly_result.get("n_anomalies", 0) > 0:
            anomalies = anomaly_result["anomalies"]
            is_synth = bool(df.get("is_synthetic", pd.Series([False])).any())
            findings.append(AuditFinding(
                finding_id=f"ELEC-ANOM-{uuid.uuid4().hex[:8].upper()}",
                category=Category.ELECTRICITY,
                severity=Severity.MEDIUM,
                confidence=Confidence.MEDIUM,
                title=f"{anomaly_result['n_anomalies']} anomalous electricity consumption days detected",
                description=(
                    f"Method: {anomaly_result.get('method_description', anomaly_result['method'])}. "
                    f"Detected {anomaly_result['n_anomalies']} anomalous days out of "
                    f"{anomaly_result['n_samples']} total. "
                    f"Limitations: {anomaly_result.get('limitations', 'None noted')}."
                ),
                affected_period_start=inp.period_start,
                affected_period_end=inp.period_end,
                evidence=[EvidenceItem(
                    source="ml_model" if anomaly_result["method"] == "isolation_forest" else "calculation",
                    description=f"Anomaly detection ({anomaly_result['method']}): "
                               f"{anomaly_result['n_anomalies']} outlier days. "
                               f"Dates: {[a['date'] for a in anomalies[:5]]}",
                    value=float(anomaly_result["n_anomalies"]),
                    unit="anomalous days",
                    supports_finding=True,
                    is_synthetic=is_synth,
                )],
                rule_triggered="anomaly_detection",
            ))

        return findings

    def _water_findings(self, df: pd.DataFrame, thr: dict, inp: AuditorInput) -> list[AuditFinding]:
        findings = []
        water_kpis = compute_water_kpis(df)
        leak_suspects = water_kpis.get("leak_suspect_periods", [])
        is_synth = bool(df.get("is_synthetic", pd.Series([False])).any()) if not df.empty else False

        for suspect in leak_suspects:
            findings.append(AuditFinding(
                finding_id=f"WATER-LEAK-{uuid.uuid4().hex[:8].upper()}",
                category=Category.WATER,
                severity=Severity.HIGH,
                confidence=Confidence.LOW,
                title=f"Suspected elevated water usage: {suspect['start']} to {suspect['end']}",
                description=(
                    f"Water consumption was persistently elevated for {suspect['consecutive_days']} days "
                    f"({suspect['start']} to {suspect['end']}). "
                    f"This may indicate a leak, but physical inspection is required to confirm. "
                    f"This is a CANDIDATE for investigation, NOT a confirmed leak."
                ),
                affected_period_start=date.fromisoformat(suspect["start"]) if isinstance(suspect["start"], str) else suspect["start"],
                affected_period_end=date.fromisoformat(suspect["end"]) if isinstance(suspect["end"], str) else suspect["end"],
                evidence=[EvidenceItem(
                    source="calculation",
                    description=f"Rolling-median comparison: {suspect['consecutive_days']} consecutive days above 1.5× median",
                    value=float(suspect["consecutive_days"]),
                    unit="consecutive days",
                    date_range=f"{suspect['start']} to {suspect['end']}",
                    supports_finding=True,
                    is_synthetic=is_synth,
                )],
                rule_triggered="water_elevated_usage_streak",
            ))

        return findings

    def _waste_findings(self, df: pd.DataFrame, waste_kpis: dict, thr: dict, inp: AuditorInput) -> list[AuditFinding]:
        findings = []
        total = waste_kpis.get("total_kg", 0)
        residual = waste_kpis.get("total_residual_kg", 0)
        is_synth = bool(df.get("is_synthetic", pd.Series([False])).any()) if not df.empty else False

        if total > 0:
            residual_pct = (residual / total) * 100
            if residual_pct > thr["waste_high_residual_pct"]:
                findings.append(AuditFinding(
                    finding_id=f"WASTE-RESID-{uuid.uuid4().hex[:8].upper()}",
                    category=Category.WASTE,
                    severity=Severity.MEDIUM,
                    confidence=Confidence.HIGH,
                    title=f"High residual waste fraction: {residual_pct:.1f}% of total",
                    description=(
                        f"Residual (non-recyclable, non-compostable) waste is {residual_pct:.1f}% of total, "
                        f"exceeding the {thr['waste_high_residual_pct']}% threshold. "
                        f"Improved waste segregation could divert more material from landfill."
                    ),
                    metric_value=residual_pct,
                    metric_unit="%",
                    affected_period_start=inp.period_start,
                    affected_period_end=inp.period_end,
                    evidence=[EvidenceItem(
                        source="calculation",
                        description=f"Residual waste: {residual:.1f} kg / {total:.1f} kg total = {residual_pct:.1f}%",
                        value=residual_pct,
                        unit="%",
                        supports_finding=True,
                        is_synthetic=is_synth,
                    )],
                    rule_triggered="waste_residual_fraction_threshold",
                ))

        return findings
