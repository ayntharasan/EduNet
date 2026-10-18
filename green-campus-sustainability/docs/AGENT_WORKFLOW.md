# Agent Workflow — Green Campus Sustainability Auditor

The audit pipeline is a **deterministic, rule-based multi-agent system**. All agents are implemented in Python. No paid LLM API is required. Every handoff uses typed Pydantic v2 schemas.

---

## Pipeline Overview

```
Data Input (CSV upload / Demo data)
         │
         ▼
[1] DataQualityAgent       ← validates completeness, flags synthetic labels
         │  DataQualityOutput
         ▼
[2] SustainabilityAuditorAgent  ← computes KPIs, detects anomalies, generates findings
         │  AuditorOutput
         ▼
[3] InvestigationAgent     ← gathers corroborating evidence, rules out false positives
         │  InvestigationOutput
         ▼
[4] ActionPlanningAgent    ← generates actionable recommendations per finding
         │  ActionPlanningOutput
         ▼
[5] PrioritizationAgent    ← scores and ranks actions by impact × urgency × feasibility
         │  PrioritizationOutput
         ▼
[7] ReportingAgent         ← generates HTML report with full provenance

[6] VerificationAgent      ← invoked separately after an intervention, compares pre/post data
```

---

## Agent 1 — DataQualityAgent

**File:** [`backend/app/agents/data_quality_agent.py`](../backend/app/agents/data_quality_agent.py)

**Input schema:** `DataQualityInput(run_id: str)` + raw DataFrames

**Output schema:** `DataQualityOutput`
| Field | Type | Description |
|-------|------|-------------|
| `quality_score` | float | 0–100 composite score |
| `issues` | list[DataQualityIssue] | Each issue has field, severity, description, recommendation |
| `can_proceed` | bool | False only when data is unrecoverably bad |
| `is_synthetic` | bool | True when demo/synthetic data detected |
| `row_counts` | dict | electricity/water/waste record counts |

**Checks performed:**
- Missing value ratio per column
- Negative consumption values (physically impossible)
- Duplicate timestamps per building
- Synthetic data detection (`is_synthetic` column flag)
- Minimum record count thresholds

**Formula:** `quality_score = 100 × (1 − severity_weighted_issue_fraction)`

---

## Agent 2 — SustainabilityAuditorAgent

**File:** [`backend/app/agents/sustainability_auditor_agent.py`](../backend/app/agents/sustainability_auditor_agent.py)

**Input schema:** `AuditorInput` + current and baseline DataFrames

**Output schema:** `AuditorOutput`
| Field | Type | Description |
|-------|------|-------------|
| `kpis` | KPISummary | Aggregated key performance indicators |
| `findings` | list[FindingRecord] | Detected sustainability issues |

**KPIs computed (`KPISummary`):**
- `total_kwh`, `avg_daily_kwh`, `kwh_per_person`
- `total_litres`, `total_kl`, `litres_per_person_per_day`
- `total_waste_kg`, `diversion_rate_pct`
- `estimated_kg_co2e`, `estimated_t_co2e`
- `emission_factor_used`, `emission_factor_source`
- `emission_disclaimer` — always present, never omitted

**Detection rules:**
- Electricity spike vs. baseline (configurable % threshold)
- Isolation Forest anomaly detection (Z-score fallback for small samples)
- Water leak candidates (rolling median analysis)
- Waste diversion rate below 50% target
- High carbon intensity vs. benchmark

**Provenance rule:** If `DataQualityOutput.is_synthetic = True`, all findings carry `data_provenance = "synthetic_demo"`.

**Evidence:** Every `FindingRecord` includes a list of `EvidenceItem`:
```
EvidenceItem(
    source: str,         # "electricity_measurements", "water_measurements", etc.
    description: str,    # human-readable description
    value: float | None,
    unit: str | None,
    timestamp: date | None,
    provenance: str      # "user_input" | "synthetic_demo" | "external_benchmark"
)
```

---

## Agent 3 — InvestigationAgent

**File:** [`backend/app/agents/investigation_agent.py`](../backend/app/agents/investigation_agent.py)

**Input schema:** `InvestigationInput(run_id, findings, quality_output)` + DataFrames

**Output schema:** `InvestigationOutput`
- `results`: list of `InvestigationResult` per finding
  - `corroborating_evidence`: additional data points supporting the finding
  - `alternative_explanations`: list of possible non-problematic causes
  - `investigation_notes`: narrative summary
  - `confidence_adjustment`: `up` / `down` / `no_change`

**Methods:** Cross-correlation with water/waste data, occupancy-normalised comparison, temporal pattern analysis (weekday vs weekend, monthly trends).

---

## Agent 4 — ActionPlanningAgent

**File:** [`backend/app/agents/action_planning_agent.py`](../backend/app/agents/action_planning_agent.py)

**Input schema:** `ActionPlanningInput(run_id, findings, investigation_results)`

**Output schema:** `ActionPlanningOutput`
- `actions`: list of `ActionRecord`

**`ActionRecord` fields:**
| Field | Type | Values |
|-------|------|--------|
| `action_id` | str | UUID hex |
| `title` | str | Short action title |
| `description` | str | Full implementation guidance |
| `category` | Category | electricity / water / waste / emissions / general |
| `cost_category` | CostCategory | zero-cost / low-cost / medium-cost / requires-quotation |
| `implementation_difficulty` | Difficulty | easy / medium / hard |
| `time_horizon` | TimeHorizon | immediate / short-term / medium-term / long-term |
| `responsible_role` | str | e.g. "Facility Manager" |
| `verification_method` | str | How to confirm improvement |
| `finding_ids` | list[str] | Traceability back to findings |

