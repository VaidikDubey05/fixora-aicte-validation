.PHONY: help up down test seed eval lint

help:
	@echo "Fixora Development Commands:"
	@echo "  make up     - Build and start all services via Docker Compose"
	@echo "  make down   - Stop and tear down running containers"
	@echo "  make test   - Run backend pytest suite"
	@echo "  make seed   - Trigger synthetic demo seed via API"
	@echo "  make eval   - Execute statutory rulepack & model evaluation"
	@echo "  make lint   - Run linters on backend and frontend"

up:
	docker compose up -d --build

down:
	docker compose down

test:
	@if [ -n "$$(docker compose ps -q backend 2>/dev/null)" ]; then \
		docker compose exec -T backend pytest; \
	else \
		python -m pytest backend/tests; \
	fi

seed:
	@echo "Seeding synthetic demo data..."
	@curl -s -X POST http://localhost:8000/api/demo/seed || echo "Backend not reachable on :8000. Start containers with 'make up' first."

eval:
	@echo "Running Fixora verification & validation evaluation suite..."
	@if [ -n "$$(docker compose ps -q backend 2>/dev/null)" ]; then \
		docker compose exec -T backend python app/eval/run_eval.py; \
	else \
		python backend/app/eval/run_eval.py; \
	fi

lint:
	@echo "Running backend lint (ruff)..."
	@if [ -n "$$(docker compose ps -q backend 2>/dev/null)" ]; then \
		docker compose exec -T backend ruff check app tests; \
	else \
		python -m ruff check backend/app backend/tests || true; \
	fi
	@echo "Running frontend type check (tsc)..."
	@if [ -d "frontend/node_modules" ]; then \
		cd frontend && npm run lint; \
	else \
		echo "frontend/node_modules not found locally. Run 'npm install' in frontend or run inside docker."; \
	fi
