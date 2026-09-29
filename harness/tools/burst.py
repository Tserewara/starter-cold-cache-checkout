"""Thursday, small: empty the cache the way the deploy did, then release
forty requests for one SKU at the same moment.

Prints one line: requests, errors, the store reads the burst caused (counted
by Postgres itself) and the p99 the callers saw.
"""

import concurrent.futures
import http.client
import os
import socket
import sys
import threading
import time
from urllib.parse import urlsplit

import psycopg
import redis

SERVICE = os.environ.get("SERVICE_URL", "http://service:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://prices:prices@postgres:5432/prices")


def store_reads() -> int:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        value, called = conn.execute("SELECT last_value, is_called FROM store_reads").fetchone()
        return value if called else 0


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    sku = sys.argv[2] if len(sys.argv) > 2 else "sku-1"
    redis.Redis.from_url(REDIS_URL).flushall()
    before = store_reads()
    # Every connection is open before the barrier, so the forty requests reach
    # the service together; the barrier lives here, never in the service.
    target = urlsplit(SERVICE)
    address = socket.gethostbyname(target.hostname)
    start = threading.Barrier(count)

    def one(_):
        conn = http.client.HTTPConnection(address, target.port or 80, timeout=10)
        conn.connect()
        start.wait(timeout=10)
        t0 = time.perf_counter()
        try:
            conn.request("GET", f"/price/{sku}", headers={"Host": target.netloc})
            response = conn.getresponse()
            response.read()
            ok = response.status == 200
        except OSError:
            ok = False
        finally:
            conn.close()
        return ok, (time.perf_counter() - t0) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(one, range(count)))
    latencies = sorted(ms for _, ms in results)
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]
    errors = sum(1 for ok, _ in results if not ok)
    print(f"requests={count} errors={errors} store_reads={store_reads() - before} p99_ms={p99:.0f}", flush=True)


if __name__ == "__main__":
    main()
