# Pico Score Keeper (PSK) — Starter (Full)

A working PWA + FastAPI starter for your pickleball scoring app.

## Quick Start

### Backend
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8787
```

### Frontend
```
cd frontend
python -m http.server 5173
# open http://localhost:5173
```
Then set API Base to http://localhost:8787 in the UI and click Save.
