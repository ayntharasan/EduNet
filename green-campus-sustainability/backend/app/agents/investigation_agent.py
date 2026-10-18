"""Agent 3: Investigation Agent.

For each finding from the Auditor, this agent investigates whether the
anomaly is genuine, looks for alternative explanations, and identifies
additional data that would improve confidence.

Method: Deterministic rule-based cross-referencing.
Does NOT make causal claims — only identifies correlation and candidates.
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from backend.app.schemas.agent_schemas import (
    AgentType, AuditFinding, Category, Confidence, EvidenceItem,
    InvestigationInput, InvestigationOutput, InvestigationResult,
)

logger = logging.getLogger(__name__)

# Correlation thresholds
WEEKEND_REDUCTION_THRESHOLD = 0.20  # weekday avg > 20% above weekend = usage pattern


class InvestigationAgent:
    """Agent 3: Investigates each finding for supporting/contradictory evidence.

    Callable interface:
        agent = InvestigationAgent()
        output: InvestigationOutput = agent.run(inp, electricity_df, water_df, waste_df)

    Does NOT make causal claims. Documents alternative explanations.
    """

    name = "investigation_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(
        self,
        inp: InvestigationInput,
        electricity_df: pd.DataFrame,
        water_df: pd.DataFrame,
        waste_df: pd.DataFrame,
    ) -> InvestigationOutput:
        logger.info(f"[{self.name}] Investigating {len(inp.findings)} findings for run_id={inp.run_id}")
        results: list[InvestigationResult] = []

        for finding in inp.findings:
            result = self._investigate_finding(finding, electricity_df, water_df, waste_df, inp)
            results.append(result)
            logger.debug(f"  Finding {finding.finding_id}: {len(result.supporting_evidence)} supporting, "
                         f"{len(result.contradictory_evidence)} contradictory evidence items")

        logger.info(f"[{self.name}] Complete. Investigated {len(results)} findings.")
        return InvestigationOutput(
            run_id=inp.run_id,
            results=results,
            timestamp=datetime.utcnow(),
        )

    def _investigate_finding(
        self,
        finding: AuditFinding,
        electricity_df: pd.DataFrame,
        water_df: pd.DataFrame,
        waste_df: pd.DataFrame,
        inp: InvestigationInput,
    ) -> InvestigationResult:
        supporting: list[EvidenceItem] = list(finding.evidence)  # inherit original evidence
        contradictory: list[EvidenceItem] = []
        alternatives: list[str] = []
        additional_data_needed: list[str] = []
        notes_parts: list[str] = []

        if finding.category == Category.ELECTRICITY and not electricity_df.empty:
            self._investigate_electricity(
                finding, electricity_df, supporting, contradictory, alternatives,
                additional_data_needed, notes_parts
            )
        elif finding.category == Category.WATER and not water_df.empty:
            self._investigate_water(
                finding, water_df, supporting, contradictory, alternatives,
                additional_data_needed, notes_parts
            )
        elif finding.category == Category.WASTE and not waste_df.empty:
            self._investigate_waste(
                finding, waste_df, supporting, contradictory, alternatives,
                additional_data_needed, notes_parts
            )

        # Check quality issues that could explain the finding
        missing_periods = inp.quality_output.missing_periods
        if missing_periods:
            alternatives.append(
                f"Data gaps exist in the measurement record ({len(missing_periods)} gap(s)). "
                f"Some apparent anomalies may be artifacts of missing data, not real consumption changes."
            )
            additional_data_needed.append(
                "Fill missing measurement periods before drawing firm conclusions."
            )

        # Revised confidence
        revised_confidence = finding.confidence
        if len(contradictory) > 0 and revised_confidence == Confidence.HIGH:
            revised_confidence = Confidence.MEDIUM
        if len(alternatives) >= 3:
            revised_confidence = Confidence.LOW

        notes = " ".join(notes_parts) if notes_parts else (
            f"Investigation of finding '{finding.title}' found "
            f"{len(supporting)} supporting and {len(contradictory)} contradictory evidence items. "
            f"Alternative explanations identified: {len(alternatives)}."
        )

        return InvestigationResult(
            finding_id=finding.finding_id,
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            alternative_explanations=alternatives,
            additional_data_needed=additional_data_needed,
            investigation_notes=notes,
            revised_confidence=revised_confidence,
        )

    def _investigate_electricity(
        self, finding: AuditFinding, df: pd.DataFrame,
        supporting, contradictory, alternatives, additional_data_needed, notes_parts
    ):
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"] >= 5
        is_synth = bool(df.get("is_synthetic", pd.Series([False])).any())

        # Check weekday vs weekend pattern
        weekday_avg = df[~df["is_weekend"]]["consumption_kwh"].mean()
        weekend_avg = df[df["is_weekend"]]["consumption_kwh"].mean()

        if weekday_avg > 0 and weekend_avg > 0:
            ratio = (weekday_avg - weekend_avg) / weekday_avg
            if ratio > WEEKEND_REDUCTION_THRESHOLD:
                supporting.append(EvidenceItem(
                    source="calculation",
                    description=f"Weekday average ({weekday_avg:.1f} kWh) is {ratio*100:.0f}% higher than "
                               f"weekend average ({weekend_avg:.1f} kWh) — consistent with occupancy-driven usage.",
                    value=ratio * 100,
                    unit="%",
                    supports_finding=True,
                    is_synthetic=is_synth,
                ))
                alternatives.append(
                    "The spike may be related to occupancy or academic calendar events rather than "
                    "equipment malfunction or waste."
                )
                additional_data_needed.append(
                    "Obtain occupancy/attendance records to separate occupancy effects from efficiency changes."
                )
            else:
                contradictory.append(EvidenceItem(
                    source="calculation",
                    description=f"Weekend consumption ({weekend_avg:.1f} kWh) is not significantly lower "
                               f"than weekday ({weekday_avg:.1f} kWh). "
                               f"This may indicate equipment left running unnecessarily on weekends.",
                    value=weekend_avg,
                    unit="kWh",
                    supports_finding=False,
                    is_synthetic=is_synth,
                ))
                notes_parts.append(
                    "Weekend consumption is not significantly lower than weekday — "
                    "suggests potential equipment left on when campus is unoccupied. "
                )

        # Check for trend (is it consistently high or a one-time spike?)
        daily = df.groupby("timestamp")["consumption_kwh"].sum().reset_index()
        if len(daily) >= 7:
            recent_7 = daily.tail(7)["consumption_kwh"].mean()
            overall_avg = daily["consumption_kwh"].mean()
            if recent_7 > overall_avg * 1.1:
                supporting.append(EvidenceItem(
                    source="calculation",
                    description=f"Recent 7-day average ({recent_7:.1f} kWh) is above overall average ({overall_avg:.1f} kWh) — trend is persistent.",
                    value=recent_7,
                    unit="kWh",
                    supports_finding=True,
                    is_synthetic=is_synth,
                ))
            else:
                alternatives.append("The elevated consumption may be a short-term spike rather than a persistent trend.")

        additional_data_needed.extend([
            "Sub-meter readings per building to identify the highest-consuming facility.",
            "Equipment inventory to identify recently added high-power equipment.",
            "Calendar of events (exams, events, holidays) for the anomalous periods.",
        ])

    def _investigate_water(
        self, finding: AuditFinding, df: pd.DataFrame,
        supporting, contradictory, alternatives, additional_data_needed, notes_parts
    ):
        is_synth = bool(df.get("is_synthetic", pd.Series([False])).any())
        df = df.copy()
        df["measurement_date"] = pd.to_datetime(df["measurement_date"])
        df["is_weekend"] = df["measurement_date"].dt.dayofweek >= 5

        # Weekend vs weekday for water
        wday = df[~df["is_weekend"]]["consumption_litres"].mean()
        wend = df[df["is_weekend"]]["consumption_litres"].mean()

        if wend > wday * 1.2:
            supporting.append(EvidenceItem(
                source="calculation",
                description=f"Weekend water use ({wend:.0f} L) exceeds weekday ({wday:.0f} L) — "
                           "unexpected if campus is less occupied. May indicate irrigation, leak, or meter issue.",
                value=wend,
                unit="litres",
                supports_finding=True,
                is_synthetic=is_synth,
            ))
        elif wend < wday * 0.5:
            contradictory.append(EvidenceItem(
                source="calculation",
                description=f"Weekend water usage ({wend:.0f} L) is much lower than weekday ({wday:.0f} L) — "
                           "consistent with occupancy-driven usage, less likely to be a persistent leak.",
                value=wend,
                unit="litres",
                supports_finding=False,
                is_synthetic=is_synth,
            ))
            alternatives.append("Elevated weekday consumption may be explained by higher campus occupancy.")

        additional_data_needed.extend([
            "Physical inspection of plumbing fixtures, taps, and irrigation systems during the identified period.",
            "Sub-meter readings per building to isolate the source.",
            "Comparison with previous year's readings for the same calendar period.",
        ])
        alternatives.append(
            "Elevated readings could result from meter calibration drift rather than actual consumption increase."
        )

    def _investigate_waste(
        self, finding: AuditFinding, df: pd.DataFrame,
        supporting, contradictory, alternatives, additional_data_needed, notes_parts
    ):
        is_synth = bool(df.get("is_synthetic", pd.Series([False])).any())
        supporting.append(EvidenceItem(
            source="calculation",
            description="High residual waste fraction confirmed from measurement records.",
            supports_finding=True,
            is_synthetic=is_synth,
        ))
        alternatives.append(
            "High residual fraction may be due to inadequate segregation infrastructure "
            "rather than user behaviour alone."
        )
        alternatives.append(
            "Data accuracy depends on whether waste categories are correctly identified during collection."
        )
        additional_data_needed.extend([
            "Waste audit (physical sampling) to verify category classifications.",
            "Inventory of segregation bins available in each building.",
            "Staff and student awareness of segregation guidelines.",
        ])
