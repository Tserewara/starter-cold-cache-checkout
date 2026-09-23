import json
import os
import threading
import time
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
cache = redis.Redis.from_url(REDIS_URL, decode_responses=True)
state_lock = threading.Lock()
state = {
    "redis_down": False,
    "store_down": False,
    "cache_hits": 0,
    "cache_misses": 0,
    "store_reads": 0,
    "durations_ms": [],
}
# During `make burst` a store read costs more the more reads are in flight at
# once, the way a busy primary slows down under a herd. One read stays cheap.
STORE_READ_COST_S = 0.025
store_reads_in_flight = 0
stampede_enabled = False


def db_connect():
    return psycopg.connect(DATABASE_URL)


def init_db():
    for _ in range(30):
        try:
            with db_connect() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS prices (sku text primary key, amount_cents integer not null)")
                conn.execute("INSERT INTO prices VALUES ('sku-1', 1299), ('sku-2', 2599) ON CONFLICT DO NOTHING")
                conn.commit()
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("database did not become ready")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Mira price service", lifespan=lifespan)


class Control(BaseModel):
    redis_down: bool | None = None
    store_down: bool | None = None
    expire: bool = False
    stampede: bool | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/_control")
def control(payload: Control):
    global stampede_enabled
    with state_lock:
        if payload.redis_down is not None:
            state["redis_down"] = payload.redis_down
        if payload.store_down is not None:
            state["store_down"] = payload.store_down
        if payload.expire:
            cache.delete("price:sku-1")
        if payload.stampede is not None:
            stampede_enabled = payload.stampede
    return {"ok": True, "state": {k: v for k, v in state.items() if k.endswith("down")}}


@app.post("/_reset")
def reset():
    global stampede_enabled
    with state_lock:
        state["cache_hits"] = 0
        state["cache_misses"] = 0
        state["store_reads"] = 0
        state["durations_ms"] = []
        state["redis_down"] = False
        state["store_down"] = False
        stampede_enabled = False
    cache.delete("price:sku-1")
    return {"ok": True}


def read_store(sku: str, contended: bool):
    global store_reads_in_flight
    with state_lock:
        store_reads_in_flight += 1
        in_flight = store_reads_in_flight
    try:
        if contended:
            time.sleep(STORE_READ_COST_S * in_flight)
        with db_connect() as conn:
            row = conn.execute("SELECT amount_cents FROM prices WHERE sku = %s", (sku,)).fetchone()
    finally:
        with state_lock:
            store_reads_in_flight -= 1
            state["store_reads"] += 1
    return row


@app.get("/price/{sku}")
def price(sku: str):
    started = time.perf_counter()
    try:
        cached = None
        with state_lock:
            redis_down = state["redis_down"]
        if not redis_down:
            cached = cache.get(f"price:{sku}")
        if cached is not None:
            with state_lock:
                state["cache_hits"] += 1
            result = json.loads(cached)
            result["source"] = "cache"
            return result

        with state_lock:
            state["cache_misses"] += 1
            store_down = state["store_down"]
            contended = stampede_enabled
        if store_down:
            raise HTTPException(status_code=503, detail="price temporarily unavailable")
        row = read_store(sku, contended=contended)
        if row is None:
            raise HTTPException(status_code=404, detail="sku not found")
        result = {"sku": sku, "amount_cents": row[0], "source": "store"}
        if not redis_down:
            cache.setex(f"price:{sku}", 30, json.dumps(result))
        return result
    finally:
        with state_lock:
            state["durations_ms"].append(round((time.perf_counter() - started) * 1000, 2))
            state["durations_ms"] = state["durations_ms"][-10000:]


@app.get("/metrics")
def metrics():
    with state_lock:
        durations = sorted(state["durations_ms"])
        p99 = durations[min(len(durations) - 1, int(len(durations) * 0.99))] if durations else 0
        return {
            "cache_hits": state["cache_hits"],
            "cache_misses": state["cache_misses"],
            "store_reads": state["store_reads"],
            "request_count": len(durations),
            "p99_ms": p99,
        }
