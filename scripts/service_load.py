"""Synthetic SigV4 load on telemetry-api, so Omni has enough requests to colour the service.

Usage: python scripts/service_load.py <telemetry_api_url> [--requests N] [--rate R] [--profile P]
No model calls, so no token cost. Hard cap 600 requests per call, 10 requests per second.
"""
import argparse
import itertools
import time
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

MAX_REQUESTS = 600
PATHS = ["alerts/ALR-1001", "metrics/checkout", "alerts/ALR-1002", "alerts/ALR-1003"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--rate", type=float, default=3.0)
    parser.add_argument("--profile", default="build04")
    args = parser.parse_args()
    if not 1 <= args.requests <= MAX_REQUESTS:
        parser.error(f"--requests must be between 1 and {MAX_REQUESTS}")
    if not 0.1 <= args.rate <= 10:
        parser.error("--rate must be between 0.1 and 10")

    session = boto3.Session(profile_name=args.profile)
    creds = session.get_credentials()
    interval = 1.0 / args.rate
    statuses, latencies = {}, []

    for n, path in zip(range(1, args.requests + 1), itertools.cycle(PATHS)):
        start = time.monotonic()
        url = args.url + path
        signed = AWSRequest(method="GET", url=url)
        SigV4Auth(creds.get_frozen_credentials(), "lambda", session.region_name).add_auth(signed)
        request = urllib.request.Request(url, headers=dict(signed.headers), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=15) as resp:
                resp.read()
                status = resp.status
        except urllib.error.HTTPError as err:
            status = err.code
        elapsed = time.monotonic() - start
        statuses[status] = statuses.get(status, 0) + 1
        latencies.append(elapsed)
        if n % 50 == 0:
            print(f"{n} sent, statuses {statuses}")
        time.sleep(max(0.0, interval - elapsed))

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
    print(f"done: {args.requests} requests, statuses {statuses}, "
          f"client p50 {p50 * 1000:.0f} ms, p95 {p95 * 1000:.0f} ms")


if __name__ == "__main__":
    main()