import json
import os
import urllib.request

BASE = os.environ.get("API_URL", "http://api:8000")


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


request("POST", "/_reset")
first = request("GET", "/price/sku-1")
second = request("GET", "/price/sku-1")
assert first["amount_cents"] == 1299
assert second["source"] == "cache"
print("2 tests passed")

