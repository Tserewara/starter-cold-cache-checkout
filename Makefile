.PHONY: up down test burst metrics
up:
	docker compose up -d --build
down:
	docker compose down -v
test:
	docker compose run --rm api python3 /app/tests.py
burst:
	docker compose exec -T api python3 /app/loadgen.py 40
metrics:
	curl -s http://localhost:58000/metrics

