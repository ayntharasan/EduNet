"""Agent 5: Prioritization Agent.

Ranks actions using a transparent weighted scoring formula.
All weights are configurable. Score calculation is shown for every action.

Score formula:
  score = (impact_score × w_impact + urgency_score × w_urgency
           + confidence_score × w_confidence + feasibility_score × w_feasibility) / 100

Where w_impact + w_urgency + w_confidence + w_feasibility = 100.
"""
from __future__ import annotations

import logging
from datetime import datetime

from backend.app.schemas.agent_schemas import (
    AgentType, Category, CostCategory, Difficulty, PrioritizationInput,
    PrioritizationOutput, PrioritizedAction, RecommendedAction, Severity,
    TimeHorizon,
)

logger = logging.getLogger(__name__)

# Dimension score lookups (0–10 scale, normalized to 0–100 in formula)
IMPACT_SCORES: dict[Category, float] = {
    Category.ELECTRICITY: 8.0,
    Category.WATER: 7.0,
    Category.WASTE: 6.0,
    Category.EMISSIONS: 9.0,
    Category.GENERAL: 5.0,
}

URGENCY_SCORES: dict[TimeHorizon, float] = {
    TimeHorizon.IMMEDIATE: 10.0,
    TimeHorizon.SHORT_TERM: 7.5,
    TimeHorizon.MEDIUM_TERM: 5.0,
    TimeHorizon.LONG_TERM: 2.5,
}

FEASIBILITY_SCORES: dict[tuple, float] = {
    (CostCategory.ZERO_COST, Difficulty.EASY): 10.0,
    (CostCategory.ZERO_COST, Difficulty.MEDIUM): 9.0,
    (CostCategory.ZERO_COST, Difficulty.HARD): 8.0,
    (CostCategory.LOW_COST, Difficulty.EASY): 8.5,
    (CostCategory.LOW_COST, Difficulty.MEDIUM): 7.0,
    (CostCategory.LOW_COST, Difficulty.HARD): 5.5,
    (CostCategory.MEDIUM_COST, Difficulty.EASY): 6.0,
    (CostCategory.MEDIUM_COST, Difficulty.MEDIUM): 5.0,
    (CostCategory.MEDIUM_COST, Difficulty.HARD): 3.5,
    (CostCategory.REQUIRES_QUOTATION, Difficulty.EASY): 4.0,
    (CostCategory.REQUIRES_QUOTATION, Difficulty.MEDIUM): 3.0,
    (CostCategory.REQUIRES_QUOTATION, Difficulty.HARD): 2.0,
}


class PrioritizationAgent:
    """Agent 5: Assigns transparent priority scores to recommended actions.

    Callable interface:
        agent = PrioritizationAgent()
        output: PrioritizationOutput = agent.run(inp)

    All weights are passed in via inp and stored with the output.
    Score formula is embedded in every PrioritizedAction for traceability.
    """

    name = "prioritization_agent"
    agent_type = AgentType.DETERMINISTIC

    def run(self, inp: PrioritizationInput) -> PrioritizationOutput:
        logger.info(
            f"[{self.name}] Prioritizing {len(inp.actions)} actions for run_id={inp.run_id}"
        )

        # Validate weights sum to 100
        total_weight = inp.weight_impact + inp.weight_urgency + inp.weight_confidence + inp.weight_feasibility
        if abs(total_weight - 100.0) > 0.01:
            logger.warning(
                f"[{self.name}] Weights sum to {total_weight}, not 100. Normalizing."
            )
            scale = 100.0 / total_weight
            w_impact = inp.weight_impact * scale
            w_urgency = inp.weight_urgency * scale
            w_confidence = inp.weight_confidence * scale
            w_feasibility = inp.weight_feasibility * scale
        else:
            w_impact = inp.weight_impact
            w_urgency = inp.weight_urgency
            w_confidence = inp.weight_confidence
            w_feasibility = inp.weight_feasibility

        weights = {
            "impact": w_impact,
            "urgency": w_urgency,
            "confidence": w_confidence,
            "feasibility": w_feasibility,
        }

        scored: list[tuple[float, PrioritizedAction]] = []

        for action in inp.actions:
            score, breakdown = self._score_action(action, w_impact, w_urgency, w_confidence, w_feasibility)
            pa = PrioritizedAction(
                action_id=action.action_id,
                priority_rank=0,  # assigned after sorting
                priority_score=round(score, 2),
                score_breakdown=breakdown,
                weight_used=weights,
            )
            scored.append((score, pa))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Assign ranks
        prioritized = []
        for rank, (_, pa) in enumerate(scored, start=1):
            pa.priority_rank = rank
            prioritized.append(pa)

        logger.info(
            f"[{self.name}] Complete. Top action score: "
            f"{prioritized[0].priority_score if prioritized else 'N/A'}"
        )
        return PrioritizationOutput(
            run_id=inp.run_id,
            prioritized_actions=prioritized,
            weights_used=weights,
            timestamp=datetime.utcnow(),
        )

    def _score_action(
        self,
        action: RecommendedAction,
        w_impact: float,
        w_urgency: float,
        w_confidence: float,
        w_feasibility: float,
    ) -> tuple[float, dict[str, float]]:
        """Compute the weighted priority score.

        Formula:
            score = (impact × w_impact + urgency × w_urgency
                     + confidence × w_confidence + feasibility × w_feasibility) / 100

        All sub-scores are on a 0–10 scale.
        """
        impact_s = IMPACT_SCORES.get(action.category, 5.0)
        urgency_s = URGENCY_SCORES.get(action.time_horizon, 5.0)

        feasibility_key = (action.cost_category, action.implementation_difficulty)
        feasibility_s = FEASIBILITY_SCORES.get(feasibility_key, 5.0)

        # Confidence derived from whether action links to a finding
        confidence_s = 8.0 if action.finding_ids else 5.0

        # Normalize sub-scores (0–10) to 0–100 by multiplying by 10
        score = (
            impact_s * 10 * w_impact / 100
            + urgency_s * 10 * w_urgency / 100
            + confidence_s * 10 * w_confidence / 100
            + feasibility_s * 10 * w_feasibility / 100
        )

        breakdown = {
            "impact_score_raw": impact_s,
            "urgency_score_raw": urgency_s,
            "confidence_score_raw": confidence_s,
            "feasibility_score_raw": feasibility_s,
            "impact_weighted": round(impact_s * 10 * w_impact / 100, 2),
            "urgency_weighted": round(urgency_s * 10 * w_urgency / 100, 2),
            "confidence_weighted": round(confidence_s * 10 * w_confidence / 100, 2),
            "feasibility_weighted": round(feasibility_s * 10 * w_feasibility / 100, 2),
        }

        return score, breakdown
