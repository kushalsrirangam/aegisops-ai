.PHONY: up down backend-test frontend-test lint
up:
	docker compose up --build
down:
	docker compose down
backend-test:
	cd backend && pytest -q
frontend-test:
	cd frontend && npm test
lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint
