.PHONY: install backend frontend dev generate

install:
	cd backend && uv sync
	cd frontend && npm install

# Run the API (http://127.0.0.1:8000)
backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

# Run the React dev server (http://127.0.0.1:5173, proxies /api -> :8000)
frontend:
	cd frontend && npm run dev

# Generate one edition from the command line (no server needed)
generate:
	cd backend && uv run python -m app.cli generate
