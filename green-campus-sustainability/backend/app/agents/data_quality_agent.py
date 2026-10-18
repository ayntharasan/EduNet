"""Agent 1: Data Quality Agent.

Validates imported measurements, computes a documented quality score,
and produces a structured QualityOutput for downstream agents.

Method: Deterministic rule-based. No ML or LLM required.
Quality score formula: 100 × (1 − weighted_issue_rate)
  where weighted_issue_rate = Σ(issue_weight × affected_records) / total_records
  weights: missing_value=2.0, duplicate=1.0, negative_value=3.0, implausible=1.5
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

from backend.app.schemas.agent_schemas import (
    AgentType, Category, Confidence, DataQualityInput, DataQualityOutput,
    QualityIssue, Severity,
)

logger = logging.getLogger(__name__)

# Configurable thresholds
THRESHOLDS = {
    "max_daily_kwh_per_building": 10_000,   # Flag if single building > 10,000 kWh/day
    "max_daily_litres_per_building": 500_000,  # Flag if > 500 kL/day per building
    "max_daily_waste_kg": 5_000,             # Flag if > 5 tonnes/day
    "min_daily_kwh": 0.0,                    # Negative is invalid
    "issue_weights": {
        "missing_value": 2.0,
        "duplicate": 1.0,
        "negative_value": 3.0,
        "implausible": 1.5,
        "schema_error": 2.5,
    },
}


class DataQualityAgent:
    """Agent 1: Validates data quality for all measurement categories.

    Callable interface:
        agent = DataQualityAgent()
        output: DataQualityOutput = agent.run(input_data, electricity_df, water_df, waste_df)

    No external dependencies required. Runs deterministically.
    """

    name = "data_quality_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(
        self,
        inp: DataQualityInput,
        electricity_df: pd.DataFrame,
        water_df: pd.DataFrame,
        waste_df: pd.DataFrame,
    ) -> DataQualityOutput:
        """Run data quality checks across all categories.

        Args:
            inp: Typed input schema with run_id and filters.
            electricity_df: DataFrame with columns [timestamp, building_id, consumption_kwh, is_synthetic].
            water_df: DataFrame with columns [measurement_date, building_id, consumption_litres, is_synthetic].
            waste_df: DataFrame with columns [measurement_date, building_id, total_waste_kg, is_synthetic].

        Returns:
            DataQualityOutput with quality score, issues, and limitations.
        """
        logger.info(f"[{self.name}] Starting data quality check for run_id={inp.run_id}")
        issues: list[QualityIssue] = []
        total_records: dict[str, int] = {}
        coverage_days: dict[str, int] = {}
        missing_periods: list[str] = []
        limitations: list[str] = []

        # --- Electricity ---
        elec_issues, elec_records, elec_days, elec_missing = self._check_electricity(electricity_df)
        issues.extend(elec_issues)
        total_records["electricity"] = elec_records
        coverage_days["electricity"] = elec_days
        missing_periods.extend(elec_missing)

        # --- Water ---
        water_issues, water_records, water_days, water_missing = self._check_water(water_df)
        issues.extend(water_issues)
        total_records["water"] = water_records
        coverage_days["water"] = water_days
        missing_periods.extend(water_missing)

        # --- Waste ---
        waste_issues, waste_records, waste_days, waste_missing = self._check_waste(waste_df)
        issues.extend(waste_issues)
        total_records["waste"] = waste_records
        coverage_days["waste"] = waste_days
        missing_periods.extend(waste_missing)

        # --- Synthetic data warning ---
        for df, cat in [(electricity_df, "electricity"), (water_df, "water"), (waste_df, "waste")]:
            if not df.empty and "is_synthetic" in df.columns and df["is_synthetic"].any():
                synth_count = int(df["is_synthetic"].sum())
                limitations.append(
                    f"⚠️  {synth_count} {cat} records are SYNTHETIC DEMO DATA. "
                    f"Do not use for real environmental reporting."
                )

        # --- Compute quality score ---
        total = sum(total_records.values()) or 1
        weighted_issues = sum(
            THRESHOLDS["issue_weights"].get(issue.issue_type, 1.0) * issue.affected_records
            for issue in issues
        )
        weighted_issue_rate = min(weighted_issues / total, 1.0)
        quality_score = round(100.0 * (1.0 - weighted_issue_rate), 1)

        can_proceed = quality_score > 30.0  # Below 30 = too unreliable for audit

        if not can_proceed:
            limitations.append(
                "Quality score is critically low. Audit results should be treated as unreliable. "
                "Resolve data issues before relying on findings."
            )

        output = DataQualityOutput(
            run_id=inp.run_id,
            quality_score=quality_score,
            total_records=total_records,
            coverage_days=coverage_days,
            missing_periods=missing_periods[:20],  # cap at 20 for readability
            issues=issues,
            limitations=limitations,
            can_proceed=can_proceed,
            timestamp=datetime.utcnow(),
        )
        logger.info(
            f"[{self.name}] Complete. Score={quality_score}, Issues={len(issues)}, "
            f"can_proceed={can_proceed}"
        )
        return output

    # ------------------------------------------------------------------
    # Internal checkers
    # ------------------------------------------------------------------

    def _check_electricity(
        self, df: pd.DataFrame
    ) -> tuple[list[QualityIssue], int, int, list[str]]:
        issues = []
        if df.empty:
            return [QualityIssue(
                category=Category.ELECTRICITY,
                issue_type="missing_value",
                description="No electricity records found in the database.",
                affected_records=0,
                severity=Severity.HIGH,
                recommendation="Import electricity measurement data before running an audit.",
            )], 0, 0, []

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        n = len(df)
        days = (df["timestamp"].max() - df["timestamp"].min()).days + 1

        # Negatives
        neg = (df["consumption_kwh"] < 0).sum()
        if neg > 0:
            issues.append(QualityIssue(
                category=Category.ELECTRICITY,
                issue_type="negative_value",
                description=f"{neg} electricity records have negative consumption_kwh.",
                affected_records=int(neg),
                severity=Severity.HIGH,
                recommendation="Investigate meter errors. Negative electricity consumption is physically invalid.",
            ))

        # Implausible highs
        high = (df["consumption_kwh"] > THRESHOLDS["max_daily_kwh_per_building"]).sum()
        if high > 0:
            issues.append(QualityIssue(
                category=Category.ELECTRICITY,
                issue_type="implausible",
                description=f"{high} records exceed {THRESHOLDS['max_daily_kwh_per_building']} kWh/day per building.",
                affected_records=int(high),
                severity=Severity.MEDIUM,
                recommendation="Verify meter readings. May indicate aggregation errors or genuine peak events.",
            ))

        # Duplicates (same building + same date)
        if "building_id" in df.columns:
            dup = df.duplicated(subset=["timestamp", "building_id"]).sum()
            if dup > 0:
                issues.append(QualityIssue(
                    category=Category.ELECTRICITY,
                    issue_type="duplicate",
                    description=f"{dup} duplicate electricity records (same building + date).",
                    affected_records=int(dup),
                    severity=Severity.MEDIUM,
                    recommendation="Remove or consolidate duplicate records before analysis.",
                ))

        # Missing periods (gaps > 1 day in daily data)
        missing_periods = self._find_gaps(df, "timestamp")

        return issues, n, days, missing_periods

    def _check_water(self, df: pd.DataFrame) -> tuple[list[QualityIssue], int, int, list[str]]:
        issues = []
        if df.empty:
            return [QualityIssue(
                category=Category.WATER,
                issue_type="missing_value",
                description="No water records found.",
                affected_records=0,
                severity=Severity.MEDIUM,
                recommendation="Import water measurement data.",
            )], 0, 0, []

        df = df.copy()
        df["measurement_date"] = pd.to_datetime(df["measurement_date"])
        n = len(df)
        days = (df["measurement_date"].max() - df["measurement_date"].min()).days + 1

        neg = (df["consumption_litres"] < 0).sum()
        if neg > 0:
            issues.append(QualityIssue(
                category=Category.WATER,
                issue_type="negative_value",
                description=f"{neg} water records have negative consumption_litres.",
                affected_records=int(neg),
                severity=Severity.HIGH,
                recommendation="Negative water consumption is invalid. Investigate meter data.",
            ))

        high = (df["consumption_litres"] > THRESHOLDS["max_daily_litres_per_building"]).sum()
        if high > 0:
            issues.append(QualityIssue(
                category=Category.WATER,
                issue_type="implausible",
                description=f"{high} records exceed {THRESHOLDS['max_daily_litres_per_building']} L/day per building.",
                affected_records=int(high),
                severity=Severity.MEDIUM,
                recommendation="Verify meter readings or check for aggregation errors.",
            ))

        missing_periods = self._find_gaps(df, "measurement_date")
        return issues, n, days, missing_periods

    def _check_waste(self, df: pd.DataFrame) -> tuple[list[QualityIssue], int, int, list[str]]:
        issues = []
        if df.empty:
            return [QualityIssue(
                category=Category.WASTE,
                issue_type="missing_value",
                description="No waste records found.",
                affected_records=0,
                severity=Severity.LOW,
                recommendation="Import waste measurement data.",
            )], 0, 0, []

        df = df.copy()
        df["measurement_date"] = pd.to_datetime(df["measurement_date"])
        n = len(df)
        days = (df["measurement_date"].max() - df["measurement_date"].min()).days + 1

        neg = (df["total_waste_kg"] < 0).sum()
        if neg > 0:
            issues.append(QualityIssue(
                category=Category.WASTE,
                issue_type="negative_value",
                description=f"{neg} waste records have negative total_waste_kg.",
                affected_records=int(neg),
                severity=Severity.HIGH,
                recommendation="Negative waste is invalid. Check data entry.",
            ))

        return issues, n, days, []

    @staticmethod
    def _find_gaps(df: pd.DataFrame, date_col: str, max_gap_days: int = 3) -> list[str]:
        """Identify gaps larger than max_gap_days in a date series."""
        if df.empty or len(df) < 2:
            return []
        daily = df[date_col].dt.normalize().drop_duplicates().sort_values()
        gaps = []
        prev = daily.iloc[0]
        for curr in daily.iloc[1:]:
            gap = (curr - prev).days
            if gap > max_gap_days:
                gaps.append(f"{prev.date()} to {curr.date()} ({gap} days)")
            prev = curr
        return gaps
