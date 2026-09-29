from __future__ import annotations

import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def request_json(url: str, token: str, *, method: str = "GET", payload: dict | None = None, idempotency_key: str | None = None) -> tuple[float, int | None, dict | None]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    started = time.perf_counter()
    try:
        request = Request(url, data=body, headers=headers, method=method)
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read())
            return time.perf_counter() - started, response.status, result
    except HTTPError as exc:
        return time.perf_counter() - started, exc.code, None
    except (TimeoutError, URLError, OSError):
        return time.perf_counter() - started, None, None


def percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(percent * len(ordered)) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent authenticated task-create load probe with cleanup.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/tasks")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    token = os.environ.get("DEMO_ACCESS_TOKEN")
    if not token:
        parser.error("set DEMO_ACCESS_TOKEN to a valid authenticated bearer token")
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")

    run_id = uuid4().hex

    def create(index: int) -> tuple[float, int | None, dict | None]:
        return request_json(
            args.url,
            token,
            method="POST",
            payload={
                "title": f"Load probe {run_id}-{index}",
                "description": "Temporary task created by load_test_tasks.py",
                "priority": "low",
            },
            idempotency_key=f"load-probe-{run_id}-{index}",
        )

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(create, range(args.requests)))
    elapsed = time.perf_counter() - started

    created = [result for _, status, result in results if status == 201 and result]
    cleanup_results = [
        request_json(f"{args.url}/{task['id']}", token, method="DELETE")
        for task in created
    ]
    statuses: dict[str, int] = {}
    for _, status, _ in results:
        key = str(status) if status is not None else "error"
        statuses[key] = statuses.get(key, 0) + 1

    latencies = [latency for latency, _, _ in results]
    failed = args.requests - statuses.get("201", 0)
    cleanup_failed = sum(status != 200 for _, status, _ in cleanup_results)
    print(f"url={args.url}")
    print(f"requests={args.requests} concurrency={args.concurrency} elapsed_seconds={elapsed:.3f}")
    print(f"throughput_rps={args.requests / elapsed:.2f}")
    print(f"latency_ms_p50={percentile(latencies, 0.50) * 1000:.2f}")
    print(f"latency_ms_p95={percentile(latencies, 0.95) * 1000:.2f}")
    print(f"latency_ms_p99={percentile(latencies, 0.99) * 1000:.2f}")
    print(f"create_statuses={statuses} cleanup_failures={cleanup_failed}")
    return 1 if failed or cleanup_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
