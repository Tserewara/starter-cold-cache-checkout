import json
import os

import psycopg
import redis
from fastapi import FastAPI, HTTPException

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
CACHE_TTL_S = 30

cache = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="Mira price service")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/price/{sku}")
def price(sku: str):
    """Cache-aside: Redis first, Postgres on a miss, then fill Redis."""
    cached = cache.get(f"price:{sku}")
    if cached is not None:
        return {**json.loads(cached), "source": "cache"}

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("SELECT amount_cents FROM prices WHERE sku = %s", (sku,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="sku not found")
    value = {"sku": sku, "amount_cents": row[0]}
    cache.setex(f"price:{sku}", CACHE_TTL_S, json.dumps(value))
    return {**value, "source": "store"}
