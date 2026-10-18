# Troubleshooting Guide

## Backend Startup

### `ModuleNotFoundError: No module named 'backend'`

**Cause:** Python cannot locate the project root package.

**Fix — Windows (PowerShell):**
```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Fix — Linux/macOS:**
```bash
PYTHONPATH=. uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### `UnicodeEncodeError` on Windows

**Cause:** Windows console defaults to code page `cp1252` which cannot encode certain characters.

**Fix:**
```powershell
$env:PYTHONIOENCODING="utf-8"
```

Add this before every Python command in the same PowerShell session.

---

### `Address already in use` (port 8000)

```powershell
# Windows — find and kill the process on port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Stop-Process -Force
```

```bash
# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

---

### `weasyprint` installation fails

**Cause:** weasyprint requires GTK system libraries not available on Windows without extra setup.

**Fix:** weasyprint is already commented out in `requirements.txt`. HTML reports are generated without it. PDF export is not supported in the current build.

---

### `pydantic_settings` import error

```bash
pip install pydantic-settings==2.6.1
```

Make sure you installed from `requirements.txt`, not just `pydantic` alone.

---

### Backend starts but returns `500` on `/api/analytics/dashboard`

**Cause:** Database not initialised yet, or demo data not loaded.

**Fix:**
1. Ensure the backend has started at least once (triggers `init_db()`)
2. Run the demo data generator: `python scripts/generate_demo_data.py`
3. Trigger an audit: `POST /api/audit/run` with `{"use_demo_data": true}`

---

## Tests

### `pytest: command not found`

Always use the module invocation:
```bash
python -m pytest backend/tests/ -v
```

---

### `collected 0 items`

**Cause:** `PYTHONPATH` not set, or wrong working directory.

**Fix:**
```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
python -m pytest backend/tests/test_agents_e2e.py -v
```

---

### Test fails with `ImportError` on `backend.app.*`

Same fix — set `PYTHONPATH` to the project root before running pytest.

---

## Frontend

### `npm install` fails with `ERESOLVE`

```bash
npm install --legacy-peer-deps
```

---

### Frontend shows blank page / API errors in console

1. Confirm backend is running: `curl http://127.0.0.1:8000/health` should return `{"status":"ok"}`
2. Check browser DevTools → Network tab for failed requests
3. Check CORS — backend allows `http://localhost:5173` only (not `http://127.0.0.1:5173`)
4. Confirm `vite.config.js` proxy target is `http://127.0.0.1:8000`

---

### `npm run dev` port conflict (5173 in use)

```bash
npm run dev -- --port 5174
```

Update `FRONTEND_ORIGIN=http://localhost:5174` in `.env` and restart the backend.

---

### `npm run build` fails

```bash
cd frontend
npm install   # re-install in case node_modules is stale
npm run build
```

If Tailwind CSS errors appear, ensure `@tailwindcss/vite` is installed and `vite.config.js` uses the v4 plugin pattern.

---

## Data Issues

### Demo data files missing

```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
python scripts/generate_demo_data.py
```

Expected: 885 electricity rows, 900 water rows, 130 waste rows.

---

### Audit returns 0 findings

**Cause:** Insufficient data variance for anomaly detection.

**Fix:** The Isolation Forest requires ≥10 samples. Ensure demo data was generated with the full 6-month window. The Z-score fallback activates for small samples.

---

### Audit reports `278% above baseline` unexpectedly

This is intentional in the demo. The demo generator includes an artificial spike in electricity consumption to demonstrate the auditor's detection capability. This is synthetic, labelled data — it is not an error.

---

### Verification returns `insufficient_data`

**Cause:** `VerificationAgent` requires ≥7 days of data in **both** the pre-action and post-action periods.

**Fix:** Provide date ranges spanning ≥7 calendar days for `baseline_start/end` and `post_start/end`.

---

### CSV upload rejected

**Cause:** Column names don't match the expected schema.

**Fix:** Use the templates in `data/templates/` as starting points:
- `electricity_template.csv` — required: `timestamp`, `building_id`, `consumption_kwh`
- `water_template.csv` — required: `measurement_date`, `building_id`, `consumption_litres`
- `waste_template.csv` — required: `measurement_date`, `building_id`, `total_waste_kg`

---

## Database

### `green_campus.db` is corrupted or locked

```powershell
# Windows
Remove-Item green_campus.db -Force
```

```bash
# Linux/macOS
rm green_campus.db
```

The database is recreated automatically on next backend startup.

---

### `OperationalError: no such table`

The database tables haven't been created yet. Start the backend once — `init_db()` runs automatically in the lifespan handler. Alternatively:

```python
from backend.app.database.init_db import init_db
init_db()
```

---

### `UNIQUE constraint failed: audit_runs.run_id`

This should never occur (run IDs are UUID-based). If it does, delete `green_campus.db` and restart.

---

## Ollama (Optional)

### `httpx.ConnectError: Connection refused` to Ollama

Ensure Ollama is running: `ollama serve`

Ollama is **optional**. Set `OLLAMA_ENABLED=false` in `.env` to disable it completely. The audit pipeline produces identical results without Ollama.

---

## Getting Help

Check in this order:
1. This troubleshooting guide
2. [`docs/SETUP_GUIDE.md`](SETUP_GUIDE.md) — step-by-step setup
3. [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — system design
4. `http://127.0.0.1:8000/api/docs` — interactive API docs (backend must be running)
5. Run tests: `python -m pytest backend/tests/ -v --tb=long` — detailed failure output
