.PHONY: api web sync

api:
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8001

web:
	cd apps/web && npm run dev -- --port 3000

sync:
	curl -s -X POST 'http://127.0.0.1:8001/api/jobs/sync?query=software%20engineer'
