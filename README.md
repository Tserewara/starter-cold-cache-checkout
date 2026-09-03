# Mira price service

Mira compares prices for shoppers. The service exposes a small price lookup and local controls for repeatable experiments.

## Run

You need Docker with Compose. Run `make up`, then `make test`. The API is at `http://localhost:58000`.

`make burst` sends 40 concurrent requests after the cache has been cleared by `POST /_control` with `{"expire": true}`. The API's `/metrics` endpoint reports cache hits, misses, store reads, request count, and p99 latency.

The local stack contains the API, Redis, and Postgres. The control endpoint can expire the hot key and simulate either dependency being unavailable. `make down` removes the local containers and database volume.

## License

MIT. See `LICENSE`.

