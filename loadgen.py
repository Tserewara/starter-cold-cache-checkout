import concurrent.futures
import json
import os
import sys
import urllib.request

BASE = os.environ.get("API_URL", "http://api:8000")


def call(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return json.load(response)


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    reset = urllib.request.Request(BASE + "/_reset", data=b"", method="POST")
    urllib.request.urlopen(reset).read()
    control = urllib.request.Request(BASE + "/_control", data=json.dumps({"expire": True, "stampede": True}).encode(), method="POST", headers={"content-type": "application/json"})
    urllib.request.urlopen(control).read()
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda _: call("/price/sku-1"), range(count)))
    metrics = call("/metrics")
    print(json.dumps({"requests": len(results), "store_reads": metrics["store_reads"], "p99_ms": metrics["p99_ms"]}))


if __name__ == "__main__":
    main()
