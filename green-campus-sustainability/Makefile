.PHONY: install install-backend install-frontend demo test run-backend run-frontend clean

install: install-backend install-frontend

install-backend:
	python -m pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

demo:
	python scripts/generate_demo_data.py

test:
	python -m pytest backend/tests/ -v

run-backend:
	python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

clean:
	Remove-Item -Recurse -Force green_campus.db,uploads,logs -ErrorAction SilentlyContinue

validate-data:
	python scripts/validate_datasets.py
