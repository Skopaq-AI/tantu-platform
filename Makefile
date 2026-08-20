dev:
	docker compose up --build

backend-dev:
	cd backend && pip install -e . && uvicorn tantu.api.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm install && npm run dev

test:
	cd backend && pytest -q
	cd frontend && npm test --silent || true

lint:
	cd backend && ruff check . && mypy src || true
	cd frontend && npm run lint || true

audit:
	cd backend && pip-audit || true
	cd frontend && npm audit || true

demo:
	python demo.py

seed:
	python scripts/seed.py

beta-up:
	docker compose -f docker-compose.microservices.yml up --build -d

beta-down:
	docker compose -f docker-compose.microservices.yml down -v

beta-logs:
	docker compose -f docker-compose.microservices.yml logs -f

dev-microservices:
	docker compose -f docker-compose.microservices.yml up --build
