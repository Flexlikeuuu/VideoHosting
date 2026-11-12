.PHONY: up down build ps logs health migrate test

up:
	./deploy.sh

down:
	docker compose down

build:
	docker compose build

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

health:
	curl -fsS http://localhost:$${APP_PORT:-80}/api/v1/health && echo ""

migrate:
	docker compose exec backend alembic upgrade head

test:
	docker compose exec backend pytest -v
