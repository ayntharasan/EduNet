"""Typed Pydantic schemas for inter-agent communication and API contracts.

All agent inputs and outputs use these schemas so handoffs are validated
and traceable. No free-form dicts are passed between agents.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    ELECTRICITY = "electricity"
    WATER = "water"
    WASTE = "waste"
    EMISSIONS = "emissions"
    GENERAL = "general"


class ActionStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class CostCategory(str, Enum):
    ZERO_COST = "zero-cost"
    LOW_COST = "low-cost"
    MEDIUM_COST = "medium-cost"
    REQUIRES_QUOTATION = "requires-quotation"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TimeHorizon(str, Enum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short-term"
    MEDIUM_TERM = "medium-term"
    LONG_TERM = "long-term"


class VerificationResult(str, Enum):
    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    REGRESSED = "regressed"
    INSUFFICIENT_DATA = "insufficient_data"


class AgentType(str, Enum):
    DETERMINISTIC = "deterministic"
    ML = "ml"
    LLM = "llm"


# ---------------------------------------------------------------------------
# Evidence item schema — used by multiple agents
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """A single piece of evidence supporting or refuting a finding."""
    source: str = Field(..., description="Source of evidence: 'measurement', 'calculation', 'rule', 'ml_model'")
    description: str = Field(..., description="Human-readable description of the evidence")
    value: float | None = Field(None, description="Numeric value if applicable")
    unit: str | None = Field(None, description="Unit of the value")
    date_range: str | None = Field(None, description="Date range this evidence covers")
    supports_finding: bool = Field(True, description="True if this supports the finding; False if contradictory")
    is_synthetic: bool = Field(False, description="True if this evidence comes from synthetic demo data")


# ---------------------------------------------------------------------------
# Agent 1: Data Quality Agent
# ---------------------------------------------------------------------------

class DataQualityInput(BaseModel):
    """Input to the Data Quality Agent."""
    run_id: str
    building_ids: list[int] | None = None
    period_start: date | None = None
    period_end: date | None = None
    categories: list[Category] = Field(default_factory=lambda: list(Category))


class QualityIssue(BaseModel):
    """A specific data quality issue found."""
    category: Category
    issue_type: str  # 'missing', 'duplicate', 'anomaly', 'negative', 'implausible', 'schema_error'
    description: str
    affected_records: int
    severity: Severity
    recommendation: str


class DataQualityOutput(BaseModel):
    """Output from the Data Quality Agent."""
    run_id: str
    agent: str = "data_quality_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    quality_score: float = Field(..., ge=0.0, le=100.0,
                                  description="0–100. Formula: 100 × (1 - weighted_issue_rate)")
    quality_score_formula: str = "100 × (1 − weighted_issue_rate); weights: missing=2, duplicate=1, anomaly=1.5"
    total_records: dict[str, int] = Field(
        default_factory=dict,
        description="Record counts per category: electricity, water, waste"
    )
    coverage_days: dict[str, int] = Field(default_factory=dict)
    missing_periods: list[str] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    can_proceed: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 2: Sustainability Auditor Agent
# ---------------------------------------------------------------------------

class AuditorInput(BaseModel):
    """Input to the Sustainability Auditor Agent."""
    run_id: str
    quality_output: DataQualityOutput
    period_start: date | None = None
    period_end: date | None = None
    baseline_start: date | None = None
    baseline_end: date | None = None
    emission_factor: float = 0.716
    emission_factor_source: str = "CEA CO2 Baseline Database Version 18 (2022-23)"


class AuditFinding(BaseModel):
    """A structured finding from the Sustainability Auditor."""
    finding_id: str
    category: Category
    severity: Severity
    confidence: Confidence
    title: str
    description: str
    metric_value: float | None = None
    metric_unit: str | None = None
    baseline_value: float | None = None
    pct_change: float | None = None
    affected_period_start: date | None = None
    affected_period_end: date | None = None
    building_id: int | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    rule_triggered: str | None = None  # e.g. "consumption_spike_threshold"


class KPISummary(BaseModel):
    """Summary KPIs calculated during the audit."""
    total_kwh: float | None = None
    avg_daily_kwh: float | None = None
    total_litres: float | None = None
    total_waste_kg: float | None = None
    estimated_kg_co2e: float | None = None
    estimated_t_co2e: float | None = None
    emission_factor_used: float | None = None
    emission_factor_source: str | None = None
    emission_disclaimer: str = (
        "Scope 2 electricity emissions estimate only. "
        "Not a certified GHG inventory. Consult a qualified practitioner for official reporting."
    )
    period_start: date | None = None
    period_end: date | None = None


class AuditorOutput(BaseModel):
    """Output from the Sustainability Auditor Agent."""
    run_id: str
    agent: str = "sustainability_auditor_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    kpis: KPISummary
    findings: list[AuditFinding] = Field(default_factory=list)
    thresholds_used: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 3: Investigation Agent
# ---------------------------------------------------------------------------

class InvestigationInput(BaseModel):
    """Input to the Investigation Agent."""
    run_id: str
    findings: list[AuditFinding]
    quality_output: DataQualityOutput


class InvestigationResult(BaseModel):
    """Investigation result for a single finding."""
    finding_id: str
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    contradictory_evidence: list[EvidenceItem] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    additional_data_needed: list[str] = Field(default_factory=list)
    investigation_notes: str = ""
    revised_confidence: Confidence | None = None


class InvestigationOutput(BaseModel):
    """Output from the Investigation Agent."""
    run_id: str
    agent: str = "investigation_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    results: list[InvestigationResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 4: Action Planning Agent
# ---------------------------------------------------------------------------

class ActionPlanningInput(BaseModel):
    """Input to the Action Planning Agent."""
    run_id: str
    findings: list[AuditFinding]
    investigation_results: list[InvestigationResult]


class RecommendedAction(BaseModel):
    """A concrete corrective action recommended by the Action Planning Agent."""
    action_id: str
    title: str
    description: str
    category: Category
    finding_ids: list[str] = Field(default_factory=list)
    responsible_role: str
    cost_category: CostCategory
    implementation_difficulty: Difficulty
    expected_impact: str  # Qualitative description — not a guaranteed saving
    prerequisites: list[str] = Field(default_factory=list)
    time_horizon: TimeHorizon
    verification_method: str
    is_estimate: bool = True  # Always true — mark estimates explicitly


class ActionPlanningOutput(BaseModel):
    """Output from the Action Planning Agent."""
    run_id: str
    agent: str = "action_planning_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    actions: list[RecommendedAction] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 5: Prioritization Agent
# ---------------------------------------------------------------------------

class PrioritizationInput(BaseModel):
    """Input to the Prioritization Agent."""
    run_id: str
    actions: list[RecommendedAction]
    weight_impact: float = Field(40.0, ge=0, le=100)
    weight_urgency: float = Field(25.0, ge=0, le=100)
    weight_confidence: float = Field(20.0, ge=0, le=100)
    weight_feasibility: float = Field(15.0, ge=0, le=100)


class PrioritizedAction(BaseModel):
    """An action with computed priority score."""
    action_id: str
    priority_rank: int
    priority_score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension scores: impact, urgency, confidence, feasibility"
    )
    score_formula: str = (
        "score = (impact×w_impact + urgency×w_urgency + confidence×w_confidence "
        "+ feasibility×w_feasibility) / 100"
    )
    weight_used: dict[str, float] = Field(default_factory=dict)


class PrioritizationOutput(BaseModel):
    """Output from the Prioritization Agent."""
    run_id: str
    agent: str = "prioritization_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    prioritized_actions: list[PrioritizedAction] = Field(default_factory=list)
    weights_used: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 6: Verification Agent
# ---------------------------------------------------------------------------

class VerificationInput(BaseModel):
    """Input to the Verification Agent."""
    action_id: str
    run_id: str
    baseline_start: date
    baseline_end: date
    post_action_start: date
    post_action_end: date
    category: Category
    building_id: int | None = None


class VerificationOutput(BaseModel):
    """Output from the Verification Agent."""
    action_id: str
    run_id: str
    agent: str = "verification_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    baseline_value: float | None = None
    post_action_value: float | None = None
    measured_change: float | None = None
    measured_change_pct: float | None = None
    metric_unit: str | None = None
    result: VerificationResult = VerificationResult.INSUFFICIENT_DATA
    confidence: Confidence = Confidence.LOW
    reviewer_notes: str = ""
    caveats: list[str] = Field(default_factory=list)
    # Critical: distinguish measured from projected
    is_measured: bool = False
    is_projected: bool = False
    projection_basis: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent 7: Reporting Agent
# ---------------------------------------------------------------------------

class ReportingInput(BaseModel):
    """Input to the Reporting Agent."""
    run_id: str
    auditor_output: AuditorOutput
    investigation_output: InvestigationOutput
    prioritization_output: PrioritizationOutput
    quality_output: DataQualityOutput
    campus_name: str = "Campus"
    report_format: str = "html"  # html or pdf


class ReportSection(BaseModel):
    """A single section of the audit report."""
    title: str
    content: str
    is_synthetic_warning: bool = False


class ReportingOutput(BaseModel):
    """Output from the Reporting Agent."""
    run_id: str
    agent: str = "reporting_agent"
    agent_type: AgentType = AgentType.DETERMINISTIC
    report_id: str
    title: str
    sections: list[ReportSection] = Field(default_factory=list)
    file_path: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    contains_synthetic_data: bool = True
    synthetic_data_warning: str = (
        "⚠️  This report contains SYNTHETIC DEMONSTRATION DATA. "
        "All measurements are artificially generated for demonstration purposes only. "
        "Do not use these figures for real environmental reporting."
    )


# ---------------------------------------------------------------------------
# Orchestrator / run status schema
# ---------------------------------------------------------------------------

class OrchestratorRunStatus(BaseModel):
    """Full status of an orchestrator run."""
    run_id: str
    status: str  # pending, running, complete, failed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    agent_statuses: dict[str, str] = Field(default_factory=dict)
    findings_count: int = 0
    actions_count: int = 0
    error: str | None = None
