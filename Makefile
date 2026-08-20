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

version:
	@./scripts/version.sh get

version-check:
	@./scripts/version.sh check

version-sync:
	@./scripts/version.sh sync

bump-patch:
	@./scripts/version.sh bump patch

bump-minor:
	@./scripts/version.sh bump minor

bump-major:
	@./scripts/version.sh bump major

# ── CI helpers (mirrors ci.yml) ──────────────────────────────────────
ci-lint:
	for svc in adapter-fabric edge-perception reasoning-copilot orchestrator api-gateway; do \
	  echo "=== ruff/mypy $$svc ==="; \
	  (cd services/$$svc && ruff check src tests && mypy src) || exit 1; \
	done
	cd frontend && npm run lint

ci-test:
	for svc in adapter-fabric edge-perception reasoning-copilot orchestrator api-gateway; do \
	  echo "=== pytest $$svc ==="; \
	  (cd services/$$svc && pytest -q) || exit 1; \
	done
	cd frontend && npm test --silent || true

ci-audit:
	for svc in adapter-fabric edge-perception reasoning-copilot orchestrator api-gateway; do \
	  echo "=== pip-audit $$svc ==="; \
	  (cd services/$$svc && pip-audit || true); \
	done
	cd frontend && npm audit || true
	gitleaks detect --source . --no-git -v || true
