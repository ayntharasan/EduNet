# Agentic AI-Powered Green Campus Sustainability Auditor

> A complete, locally-runnable, ₹0-cost final-year CS academic project — sustainability auditing platform for college campuses.

---

## What It Does

This platform helps campus sustainability officers:

1. **Import** electricity, water, and waste measurements via CSV upload or synthetic demo data  
2. **Audit** consumption patterns using a **7-agent deterministic AI pipeline**  
3. **Detect** anomalies, baseline deviations, and waste inefficiencies using ML  
4. **Plan** prioritised corrective actions (zero-cost first)  
5. **Verify** that implemented actions produced measurable improvements  
6. **Report** all findings with full evidence provenance as HTML documents  

---

## Key Features

| Feature | Detail |
|---------|--------|
| 7 real agents | DataQuality → Auditor → Investigation → ActionPlanning → Prioritization → Reporting + Verification |
| Typed Pydantic handoffs | Every agent-to-agent interface is schema-validated |
| Zero paid dependencies | Runs entirely offline after `pip install` + `npm install` |
| SQLite persistence | 14 tables, no database server needed |
| ML anomaly detection | Isolation Forest (scikit-learn), Z-score fallback |
| CO₂ estimation | CEA India grid emission factor (Scope 2, cited) |
| Synthetic data labels | All demo data marked `is_synthetic=True` throughout |
| React dashboard | Recharts visualisations, 12 pages, React Router v7 |
| 41 pytest tests | Agents, analytics, ML, data provenance |
| API docs | Swagger UI at `http://127.0.0.1:8000/api/docs` |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1 — Install dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2 — Generate demo data

```powershell
# Windows (PowerShell)
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python scripts/generate_demo_data.py
```

```bash
# Linux/macOS
PYTHONPATH=. python scripts/generate_demo_data.py
```

### 3 — Start the backend

```powershell
# Windows
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# Linux/macOS
PYTHONPATH=. uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4 — Start the frontend _(new terminal)_

```bash
cd frontend
npm run dev
```

### 5 — Open the application

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API docs (Swagger) | http://127.0.0.1:8000/api/docs |
| Health check | http://127.0.0.1:8000/health |

---

## Running Tests

```powershell
# Windows
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python -m pytest backend/tests/ -v
```

```bash
# Linux/macOS
PYTHONPATH=. python -m pytest backend/tests/ -v
```

Expected: **41 passed** (agent e2e) + API integration tests.

---

## Demo Pipeline

```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python scripts/run_demo.py
```

The demo runs 8 steps:
1. Database initialisation  
2. Loads 1,915 synthetic records  
3. Runs all 7 agents  
4. Prints audit summary  
5. Shows agent execution log  
6. Lists top findings (with anomaly injection)  
7. Shows priority action plan  
8. Runs verification simulation (18% synthetic reduction)  
9. Generates HTML report in `reports/`  

---

## Architecture Overview

```
React Frontend (Vite + Tailwind CSS v4 + Recharts)
        │  REST/JSON
FastAPI Backend (Python 3.11, SQLAlchemy, SQLite)
        │
   7-Agent Pipeline (deterministic, rule-based, no paid LLM)
   ├─ [1] DataQualityAgent
   ├─ [2] SustainabilityAuditorAgent  ←── Isolation Forest / Z-score
   ├─ [3] InvestigationAgent
   ├─ [4] ActionPlanningAgent
   ├─ [5] PrioritizationAgent
   ├─ [6] VerificationAgent  (post-intervention, separate invocation)
   └─ [7] ReportingAgent  ──► HTML report
        │
   SQLite (14 tables)
```

---

## Project Structure

```
green-campus-sustainability/
├── backend/app/
│   ├── agents/         ← 7 agents + orchestrator
│   ├── api/            ← 9 FastAPI route modules
│   ├── analytics/      ← energy, water, waste KPIs
│   ├── ml/             ← anomaly detection, forecasting
│   └── models/         ← 14 SQLAlchemy tables
├── frontend/src/pages/ ← 12 React pages
├── scripts/            ← demo, generation, validation
├── docs/               ← documentation
└── data/demo/          ← synthetic demo CSVs
```

---

## Data Transparency

> [!IMPORTANT]
> All demo measurements are **synthetically generated** (`is_synthetic=True` everywhere).
> No real campus data is used. External public datasets (UCI, CPCB, data.gov.in) are
> referenced only as benchmarks, never imported as campus data.

Emission estimates use **CEA India grid factor: 0.716 kgCO2e/kWh (2022-23)**, Scope 2 only.

See [data/DATASET_CATALOG.md](data/DATASET_CATALOG.md) and [docs/DATASET_DOWNLOAD_GUIDE.md](docs/DATASET_DOWNLOAD_GUIDE.md).

---

## Cost

**₹0 total.** No paid APIs. No cloud. No credit card. No subscriptions.

---

## Optional: Local LLM via Ollama

1. Install [Ollama](https://ollama.com)  
2. `ollama pull mistral`  
3. Set in `.env`: `OLLAMA_ENABLED=true`, `OLLAMA_MODEL=mistral`  

The system produces identical audit results without Ollama.

---

## Documentation

| Document | Path |
|----------|------|
| Setup Guide | [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) |
| Agent Workflow | [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Dataset Download Guide | [docs/DATASET_DOWNLOAD_GUIDE.md](docs/DATASET_DOWNLOAD_GUIDE.md) |
| Troubleshooting | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Dataset Catalog | [data/DATASET_CATALOG.md](data/DATASET_CATALOG.md) |

---

## Licence

MIT — free to use, modify, and share for educational purposes.
