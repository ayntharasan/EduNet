# Architecture — Green Campus Sustainability Auditor

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      Browser / UI                            │
│          React 19 + Vite 6 + Tailwind CSS v4 + Recharts      │
│                   http://localhost:5173                       │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP/JSON  (Vite proxy → :8000)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Application                         │
│               http://127.0.0.1:8000                          │
│                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │  9 API Route │  │  7 Agents   │  │  Analytics Layer  │   │
│  │   modules    │  │ Orchestrator│  │  energy / water / │   │
│  └──────┬───────┘  └──────┬──────┘  │  waste_analytics  │   │
│         │                 │         └───────────────────┘   │
│         ▼                 ▼                                  │
│  ┌─────────────────────────────────┐  ┌──────────────────┐  │
│  │       SQLAlchemy ORM            │  │    ML Layer      │  │
│  │       14 Database Tables        │  │ anomaly_detection│  │
│  └───────────────┬─────────────────┘  │ forecasting      │  │
│                  │                    └──────────────────┘  │
│                  ▼                                           │
│  ┌──────────────────────┐                                    │
│  │   SQLite Database    │                                    │
│  │   green_campus.db    │                                    │
│  └──────────────────────┘                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Web framework | FastAPI | 0.115.5 |
| ASGI server | Uvicorn | 0.32.1 |
| Data validation | Pydantic v2 | 2.10.3 |
| Settings | pydantic-settings | 2.6.1 |
| ORM | SQLAlchemy | 2.0.36 |
| Migrations | Alembic | 1.14.0 |
| Database | SQLite | (stdlib) |
| Data processing | Pandas | 2.2.3 |
| Numerical | NumPy | 2.2.0 |
| ML | Scikit-learn | 1.5.2 |
| Templating | Jinja2 | 3.1.4 |
| HTTP client | httpx | 0.28.1 |
| File uploads | python-multipart | 0.0.19 |
| Testing | pytest | 8.3.4 |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 19 |
| Build tool | Vite | 6 |
| Styling | Tailwind CSS | v4 (via @tailwindcss/vite) |
| Charts | Recharts | latest |
| Icons | Lucide React | latest |
| Routing | React Router | v7 |
| HTTP | fetch API | (browser built-in) |

---

## Database Schema (14 Tables)

```
buildings               — campus buildings with floor area and capacity
electricity_measurements — daily kWh readings per building
water_measurements      — daily litres per building
waste_measurements      — daily waste category breakdown per building
dataset_sources         — provenance record for every imported file
audit_runs              — one record per pipeline execution (status, timing)
agent_executions        — per-agent execution log (status, duration, errors)
findings                — sustainability issues with evidence (stored as JSON)
actions                 — recommended corrective actions with priority scores
action_status_history   — full audit trail of action status changes
verifications           — pre/post measurement comparison results
emission_factors        — configurable CO₂e factors with source citation
app_settings            — campus name, Ollama config, priority weights
audit_reports           — generated report metadata and file paths
```

### Key Relationships

```
buildings ──< electricity_measurements
buildings ──< water_measurements
buildings ──< waste_measurements
audit_runs ──< agent_executions
audit_runs ──< findings
audit_runs ──< actions
audit_runs ──< audit_reports
actions ──< action_status_history
actions ──< verifications
dataset_sources ──< electricity_measurements (optional FK)
dataset_sources ──< water_measurements (optional FK)
dataset_sources ──< waste_measurements (optional FK)
```

---

## API Routes

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `GET /health` | health.py | Health check |
| `GET /api/buildings` | buildings.py | List buildings |
| `POST /api/buildings` | buildings.py | Create building |
| `GET /api/datasets` | datasets.py | List dataset sources |
| `POST /api/datasets/upload/electricity` | datasets.py | Upload electricity CSV |
| `POST /api/datasets/upload/water` | datasets.py | Upload water CSV |
| `POST /api/datasets/upload/waste` | datasets.py | Upload waste CSV |
| `POST /api/audit/run` | audit.py | Trigger audit (background) |
| `GET /api/audit/runs` | audit.py | List all audit runs |
| `GET /api/audit/runs/{run_id}` | audit.py | Get run status + findings |
| `GET /api/analytics/dashboard` | analytics.py | Dashboard KPIs |
| `GET /api/analytics/energy` | analytics.py | Energy chart data |
| `GET /api/analytics/water` | analytics.py | Water chart data |
| `GET /api/analytics/waste` | analytics.py | Waste chart data |
| `GET /api/analytics/carbon` | analytics.py | Carbon estimates |
| `GET /api/actions` | actions.py | List actions |
| `PATCH /api/actions/{action_id}/status` | actions.py | Update action status |
| `POST /api/verification/run` | verification.py | Run post-action verification |
| `GET /api/reports` | reports.py | List reports |
| `GET /api/reports/{report_id}/download` | reports.py | Download HTML report |
| `GET /api/settings` | settings_api.py | Get settings |
| `PATCH /api/settings` | settings_api.py | Update settings |

