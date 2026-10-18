"""Agent 6: Verification Agent.

Compares baseline vs post-action measurements to determine whether a
corrective action produced a measurable environmental improvement.

CRITICAL RULES:
- Never marks an action as verified based on a user clicking a button alone.
- Requires actual pre- and post-action measurements.
- Clearly distinguishes MEASURED change from PROJECTED change.
- Detects occupancy changes that could explain apparent improvements.
- Insufficient data → result = INSUFFICIENT_DATA, not SUCCESS.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import pandas as pd

from backend.app.analytics.energy import safe_pct_change
from backend.app.schemas.agent_schemas import (
    AgentType, Category, Confidence, VerificationInput, VerificationOutput,
    VerificationResult,
)

logger = logging.getLogger(__name__)

MIN_DAYS_REQUIRED = 7  # minimum days in each period to produce a meaningful comparison


class VerificationAgent:
    """Agent 6: Measures whether an action produced actual improvement.

    Callable interface:
        agent = VerificationAgent()
        output: VerificationOutput = agent.run(inp, pre_df, post_df)

    Never auto-verifies. Requires sufficient data in both periods.
    """

    name = "verification_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(
        self,
        inp: VerificationInput,
        pre_df: pd.DataFrame,
        post_df: pd.DataFrame,
    ) -> VerificationOutput:
        """Run verification for one action.

        Args:
            inp: VerificationInput with action_id, periods, and category.
            pre_df: Measurements from baseline (pre-action) period.
            post_df: Measurements from post-action period.

        Returns:
            VerificationOutput with measured change and confidence.
            Result is INSUFFICIENT_DATA when either period lacks enough records.
        """
        logger.info(
            f"[{self.name}] Verifying action={inp.action_id}, "
            f"category={inp.category}, run_id={inp.run_id}"
        )

        caveats: list[str] = []
        is_synth_pre = False
        is_synth_post = False

        # Check for synthetic data
        if not pre_df.empty and "is_synthetic" in pre_df.columns:
            is_synth_pre = bool(pre_df["is_synthetic"].any())
        if not post_df.empty and "is_synthetic" in post_df.columns:
            is_synth_post = bool(post_df["is_synthetic"].any())

        if is_synth_pre or is_synth_post:
            caveats.append(
                "⚠️  SYNTHETIC DATA: One or both measurement periods contain synthetic demo data. "
                "This verification is for DEMONSTRATION PURPOSES ONLY and does not represent "
                "real measured environmental improvements."
            )

        # Determine value column and date column by category
        val_col, date_col = self._get_columns(inp.category)

        # Check data sufficiency
        pre_days = self._count_days(pre_df, date_col)
        post_days = self._count_days(post_df, date_col)

        if pre_days < MIN_DAYS_REQUIRED or post_days < MIN_DAYS_REQUIRED:
            msg = (
                f"Insufficient data: baseline period has {pre_days} day(s), "
                f"post-action period has {post_days} day(s). "
                f"Minimum {MIN_DAYS_REQUIRED} days required in each period."
            )
            logger.warning(f"[{self.name}] {msg}")
            caveats.append(msg)
            return VerificationOutput(
                action_id=inp.action_id,
                run_id=inp.run_id,
                result=VerificationResult.INSUFFICIENT_DATA,
                confidence=Confidence.LOW,
                reviewer_notes=msg,
                caveats=caveats,
                is_measured=False,
                is_projected=False,
                timestamp=datetime.utcnow(),
            )

        # Compute per-day averages (not totals — periods may differ in length)
        if val_col not in pre_df.columns or val_col not in post_df.columns:
            caveats.append(f"Column '{val_col}' not found in measurement data.")
            return VerificationOutput(
                action_id=inp.action_id,
                run_id=inp.run_id,
                result=VerificationResult.INSUFFICIENT_DATA,
                confidence=Confidence.LOW,
                caveats=caveats,
                is_measured=False,
                timestamp=datetime.utcnow(),
            )

        baseline_avg = float(pre_df[val_col].sum() / pre_days)
        post_avg = float(post_df[val_col].sum() / post_days)
        measured_change = post_avg - baseline_avg
        pct_change = safe_pct_change(post_avg, baseline_avg)
        unit = self._get_unit(inp.category)

        # Determine result
        result, confidence = self._assess_result(pct_change, pre_days, post_days, caveats)

        # Check for occupancy change (warn if present in data)
        occ_caveat = self._check_occupancy_change(pre_df, post_df)
        if occ_caveat:
            caveats.append(occ_caveat)
            if confidence == Confidence.HIGH:
                confidence = Confidence.MEDIUM

        pct_str = f"{pct_change:+.1f}%" if pct_change is not None else "undefined"
        reviewer_notes = (
            f"Baseline daily average: {baseline_avg:.2f} {unit}. "
            f"Post-action daily average: {post_avg:.2f} {unit}. "
            f"Measured change: {measured_change:+.2f} {unit} ({pct_str}). "
            f"Based on {pre_days} baseline days and {post_days} post-action days."
        )

        output = VerificationOutput(
            action_id=inp.action_id,
            run_id=inp.run_id,
            baseline_value=round(baseline_avg, 3),
            post_action_value=round(post_avg, 3),
            measured_change=round(measured_change, 3),
            measured_change_pct=round(pct_change, 2) if pct_change is not None else None,
            metric_unit=f"{unit}/day (average)",
            result=result,
            confidence=confidence,
            reviewer_notes=reviewer_notes,
            caveats=caveats,
            is_measured=True,  # actual measurements used
            is_projected=False,
            timestamp=datetime.utcnow(),
        )

        logger.info(
            f"[{self.name}] Result: {result.value}, confidence={confidence.value}, "
            f"change={measured_change:+.2f} {unit}"
        )
        return output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_columns(category: Category) -> tuple[str, str]:
        if category == Category.ELECTRICITY:
            return "consumption_kwh", "timestamp"
        elif category == Category.WATER:
            return "consumption_litres", "measurement_date"
        elif category == Category.WASTE:
            return "total_waste_kg", "measurement_date"
        return "consumption_kwh", "timestamp"

    @staticmethod
    def _get_unit(category: Category) -> str:
        return {"electricity": "kWh", "water": "litres", "waste": "kg"}.get(
            category.value, "units"
        )

    @staticmethod
    def _count_days(df: pd.DataFrame, date_col: str) -> int:
        if df.empty or date_col not in df.columns:
            return 0
        dates = pd.to_datetime(df[date_col]).dt.normalize().drop_duplicates()
        return len(dates)

    @staticmethod
    def _assess_result(
        pct_change: float | None,
        pre_days: int,
        post_days: int,
        caveats: list[str],
    ) -> tuple[VerificationResult, Confidence]:
        if pct_change is None:
            caveats.append("Cannot compute percentage change (baseline is zero or undefined).")
            return VerificationResult.INSUFFICIENT_DATA, Confidence.LOW

        if pct_change < -5.0:
            result = VerificationResult.IMPROVED
            confidence = Confidence.HIGH if (pre_days >= 14 and post_days >= 14) else Confidence.MEDIUM
        elif pct_change > 5.0:
            result = VerificationResult.REGRESSED
            confidence = Confidence.HIGH if (pre_days >= 14 and post_days >= 14) else Confidence.MEDIUM
            caveats.append(
                "Consumption INCREASED post-action. The action does not appear to have reduced consumption. "
                "Consider whether the action was implemented as planned."
            )
        else:
            result = VerificationResult.NO_CHANGE
            confidence = Confidence.MEDIUM
            caveats.append(
                f"Change of {pct_change:+.1f}% is within the ±5% no-change threshold. "
                "Cannot confirm a meaningful improvement or regression."
            )

        if pre_days < 14:
            caveats.append(
                f"Baseline period is only {pre_days} days. "
                "Longer baseline (≥14 days) would increase confidence."
            )

        return result, confidence

    @staticmethod
    def _check_occupancy_change(pre_df: pd.DataFrame, post_df: pd.DataFrame) -> str | None:
        """Warn if occupancy changed between periods (may explain apparent improvements)."""
        for df in [pre_df, post_df]:
            if "occupancy_count" not in df.columns:
                return None

        pre_occ = pre_df["occupancy_count"].dropna()
        post_occ = post_df["occupancy_count"].dropna()

        if pre_occ.empty or post_occ.empty:
            return None

        pre_avg = pre_occ.mean()
        post_avg = post_occ.mean()

        if pre_avg > 0:
            occ_change_pct = (post_avg - pre_avg) / pre_avg * 100
            if abs(occ_change_pct) > 15:
                return (
                    f"⚠️  Occupancy changed by {occ_change_pct:+.0f}% between periods "
                    f"(baseline avg: {pre_avg:.0f}, post-action avg: {post_avg:.0f}). "
                    "Apparent consumption change may partly reflect occupancy differences, "
                    "not solely the corrective action."
                )
        return None
