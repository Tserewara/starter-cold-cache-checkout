"""The price service's given behaviour, black-box over HTTP. A port passes these."""

import os
import unittest

import httpx
import redis

SERVICE = os.environ.get("SERVICE_URL", "http://localhost:58000")
cache = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


class Contract(unittest.TestCase):
    def setUp(self):
        cache.flushall()

    def test_health(self):
        self.assertEqual(httpx.get(f"{SERVICE}/health").status_code, 200)

    def test_cold_then_warm(self):
        first = httpx.get(f"{SERVICE}/price/sku-1")
        second = httpx.get(f"{SERVICE}/price/sku-1")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["sku"], "sku-1")
        self.assertEqual(first.json()["amount_cents"], 1299)
        self.assertEqual(first.json()["source"], "store")
        self.assertEqual(second.json()["amount_cents"], 1299)
        self.assertEqual(second.json()["source"], "cache")

    def test_another_sku(self):
        r = httpx.get(f"{SERVICE}/price/sku-2")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["amount_cents"], 1599)

    def test_unknown_sku_is_404(self):
        self.assertEqual(httpx.get(f"{SERVICE}/price/sku-nope").status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
