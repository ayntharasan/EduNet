# Setup Guide — Green Campus Sustainability Auditor

> [!IMPORTANT]
> This project runs entirely locally for ₹0. No paid API keys, cloud accounts, or subscriptions are required.

## Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Python | 3.11 | `python --version` |
| Node.js | 18 | `node --version` |
| npm | 9 | `npm --version` |
| Git | any | `git --version` |

---

## 1. Clone / Download the Project

```bash
git clone <your-repo-url> green-campus-sustainability
cd green-campus-sustainability
```

Or download and extract the ZIP, then open a terminal in the project root.

---

## 2. Backend Setup

### 2a. Create a virtual environment (recommended)

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2b. Install Python dependencies

```bash
pip install -r requirements.txt
```

> [!NOTE]
> `weasyprint` (PDF export) is commented out in `requirements.txt` because it requires
> system-level GTK libraries. HTML reports are fully supported without it.

### 2c. Copy the environment example

```powershell
# Windows
copy .env.example .env
```

```bash
# Linux/macOS
cp .env.example .env
```

The defaults in `.env.example` work out of the box. Edit only if you want to change
the database path, emission factor, or optional Ollama settings.

---

## 3. Generate Synthetic Demo Data

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

This creates:
- `data/demo/electricity_demo.csv` — ≈885 rows
- `data/demo/water_demo.csv` — ≈900 rows
- `data/demo/waste_demo.csv` — ≈130 rows

All records are labelled `is_synthetic=True`.

---

## 4. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## 5. Run the Demo (Verify Everything Works)

```powershell
# Windows
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python scripts/run_demo.py
```

```bash
# Linux/macOS
PYTHONPATH=. python scripts/run_demo.py
```

Expected output: 8-step pipeline, 7 agents execute, findings and actions printed, verification simulation completes.

---

## 6. Start the Backend

**Windows (PowerShell)**
```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Linux / macOS**
```bash
PYTHONPATH=. uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify: open `http://127.0.0.1:8000/health` → `{"status":"ok"}`

API docs (Swagger UI): `http://127.0.0.1:8000/api/docs`

---

## 7. Start the Frontend

Open a **second terminal**:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

> [!NOTE]
> The backend must be running on port 8000 for the frontend to fetch data.

---

## 8. Run Tests

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

Expected: **41 passed** (agent e2e tests) + API integration tests.

---

## 9. Validate Datasets

```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
python scripts/validate_datasets.py
```

---

## 10. Build Frontend for Production

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`.

---

## Optional: Ollama Local LLM

1. Install [Ollama](https://ollama.com) (free, runs locally).
2. Pull a model: `ollama pull mistral`
3. Set in `.env`:
   ```
   OLLAMA_ENABLED=true
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=mistral
   ```
4. The core application runs identically without Ollama — this is a purely optional enhancement.

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common errors and fixes.
