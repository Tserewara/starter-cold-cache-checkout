COMPOSE = docker compose -f harness/compose.yaml
.PHONY: up down contract burst reads flush redis-down redis-up store-down store-up logs

# The price service, Redis and Postgres.
up:
	$(COMPOSE) up -d --build --wait service

# Removes the containers and the database.
down:
	$(COMPOSE) down -v

# What the service already does, black-box. Passes before and after your change.
contract:
	$(COMPOSE) run --rm --build contract

# Empty Redis, then 40 simultaneous requests for sku-1. One summary line.
burst:
	$(COMPOSE) run --rm --build tools python3 burst.py 40 sku-1

# How many times the service has read prices from Postgres.
reads:
	@$(COMPOSE) exec -T postgres psql -U prices -d prices -tAc "SELECT 'store_reads=' || CASE WHEN is_called THEN last_value ELSE 0 END FROM store_reads"

# Empty Redis, the way Thursday's deploy did.
flush:
	$(COMPOSE) exec redis redis-cli FLUSHALL

redis-down:
	$(COMPOSE) stop redis
redis-up:
	$(COMPOSE) start redis
store-down:
	$(COMPOSE) stop postgres
store-up:
	$(COMPOSE) start postgres

logs:
	$(COMPOSE) logs -f service
