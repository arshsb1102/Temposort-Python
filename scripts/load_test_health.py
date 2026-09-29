from __future__ import annotations

import argparse
import math
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_health(url: str) -> tuple[float, int | None]:
    started = time.perf_counter()
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=10) as response:
            response.read()
            status_code = response.status
    except HTTPError as exc:
        status_code = exc.code
    except (TimeoutError, URLError, OSError):
        status_code = None
    return time.perf_counter() - started, status_code


def percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(percent * len(ordered)) - 1)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Load probe for the read-only health endpoint.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")

    warmup_latency, warmup_status = request_health(args.url)
    if warmup_status != 200:
        print(f"warmup_failed status={warmup_status}")
        return 1

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda _: request_health(args.url), range(args.requests)))
    elapsed = time.perf_counter() - started

    latencies = [latency for latency, _ in results]
    statuses: dict[str, int] = {}
    for _, status_code in results:
        key = str(status_code) if status_code is not None else "error"
        statuses[key] = statuses.get(key, 0) + 1

    failures = args.requests - statuses.get("200", 0)
    print(f"url={args.url}")
    print(f"requests={args.requests} concurrency={args.concurrency} elapsed_seconds={elapsed:.3f}")
    print(f"warmup_status={warmup_status} warmup_latency_ms={warmup_latency * 1000:.2f}")
    print(f"throughput_rps={args.requests / elapsed:.2f}")
    print(f"latency_ms_p50={percentile(latencies, 0.50) * 1000:.2f}")
    print(f"latency_ms_p95={percentile(latencies, 0.95) * 1000:.2f}")
    print(f"latency_ms_p99={percentile(latencies, 0.99) * 1000:.2f}")
    print(f"statuses={statuses}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
