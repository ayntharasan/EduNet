"""Agent 4: Action Planning Agent.

Generates specific corrective actions for each finding.
Prefers no-cost and low-cost actions first.
All expected impacts are explicitly labelled as estimates.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from backend.app.schemas.agent_schemas import (
    ActionPlanningInput, ActionPlanningOutput, AgentType, AuditFinding,
    Category, CostCategory, Difficulty, InvestigationResult,
    RecommendedAction, Severity, TimeHorizon,
)

logger = logging.getLogger(__name__)


# Action templates by finding category and severity
# Prefer zero-cost / low-cost actions first (sorted by cost_category)
ACTION_TEMPLATES = {
    Category.ELECTRICITY: [
        {
            "title": "Conduct lighting switch-off awareness campaign",
            "description": (
                "Launch a targeted awareness campaign to remind staff and students to switch off "
                "lights, computers, and equipment when leaving rooms. Use signage, emails, and "
                "champions in each department."
            ),
            "responsible_role": "Facilities Manager / Student Sustainability Committee",
            "cost_category": CostCategory.ZERO_COST,
            "difficulty": Difficulty.EASY,
            "expected_impact": (
                "ESTIMATE: Awareness campaigns typically achieve 5–15% reduction in standby losses "
                "in comparable institutional settings. Actual impact depends on baseline behaviour. "
                "No specific saving is guaranteed."
            ),
            "prerequisites": ["Identify departmental champions", "Prepare communication materials"],
            "time_horizon": TimeHorizon.IMMEDIATE,
            "verification_method": "Compare electricity consumption for the same building over the same period one semester later.",
        },
        {
            "title": "Audit and schedule equipment shutdown for nights and weekends",
            "description": (
                "Identify non-essential equipment (computers, projectors, HVAC zones) that remains "
                "energised outside working hours. Create a shutdown checklist and automate where possible."
            ),
            "responsible_role": "Facilities Manager / IT Department",
            "cost_category": CostCategory.ZERO_COST,
            "difficulty": Difficulty.EASY,
            "expected_impact": (
                "ESTIMATE: Night/weekend shutdown of non-essential equipment can reduce standby load. "
                "Actual savings depend on inventory and current baseline — inspect before claiming savings."
            ),
            "prerequisites": ["Building access audit", "Equipment inventory per room"],
            "time_horizon": TimeHorizon.SHORT_TERM,
            "verification_method": "Sub-meter reading comparison for affected buildings before and after implementation.",
        },
        {
            "title": "Inspect and repair faulty metering or identified anomalous equipment",
            "description": (
                "Investigate the specific days or periods flagged as anomalies. Check whether "
                "a particular piece of equipment (e.g., HVAC, industrial equipment, computing cluster) "
                "was running unexpectedly."
            ),
            "responsible_role": "Facilities Manager / Technical Staff",
            "cost_category": CostCategory.LOW_COST,
            "difficulty": Difficulty.MEDIUM,
            "expected_impact": (
                "ESTIMATE: Depends on identified root cause. Equipment faults can account for "
                "significant unexplained consumption. Actual saving is unknown until fault is confirmed."
            ),
            "prerequisites": ["Sub-meter readings or building walk-through during anomaly period"],
            "time_horizon": TimeHorizon.SHORT_TERM,
            "verification_method": "Before/after sub-meter comparison after repair or equipment adjustment.",
        },
    ],
    Category.WATER: [
        {
            "title": "Inspect plumbing fixtures in buildings with elevated water use",
            "description": (
                "Send trained maintenance staff to physically inspect all taps, toilets, urinals, "
                "and water-using equipment in buildings showing elevated consumption. "
                "Log findings. This inspection must happen before claiming a leak exists."
            ),
            "responsible_role": "Facilities Manager / Maintenance Team",
            "cost_category": CostCategory.LOW_COST,
            "difficulty": Difficulty.EASY,
            "expected_impact": (
                "ESTIMATE: Fixing a continuously running toilet can save several hundred litres per day. "
                "Actual saving is unknown until the source is confirmed by inspection."
            ),
            "prerequisites": ["Access to affected buildings", "Maintenance inspection checklist"],
            "time_horizon": TimeHorizon.IMMEDIATE,
            "verification_method": "Daily water meter readings before and after repairs.",
        },
        {
            "title": "Install water-saving fixtures where metering shows high use",
            "description": (
                "After confirming consumption sources through inspection, consider installing "
                "low-flow tap aerators and dual-flush toilet conversions in high-use buildings."
            ),
            "responsible_role": "Facilities Manager",
            "cost_category": CostCategory.LOW_COST,
            "difficulty": Difficulty.MEDIUM,
            "expected_impact": (
                "ESTIMATE: Low-flow fixtures typically reduce fixture-level consumption by 20–40% "
                "compared to standard fittings. Savings depend on usage frequency and fixture type."
            ),
            "prerequisites": ["Completed plumbing inspection", "Approval for minor works"],
            "time_horizon": TimeHorizon.SHORT_TERM,
            "verification_method": "Sub-meter water readings per building over 30-day period after installation.",
        },
    ],
    Category.WASTE: [
        {
            "title": "Improve waste segregation infrastructure and awareness",
            "description": (
                "Audit the number and placement of labelled segregation bins (wet/dry/residual). "
                "Ensure every common area has clearly labelled bins for all three categories. "
                "Run a one-week awareness campaign."
            ),
            "responsible_role": "Facilities Manager / Sustainability Officer",
            "cost_category": CostCategory.LOW_COST,
            "difficulty": Difficulty.EASY,
            "expected_impact": (
                "ESTIMATE: Proper bin placement and labelling can improve diversion rates. "
                "Actual impact depends on current infrastructure and user behaviour."
            ),
            "prerequisites": ["Waste bin audit", "Communication plan"],
            "time_horizon": TimeHorizon.SHORT_TERM,
            "verification_method": "Compare waste category breakdown from weekly measurements before and after intervention.",
        },
        {
            "title": "Engage canteen and food service for wet waste reduction",
            "description": (
                "Work with the campus canteen to reduce food waste through portion control, "
                "composting arrangements, and donation of surplus food where feasible."
            ),
            "responsible_role": "Sustainability Officer / Canteen Manager",
            "cost_category": CostCategory.ZERO_COST,
            "difficulty": Difficulty.MEDIUM,
            "expected_impact": (
                "ESTIMATE: Food waste reduction programmes in institutional canteens have shown "
                "15–30% reduction in food waste in comparable settings. Results vary significantly."
            ),
            "prerequisites": ["Canteen management buy-in", "Composting partner or facility"],
            "time_horizon": TimeHorizon.MEDIUM_TERM,
            "verification_method": "Monthly wet waste weight measurements over 3 months before and after.",
        },
    ],
}


class ActionPlanningAgent:
    """Agent 4: Recommends corrective actions for each finding.

    Callable interface:
        agent = ActionPlanningAgent()
        output: ActionPlanningOutput = agent.run(inp)

    Prefers zero-cost actions first. All impacts are labelled as estimates.
    """

    name = "action_planning_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(self, inp: ActionPlanningInput) -> ActionPlanningOutput:
        logger.info(
            f"[{self.name}] Generating actions for {len(inp.findings)} findings, "
            f"run_id={inp.run_id}"
        )

        # Map finding_id → investigation result for quick lookup
        inv_map: dict[str, InvestigationResult] = {
            r.finding_id: r for r in inp.investigation_results
        }

        actions: list[RecommendedAction] = []
        seen_titles: set[str] = set()  # avoid duplicate action titles

        # Sort findings by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings: list[AuditFinding] = sorted(
            inp.findings, key=lambda f: severity_order.get(f.severity, 99)
        )

        for finding in sorted_findings:
            templates = ACTION_TEMPLATES.get(finding.category, [])
            inv = inv_map.get(finding.finding_id)

            for template in templates:
                title = template["title"]
                if title in seen_titles:
                    continue  # don't duplicate

                action = RecommendedAction(
                    action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                    title=title,
                    description=template["description"],
                    category=finding.category,
                    finding_ids=[finding.finding_id],
                    responsible_role=template["responsible_role"],
                    cost_category=template["cost_category"],
                    implementation_difficulty=template["difficulty"],
                    expected_impact=template["expected_impact"],
                    prerequisites=template["prerequisites"],
                    time_horizon=template["time_horizon"],
                    verification_method=template["verification_method"],
                    is_estimate=True,
                )
                actions.append(action)
                seen_titles.add(title)

            # For high/critical findings with low confidence, add investigation action
            if finding.severity in (Severity.HIGH, Severity.CRITICAL) and inv and \
               inv.revised_confidence and inv.revised_confidence.value == "low":
                additional_data = inv.additional_data_needed
                if additional_data:
                    inv_title = f"Gather additional data to confirm finding: {finding.title[:60]}"
                    if inv_title not in seen_titles:
                        actions.append(RecommendedAction(
                            action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                            title=inv_title,
                            description=(
                                f"Current evidence confidence is LOW. Before committing resources, "
                                f"gather: {'; '.join(additional_data[:3])}."
                            ),
                            category=finding.category,
                            finding_ids=[finding.finding_id],
                            responsible_role="Data/Sustainability Officer",
                            cost_category=CostCategory.ZERO_COST,
                            implementation_difficulty=Difficulty.EASY,
                            expected_impact=(
                                "This action improves decision quality, not directly environmental performance. "
                                "It reduces the risk of acting on incorrect findings."
                            ),
                            prerequisites=[],
                            time_horizon=TimeHorizon.IMMEDIATE,
                            verification_method="Confirm that additional data has been collected and re-run the audit.",
                            is_estimate=True,
                        ))
                        seen_titles.add(inv_title)

        logger.info(f"[{self.name}] Generated {len(actions)} actions.")
        return ActionPlanningOutput(
            run_id=inp.run_id,
            actions=actions,
            timestamp=datetime.utcnow(),
        )