Full interactive documentation: **`http://127.0.0.1:8000/api/docs`**

---

## Directory Structure

```
green-campus-sustainability/
├── backend/
│   ├── app/
│   │   ├── agents/          ← 7 agent implementations + orchestrator.py
│   │   ├── analytics/       ← energy.py, water.py, waste_analytics.py
│   │   ├── api/             ← 9 FastAPI route modules
│   │   ├── core/            ← config.py, logging_config.py
│   │   ├── database/        ← session.py, init_db.py, Base
│   │   ├── ml/              ← anomaly_detection.py, forecasting.py
│   │   ├── models/          ← 14 SQLAlchemy model files
│   │   ├── reports/         ← Jinja2 HTML report templates
│   │   ├── schemas/         ← agent_schemas.py (all Pydantic handoffs)
│   │   └── main.py          ← FastAPI app + lifespan startup
│   └── tests/
│       ├── test_agents_e2e.py   ← 41 agent + analytics tests
│       └── test_api.py          ← API integration tests (TestClient)
├── data/
│   ├── demo/                ← synthetic demo CSVs (is_synthetic=True)
│   ├── templates/           ← blank import templates
│   ├── raw/                 ← user uploads — git-ignored
│   └── processed/           ← pipeline outputs — git-ignored
├── docs/                    ← all documentation
├── frontend/
│   ├── src/
│   │   ├── pages/           ← 12 React page components
│   │   ├── App.jsx          ← sidebar nav + routing
│   │   ├── api.js           ← all fetch() wrappers
│   │   └── main.jsx         ← React entry point
│   └── vite.config.js       ← Tailwind v4 plugin + proxy config
├── models/                  ← saved ML artifacts — git-ignored
├── reports/                 ← generated HTML audit reports
├── scripts/
│   ├── generate_demo_data.py
│   ├── run_demo.py
│   ├── validate_datasets.py
│   └── download_datasets.py
├── uploads/                 ← user file uploads — git-ignored
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

## Data Flow — Audit Pipeline

```
CSV Upload  ─────────────────────────┐
Demo Data   → generate_demo_data.py ─┤
                                     ▼
                             Pandas DataFrames
                                     │
                    ┌────────────────▼───────────────────┐
                    │          AuditOrchestrator          │
                    │                                     │
                    │  [1] DataQualityAgent               │
                    │       └─ quality_score, issues      │
                    │                  │                  │
                    │  [2] SustainabilityAuditorAgent     │
                    │       ├─ energy.py KPIs             │
                    │       ├─ water.py KPIs              │
                    │       ├─ waste_analytics KPIs       │
                    │       └─ anomaly_detection.py       │
                    │              → FindingRecord list   │
                    │                  │                  │
                    │  [3] InvestigationAgent             │
                    │       └─ evidence + explanations    │
                    │                  │                  │
                    │  [4] ActionPlanningAgent            │
                    │       └─ ActionRecord list          │
                    │                  │                  │
                    │  [5] PrioritizationAgent            │
                    │       └─ ranked + scored actions    │
                    │                  │                  │
                    │  [7] ReportingAgent                 │
                    │       └─ HTML report → reports/     │
                    └────────────────────────────────────┘

Post-intervention:
  new measurements → [6] VerificationAgent
                          └─ improved / no_change / regressed / insufficient_data
```

---

## Frontend Pages (12 Routes)

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | KPI cards, summary charts |
| `/audit` | AuditPage | Trigger audit, view run history |
| `/electricity` | ElectricityPage | Energy charts and anomaly flags |
| `/water` | WaterPage | Water consumption and leak candidates |
| `/waste` | WastePage | Waste categories and diversion rate |
| `/carbon` | CarbonPage | CO₂ estimates with disclaimer |
| `/findings` | FindingsPage | All findings with evidence |
| `/actions` | ActionsPage | Priority action plan, status updates |
| `/verification` | VerificationPage | Post-action verification form |
| `/datasets` | DatasetsPage | Upload CSVs, view provenance |
| `/reports` | ReportsPage | Download HTML reports |
| `/settings` | SettingsPage | Campus config, emission factor, weights |

---

## Security Notes

- SQLite file stored locally — no network-exposed database server
- File uploads: size-limited (50 MB), stored in `uploads/` outside web root
- CORS restricted to `FRONTEND_ORIGIN` (default: `http://localhost:5173`)
- No secrets in source code — `.env` is git-ignored
- No path traversal: uploads use UUID-named files
- No data sent to external services — fully offline operation
- No paid APIs, no telemetry, no analytics tracking

---

## Design Rationale

This is a **modular monolith** intentionally designed for:
- Single-campus academic use
- Student demonstration on a laptop
- Offline operation after initial `pip install` + `npm install`
- Zero cost — no cloud, no subscriptions

The agent pipeline is **deterministic and rule-based** — not reliant on a language model. This ensures:
- Reproducible results for the same input
- No API cost or network dependency
- Transparent, auditable logic for academic review
- Explainable findings with cited evidence

Optional Ollama integration is provided via a provider interface, but the system produces identical audit results without it.
