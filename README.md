# Mira price service

Mira compares prices for shoppers. This is its price lookup, plus a few local controls so you can break it the same way twice.

## Run

You need Docker with Compose. `make up` starts the API, Redis and Postgres, and `make test` runs the checks. The API listens on `http://localhost:58000`. `make down` removes the containers and the database volume.

## Break it

`make burst` resets the counters, expires the hot key `sku-1` and sends 40 concurrent requests for it. It prints one line:

```
{"requests": 40, "store_reads": N, "p99_ms": N}
```

`make metrics` shows the running counters: cache hits, misses, store reads, request count and p99 latency. `POST /_reset` zeroes them and drops the hot key.

`POST /_control` takes any of these:

- `{"expire": true}` drops the cached `sku-1`
- `{"redis_down": true}` makes the API behave as if Redis were gone
- `{"store_down": true}` does the same for Postgres

Send `false` to bring a dependency back.

## License

MIT. See `LICENSE`.