**Rule base:** Actions are selected from a pattern-matching dictionary of finding category → action templates, contextualised with finding metadata. Actions are not invented randomly.

---

## Agent 5 — PrioritizationAgent

**File:** [`backend/app/agents/prioritization_agent.py`](../backend/app/agents/prioritization_agent.py)

**Input schema:** `PrioritizationInput(run_id, actions, weight_impact, weight_urgency, weight_confidence, weight_feasibility)`

**Output schema:** `PrioritizationOutput`
- `prioritized_actions`: list of `PrioritizedAction`
  - `priority_score`: 0–100
  - `priority_rank`: 1 = highest priority
  - `score_breakdown`: `{impact, urgency, confidence, feasibility}` individual scores

**Scoring formula:**
```
priority_score = (
    impact_score      × weight_impact      +
    urgency_score     × weight_urgency     +
    confidence_score  × weight_confidence  +
    feasibility_score × weight_feasibility
) / 100
```

**Default weights:** impact=40, urgency=25, confidence=20, feasibility=15 (all configurable via Settings page).

**Zero-cost bonus:** Zero-cost actions receive a feasibility boost so they rank higher than equivalent-impact costly actions, consistent with the ₹0 operational objective.

---

## Agent 6 — VerificationAgent

**File:** [`backend/app/agents/verification_agent.py`](../backend/app/agents/verification_agent.py)

> [!IMPORTANT]
> This agent is invoked **separately** (not in the main audit pipeline) after a real-world
> intervention has been completed and post-action measurements are available.

**Input schema:** `VerificationInput` + `pre_df: DataFrame` + `post_df: DataFrame`

**Output schema:** `VerificationOutput`
| Field | Type | Description |
|-------|------|-------------|
| `result` | VerificationResult | improved / no_change / regressed / insufficient_data |
| `baseline_value` | float | Mean of pre-action period |
| `post_action_value` | float | Mean of post-action period |
| `measured_change` | float | Absolute difference |
| `measured_change_pct` | float | Percentage change |
| `confidence` | Confidence | high / medium / low |
| `caveats` | list[str] | Always populated; synthetic data caveat always added |
| `metric_unit` | str | Unit of measurement |

**Verification rules:**
- Requires ≥7 days of data in each period → `insufficient_data` if not met
- **Improvement threshold:** ≥5% reduction in mean consumption
- **Regression threshold:** ≥5% increase in mean consumption
- If `is_synthetic=True` in input, a caveat is always added: *"Data is synthetic — result cannot be used for official reporting."*
- **Never automatically marks an action as "verified improved"** — only records the measurement comparison

---

## Agent 7 — ReportingAgent

**File:** [`backend/app/agents/reporting_agent.py`](../backend/app/agents/reporting_agent.py)

**Input schema:** `ReportingInput(run_id, auditor_output, investigation_output, prioritization_output, quality_output, campus_name, report_format)`

**Output schema:** `ReportingOutput`
| Field | Type | Description |
|-------|------|-------------|
| `report_id` | str | UUID hex |
| `title` | str | Report title |
| `file_path` | str | Path to generated HTML file |
| `format` | str | "html" |

**Report sections:** Executive summary · KPI table · Data quality note · Findings with evidence · Priority action plan · Emission estimate with disclaimer · Synthetic data banner (if applicable) · Methodology notes · Generation timestamp.

---

## Typed Schemas Reference

All handoff schemas are defined in [`backend/app/schemas/agent_schemas.py`](../backend/app/schemas/agent_schemas.py) using Pydantic v2.

**Enumerations:**
- `Category`: `electricity` · `water` · `waste` · `emissions` · `general`
- `Severity`: `critical` · `high` · `medium` · `low` · `info`
- `Confidence`: `high` · `medium` · `low`
- `VerificationResult`: `improved` · `no_change` · `regressed` · `insufficient_data`
- `CostCategory`: `zero-cost` · `low-cost` · `medium-cost` · `requires-quotation`
- `Difficulty`: `easy` · `medium` · `hard`
- `TimeHorizon`: `immediate` · `short-term` · `medium-term` · `long-term`

---

## Orchestrator

**File:** [`backend/app/agents/orchestrator.py`](../backend/app/agents/orchestrator.py)

- Wraps all 7 agents and wires typed handoffs
- Logs every agent execution to the `agent_executions` DB table (status, duration, error)
- On agent failure: logs error, uses safe empty fallback, continues pipeline
- Saves findings → `findings` table, actions → `actions` table, report → `audit_reports` table
- `run_audit()` returns `run_id: str`
- `run_verification()` returns verification result string

**Retry policy:** 1 retry per agent on exception. If all retries exhausted, the agent is marked `failed` in the DB and execution continues with safe defaults where possible.

---

## End-to-End Test Coverage

All 7 agents are covered by `backend/tests/test_agents_e2e.py` (41 tests). Key scenarios:
- Full pipeline runs without error
- Anomaly injected → detected by auditor
- Verification with <7 days → `insufficient_data`
- Verification with 18% reduction → `improved`
- Synthetic label propagates through all agents
- Zero-cost actions ranked above costly equivalents
