# Mira price service

Mira compares prices for shoppers. Checkout asks this service for the price of
every item in the basket: `GET /price/{sku}` answers from Redis when it can
and from Postgres when it can't, then fills Redis for 30 seconds. Every
answer carries `source`: `cache` or `store`.

```
service/    the price service: Python and FastAPI
harness/    Redis, Postgres with the prices, and the tools the drills use
contract/   black-box tests of what the service answers
```

## Run

You need Docker with Compose, nothing else. `make up` starts the service,
Redis and Postgres; the service listens on `http://localhost:58000`.
`make contract` runs the contract tests. `make down` removes the containers
and the database.

## Break it

- `make flush` empties Redis, the way Thursday's deploy did.
- `make burst` empties Redis, then sends 40 requests for `sku-1` at the same
  moment. It prints one line:

  ```
  requests=40 errors=N store_reads=N p99_ms=N
  ```

  `store_reads` is how many times the service read prices from Postgres
  during the burst, counted by Postgres itself. `p99_ms` is what the forty
  callers waited.
- `make reads` prints the running total, `store_reads=N`.
- `make redis-down` and `make redis-up` stop and start Redis for real.
  `make store-down` and `make store-up` do the same for Postgres.

The Postgres here is small, so the harness makes it behave like a busier
primary: reads of `prices` get slower as more of them run at once. That lives
in the database (`harness/postgres/init.sql`), outside the service.

## Porting the service

The service is Python and FastAPI; you can write it in another language. It
listens on port 8000 inside its container (published as 58000), reads
`DATABASE_URL` and `REDIS_URL`, reads prices from the `prices` view
(`sku`, `amount_cents`), and answers the routes in `contract/openapi.yaml`.
Build it from `service/Dockerfile`, then run `make contract` until it passes.
The contract covers the normal path only: extra fields in an answer, and
whatever you answer during an outage, are yours to decide.

## License

MIT. See `LICENSE`.
